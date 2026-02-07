import os
import time
import logging
from urllib.parse import quote_plus
from flask import Flask, jsonify, request
from flask_sqlalchemy import SQLAlchemy
from opentelemetry import trace
from opentelemetry.trace import Status, StatusCode

app = Flask(__name__)

# --- Configuração de Logs ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Configuração do Banco de Dados ---
db_user = os.getenv("DB_USER", "root")
db_pass = os.getenv("DB_PASS", "senha")
db_host = os.getenv("DB_HOST", "127.0.0.1")
db_name = os.getenv("DB_NAME", "loja_rum")

encoded_pass = quote_plus(db_pass)
app.config['SQLALCHEMY_DATABASE_URI'] = f'mysql+pymysql://{db_user}:{encoded_pass}@{db_host}/{db_name}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {'pool_recycle': 280, 'pool_pre_ping': True}

db = SQLAlchemy(app)

# --- Modelo ---
class Pedido(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    produto = db.Column(db.String(50))
    status = db.Column(db.String(20))
    valor = db.Column(db.Float)
    timestamp_epoch = db.Column(db.Float)

# --- Inicialização ---
with app.app_context():
    try:
        db.create_all()
        logger.info(f"✅ CONECTADO AO BANCO: {db_host}")
    except Exception as e:
        logger.error(f"❌ FALHA AO CONECTAR NO BANCO: {e}")

# --- Frontend RUM (ATUALIZADO PARA GRAFANA CLOUD) ---
RUM_HTML = """
<!DOCTYPE html>
<html lang="pt-br">
<head>
    <meta charset="UTF-8">
    <title>Loja RUM - Grafana Cloud</title>
    <style>
        body { font-family: 'Segoe UI', sans-serif; text-align: center; background-color: #f4f4f9; padding: 50px; }
        .card { background: white; max-width: 400px; margin: auto; padding: 30px; border-radius: 10px; box-shadow: 0 4px 15px rgba(0,0,0,0.1); }
        h1 { color: #333; }
        button { width: 100%; padding: 15px; margin: 10px 0; border: none; border-radius: 5px; font-size: 18px; cursor: pointer; transition: 0.3s; }
        .btn-buy { background-color: #28a745; color: white; }
        .btn-buy:hover { background-color: #218838; }
        .btn-error { background-color: #dc3545; color: white; }
        .btn-error:hover { background-color: #c82333; }
        #status { margin-top: 20px; font-weight: bold; color: #555; }
    </style>
    
    <script type="module">
      import { context, trace, SpanStatusCode } from 'https://esm.sh/@opentelemetry/api@1.7.0';
      import { WebTracerProvider } from 'https://esm.sh/@opentelemetry/sdk-trace-web@1.30.1';
      import { BatchSpanProcessor } from 'https://esm.sh/@opentelemetry/sdk-trace-base@1.30.1';
      import { Resource } from 'https://esm.sh/@opentelemetry/resources@1.30.1';
      import { SemanticResourceAttributes } from 'https://esm.sh/@opentelemetry/semantic-conventions@1.28.0';
      import { OTLPTraceExporter } from 'https://esm.sh/@opentelemetry/exporter-trace-otlp-http@0.57.2';
      import { FetchInstrumentation } from 'https://esm.sh/@opentelemetry/instrumentation-fetch@0.34.0';
      import { W3CTraceContextPropagator } from 'https://esm.sh/@opentelemetry/core@1.30.1';

      // --- CONFIGURAÇÃO MANUAL GRAFANA CLOUD (RUM) ---
      // IMPORTANTE: Isso envia o trace do navegador do cliente direto para a nuvem
      const tempoUser = '1471033'; 
      const tempoToken = '62d28f58-5cc3-4f65-8452-fd4f5092e5e9'; 
      const tempoUrl = 'https://tempo-prod-17-prod-sa-east-1.grafana.net/tempo/v1/traces';

      // Criação do Header de Autenticação Basic Auth
      const authHeader = 'Basic ' + btoa(tempoUser + ':' + tempoToken);

      const provider = new WebTracerProvider({
          resource: new Resource({ 
            [SemanticResourceAttributes.SERVICE_NAME]: 'flask-frontend-rum',
            [SemanticResourceAttributes.DEPLOYMENT_ENVIRONMENT]: 'producao'
          })
      });
      
      const exporter = new OTLPTraceExporter({ 
          url: tempoUrl,
          headers: {
              'Authorization': authHeader
          }
      });

      provider.addSpanProcessor(new BatchSpanProcessor(exporter));
      
      provider.register({ propagator: new W3CTraceContextPropagator() });
      new FetchInstrumentation({ propagateTraceHeaderCorsUrls: [/.+/] }).setTracerProvider(provider);
      
      const tracer = provider.getTracer('loja-frontend');

      // Trace de Carregamento da Página
      window.addEventListener('load', () => {
          const pageLoadSpan = tracer.startSpan('page_load');
          setTimeout(() => { pageLoadSpan.end(); }, 100);
      });

      window.acao = (tipo) => {
          const span = tracer.startSpan('user_interaction', {
              attributes: { 
                  'action': tipo === 'comprar' ? 'compra' : 'erro',
                  'app.component': 'botao',
                  'target_system': 'grafana_cloud'
              }
          });
          
          const endpoint = tipo === 'comprar' ? '/checkout' : '/simular_erro';
          console.info(`🚀 [AÇÃO] Usuário: ${tipo.toUpperCase()}`);
          
          document.getElementById('status').innerText = "Processando...";

          context.with(trace.setSpan(context.active(), span), () => {
              fetch(endpoint, { method: 'POST' })
                .then(r => r.json().then(data => ({status: r.status, body: data})))
                .then(res => { 
                    if(res.status === 200) {
                        document.getElementById('status').innerText = `✅ Sucesso! ID: ${res.body.id}`;
                        document.getElementById('status').style.color = "green";
                        span.setStatus({ code: SpanStatusCode.OK });
                    } else {
                        document.getElementById('status').innerText = `❌ Erro: ${res.body.msg}`;
                        document.getElementById('status').style.color = "red";
                        span.setStatus({ code: SpanStatusCode.ERROR, message: res.body.msg });
                    }
                    span.end(); 
                })
                .catch(e => { 
                    console.error("🔥 Erro JS:", e);
                    document.getElementById('status').innerText = "Erro Crítico"; 
                    span.recordException(e);
                    span.setStatus({ code: SpanStatusCode.ERROR });
                    span.end(); 
                });
          });
      };
    </script>
</head>
<body>
    <div class="card">
        <h1>🛍️ Loja RUM</h1>
        <p>Monitorado por Grafana Cloud</p>
        <button class="btn-buy" onclick="window.acao('comprar')">COMPRAR (Gera Trace)</button>
        <button class="btn-error" onclick="window.acao('erro')">GERAR ERRO (Gera Alerta)</button>
        <div id="status">Aguardando ação...</div>
    </div>
</body>
</html>
"""

@app.route('/')
def home():
    return RUM_HTML

@app.route('/checkout', methods=['POST'])
def checkout():
    tracer = trace.get_tracer(__name__)
    
    # Atributos para enriquecer o trace no Backend
    span_attributes = {
        "http.method": "DB_INSERT", 
        "db.system": "mysql",
        "db.operation": "INSERT",
        "db.table": "pedido"
    }
    
    with tracer.start_as_current_span("processar_pagamento", attributes=span_attributes) as span:
        try:
            logger.info("Iniciando transação no banco...")
            
            novo = Pedido(produto="PlayStation 5", status="PAGO", valor=4500.00, timestamp_epoch=time.time())
            db.session.add(novo)
            db.session.commit()
            
            span.set_attribute("db.row_id", novo.id)
            return jsonify({"status": "sucesso", "id": novo.id})
            
        except Exception as e:
            logger.error(f"Erro no banco: {e}")
            span.record_exception(e)
            span.set_status(Status(StatusCode.ERROR))
            return jsonify({"status": "erro", "msg": str(e)}), 500

@app.route('/simular_erro', methods=['POST'])
def simular_erro():
    tracer = trace.get_tracer(__name__)
    
    span_attributes = {
        "http.method": "INTERNAL_ERROR",
        "simulacao": "true"
    }
    
    with tracer.start_as_current_span("simulacao_falha", attributes=span_attributes) as span:
        try:
            logger.error("Simulação de erro solicitada!")
            raise Exception("Gateway de Pagamento: Indisponível (Simulação)")
        except Exception as e:
            span.record_exception(e)
            span.set_status(Status(StatusCode.ERROR))
            return jsonify({"status": "erro_simulado", "msg": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
