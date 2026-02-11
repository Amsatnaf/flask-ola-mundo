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

# Tratamento seguro da senha
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

# --- Inicialização do Banco ---
with app.app_context():
    try:
        db.create_all()
        logger.info(f"✅ CONECTADO AO BANCO: {db_host}")
    except Exception as e:
        logger.error(f"❌ FALHA AO CONECTAR NO BANCO: {e}")

# --- Frontend RUM (HTML + JS Faro) ---
RUM_HTML = """
<!DOCTYPE html>
<html lang="pt-br">
<head>
    <meta charset="UTF-8">
    <title>Loja RUM - Monitoramento V2</title>
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
        .info { font-size: 12px; color: #888; margin-top: 10px; }
    </style>
    
    <script src="https://unpkg.com/@grafana/faro-web-sdk@^1.4.0/dist/bundle/faro-web-sdk.iife.js"></script>
    <script src="https://unpkg.com/@grafana/faro-web-tracing@^1.4.0/dist/bundle/faro-web-tracing.iife.js"></script>

    <script>
      // --- 1. INICIALIZAÇÃO DO FARO ---
      var faro = GrafanaFaroWebSdk.initializeFaro({
        url: 'https://faro-collector-prod-sa-east-1.grafana.net/collect/e1a2f88c30e6e51ce17e7027fda40ae4', 
        app: {
          name: 'loja-frontend-prod',
          version: '3.0.0', // Versão nova para limpar o cache visual
          environment: 'production'
        },
        instrumentations: [
          new GrafanaFaroWebSdk.ConsoleInstrumentation(),
          new GrafanaFaroWebSdk.ErrorsInstrumentation(),
          new GrafanaFaroWebSdk.SessionInstrumentation(),
          // Instrumentação de Ações do Usuário
          new GrafanaFaroWebSdk.UserActionInstrumentation(),
          // Instrumentação de Tracing (Liga o Front ao Back)
          new GrafanaFaroWebTracing.TracingInstrumentation({
            propagationKey: 'traceparent', 
            cors: true 
          })
        ]
      });

      // --- 2. LÓGICA DO CLIQUE (MANUAL + AUTOMÁTICO) ---
      window.acao = (tipo) => {
          const endpoint = tipo === 'comprar' ? '/checkout' : '/simular_erro';
          const actionName = tipo === 'comprar' ? 'click_comprar' : 'click_gerar_erro';
          
          console.info(`🚀 [AÇÃO] Usuário iniciou: ${actionName}`);
          
          // --- FORÇANDO O ENVIO PARA O GRAFANA ---
          // Isso garante que apareça no painel de Eventos/Logs mesmo se o "User Action" falhar
          faro.api.pushEvent(actionName, { categoria: 'botao_interface' });
          
          document.getElementById('status').innerText = "Processando...";
          document.getElementById('status').style.color = "orange";

          fetch(endpoint, { method: 'POST' })
            .then(async (response) => {
                const data = await response.json();
                
                if (response.ok) {
                    document.getElementById('status').innerText = `✅ Sucesso! ID: ${data.id}`;
                    document.getElementById('status').style.color = "green";
                    
                    // Evento de Sucesso de Negócio
                    faro.api.pushEvent('compra_realizada', { 
                        pedido_id: String(data.id),
                        valor: '4500.00'
                    });
                } else {
                    throw new Error(data.msg || "Erro desconhecido");
                }
            })
            .catch(error => { 
                console.error("🔥 Erro capturado:", error);
                document.getElementById('status').innerText = `❌ Falha: ${error.message}`;
                document.getElementById('status').style.color = "red";
                
                // Envia o erro explicitamente
                faro.api.pushError(error, { context: actionName });
            });
      };
    </script>
</head>
<body>
    <div class="card">
        <h1>🛍️ Loja RUM v3.1</h1>
        <p>Monitoramento Avançado</p>
        
        <button class="btn-buy" 
                onclick="window.acao('comprar')" 
                data-faro-user-action-name="click_comprar">
            COMPRAR (PlayStation 5)
        </button>
        
        <button class="btn-error" 
                onclick="window.acao('erro')" 
                data-faro-user-action-name="click_gerar_erro">
            GERAR ERRO
        </button>
        
        <div id="status">Aguardando ação...</div>
        <div class="info">Dados enviados para Grafana Cloud</div>
    </div>
</body>
</html>
"""

@app.route('/')
def home():
    return RUM_HTML

@app.route('/checkout', methods=['POST'])
def checkout():
    # Inicia Span no Backend
    tracer = trace.get_tracer(__name__)
    
    with tracer.start_as_current_span("processar_compra_backend", attributes={"app.feature": "checkout"}) as span:
        try:
            logger.info("💳 Iniciando pagamento...")
            
            # Simulando processamento
            novo = Pedido(produto="PlayStation 5", status="PAGO", valor=4500.00, timestamp_epoch=time.time())
            db.session.add(novo)
            db.session.commit()
            
            logger.info(f"✅ Pedido {novo.id} salvo!")
            span.set_attribute("app.order_id", novo.id)
            
            return jsonify({"status": "sucesso", "id": novo.id})
            
        except Exception as e:
            logger.error(f"❌ Erro: {e}")
            span.record_exception(e)
            span.set_status(Status(StatusCode.ERROR))
            return jsonify({"status": "erro", "msg": str(e)}), 500

@app.route('/simular_erro', methods=['POST'])
def simular_erro():
    tracer = trace.get_tracer(__name__)
    
    with tracer.start_as_current_span("simulacao_falha_backend") as span:
        try:
            logger.error("⚠️ Simulando falha crítica...")
            raise Exception("Gateway Timeout (Erro Simulado)")
        except Exception as e:
            span.record_exception(e)
            span.set_status(Status(StatusCode.ERROR))
            return jsonify({"status": "erro_simulado", "msg": str(e)}), 500

if __name__ == '__main__':
    # A instrumentação real é feita pelo comando 'opentelemetry-instrument' no Dockerfile
    app.run(host='0.0.0.0', port=8080)
