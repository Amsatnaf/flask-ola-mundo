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

# --- Frontend RUM (CORRIGIDO: TRACING + CORE) ---
RUM_HTML = """
<!DOCTYPE html>
<html lang="pt-br">
<head>
    <meta charset="UTF-8">
    <title>Loja RUM - Monitoramento Completo</title>
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
    
    <script src="https://unpkg.com/@grafana/faro-web-sdk@^1.4.0/dist/bundle/faro-web-sdk.iife.js"></script>
    
    <script src="https://unpkg.com/@grafana/faro-web-tracing@^1.4.0/dist/bundle/faro-web-tracing.iife.js"></script>

    <script>
      // Configuração para ligar Frontend ao Backend
      var faro = GrafanaFaroWebSdk.initializeFaro({
        url: 'https://faro-collector-prod-sa-east-1.grafana.net/collect/e1a2f88c30e6e51ce17e7027fda40ae4',
        app: {
          name: 'loja-frontend',
          version: '2.0.0', // Mudei a versão para você ver a diferença no dashboard
          environment: 'production'
        },
        instrumentations: [
          new GrafanaFaroWebSdk.ConsoleInstrumentation(),
          new GrafanaFaroWebSdk.ErrorsInstrumentation(),
          new GrafanaFaroWebSdk.SessionInstrumentation(),
          
          // AQUI ESTÁ A CORREÇÃO: Usamos o pacote 'GrafanaFaroWebTracing'
          new GrafanaFaroWebTracing.TracingInstrumentation({
            // Isso garante que o trace do front se conecte ao trace do back (Flask)
            propagationKey: 'traceparent',
            cors: true 
          })
        ]
      });

      window.acao = (tipo) => {
          const endpoint = tipo === 'comprar' ? '/checkout' : '/simular_erro';
          console.info(`🚀 [AÇÃO] Usuário: ${tipo.toUpperCase()}`);
          
          document.getElementById('status').innerText = "Processando...";

          // Envia evento de clique para contagem de uso
          faro.api.pushEvent('click_botao', { acao: tipo });

          fetch(endpoint, { method: 'POST' })
            .then(r => r.json().then(data => ({status: r.status, body: data})))
            .then(res => { 
                if(res.status === 200) {
                    document.getElementById('status').innerText = `✅ Sucesso! ID: ${res.body.id}`;
                    document.getElementById('status').style.color = "green";
                } else {
                    document.getElementById('status').innerText = `❌ Erro: ${res.body.msg}`;
                    document.getElementById('status').style.color = "red";
                    // Envia erro estruturado para o Grafana (Conta no gráfico de erros)
                    faro.api.pushError(new Error(res.body.msg));
                }
            })
            .catch(e => { 
                console.error("🔥 Erro JS:", e);
                document.getElementById('status').innerText = "Erro Crítico";
                faro.api.pushError(e);
            });
      };
    </script>
</head>
<body>
    <div class="card">
        <h1>🛍️ Loja RUM</h1>
        <p>Versão 2.0 - Full Monitoring</p>
        <button class="btn-buy" onclick="window.acao('comprar')">COMPRAR</button>
        <button class="btn-error" onclick="window.acao('erro')">GERAR ERRO</button>
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
    
    # Isso vai aparecer no detalhe do Trace
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
