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
# DICA: Substitua a URL do 'url' abaixo pela sua URL do Faro Collector se mudar
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
        .info { font-size: 12px; color: #888; margin-top: 10px; }
    </style>
    
    <script src="https://unpkg.com/@grafana/faro-web-sdk@^1.4.0/dist/bundle/faro-web-sdk.iife.js"></script>
    <script src="https://unpkg.com/@grafana/faro-web-tracing@^1.4.0/dist/bundle/faro-web-tracing.iife.js"></script>

    <script>
      // --- INICIALIZAÇÃO DO FARO ---
      var faro = GrafanaFaroWebSdk.initializeFaro({
        url: 'https://faro-collector-prod-sa-east-1.grafana.net/collect/e1a2f88c30e6e51ce17e7027fda40ae4', // SUA URL AQUI
        app: {
          name: 'loja-frontend-prod', // Nome padronizado
          version: '1.0.0',
          environment: 'production'
        },
        instrumentations: [
          // Instrumentações Padrão
          new GrafanaFaroWebSdk.ConsoleInstrumentation(),
          new GrafanaFaroWebSdk.ErrorsInstrumentation(),
          new GrafanaFaroWebSdk.SessionInstrumentation(),
          
          // --- CORREÇÃO 1: User Actions Ativadas ---
          new GrafanaFaroWebSdk.UserActionInstrumentation(),

          // --- CORREÇÃO 2: Tracing Conectado ---
          new GrafanaFaroWebTracing.TracingInstrumentation({
            propagationKey: 'traceparent', // Padrão W3C para conectar com o Python
            cors: true 
          })
        ]
      });

      // Função para lidar com os cliques
      window.acao = (tipo) => {
          const endpoint = tipo === 'comprar' ? '/checkout' : '/simular_erro';
          console.info(`🚀 [AÇÃO] Usuário iniciou: ${tipo.toUpperCase()}`);
          
          document.getElementById('status').innerText = "Processando...";
          document.getElementById('status').style.color = "orange";

          // O fetch gera automaticamente o span de rede
          fetch(endpoint, { method: 'POST' })
            .then(async (response) => {
                const data = await response.json();
                
                if (response.ok) {
                    document.getElementById('status').innerText = `✅ Sucesso! ID Pedido: ${data.id}`;
                    document.getElementById('status').style.color = "green";
                    
                    // Envia evento de sucesso customizado
                    faro.api.pushEvent('compra_sucesso', { valor: '4500.00', pedido_id: data.id });
                } else {
                    throw new Error(data.msg || "Erro desconhecido no servidor");
                }
            })
            .catch(error => { 
                console.error("🔥 Erro capturado no Frontend:", error);
                
                document.getElementById('status').innerText = `❌ Falha: ${error.message}`;
                document.getElementById('status').style.color = "red";
                
                // Envia o erro explicitamente para o Grafana
                faro.api.pushError(error, { type: 'network_error', context: 'checkout_flow' });
            });
      };
    </script>
</head>
<body>
    <div class="card">
        <h1>🛍️ Loja RUM</h1>
        <p>Monitoramento Full-Stack</p>
        
        <button class="btn-buy" 
                onclick="window.acao('comprar')" 
                data-faro-user-action-name="clique_comprar"> COMPRAR (PlayStation 5)
        </button>
        
        <button class="btn-error" 
                onclick="window.acao('erro')" 
                data-faro-user-action-name="clique_gerar_erro"> GERAR ERRO
        </button>
        
        <div id="status">Aguardando ação...</div>
        <div class="info">Abra o Console (F12) para ver os logs do Faro</div>
    </div>
</body>
</html>
"""

@app.route('/')
def home():
    return RUM_HTML

@app.route('/checkout', methods=['POST'])
def checkout():
    # Inicia o Span manual para detalhar o trace
    tracer = trace.get_tracer(__name__)
    
    # Atributos ricos para aparecer no Trace Waterfall
    span_attributes = {
        "http.method": "POST", 
        "db.system": "mysql",
        "app.feature": "checkout",
        "user.tier": "gold" # Exemplo de dado de negócio
    }
    
    with tracer.start_as_current_span("processar_compra_backend", attributes=span_attributes) as span:
        try:
            logger.info("💳 Iniciando processamento de pagamento...")
            
            # Simulando um "delay" de banco de dados para ficar visível no gráfico
            # time.sleep(0.1) 
            
            novo = Pedido(produto="PlayStation 5", status="PAGO", valor=4500.00, timestamp_epoch=time.time())
            db.session.add(novo)
            db.session.commit()
            
            logger.info(f"✅ Pedido {novo.id} salvo com sucesso!")
            
            # Adiciona o ID do pedido no Trace
            span.set_attribute("app.order_id", novo.id)
            
            return jsonify({"status": "sucesso", "id": novo.id})
            
        except Exception as e:
            logger.error(f"❌ Erro ao salvar pedido: {e}")
            span.record_exception(e)
            span.set_status(Status(StatusCode.ERROR))
            return jsonify({"status": "erro", "msg": str(e)}), 500

@app.route('/simular_erro', methods=['POST'])
def simular_erro():
    tracer = trace.get_tracer(__name__)
    
    with tracer.start_as_current_span("gateway_pagamento_falha") as span:
        try:
            logger.error("⚠️ Simulando falha crítica no Gateway...")
            # Forçando um erro
            raise Exception("Timeout: Gateway de Pagamento não respondeu em 3000ms")
        except Exception as e:
            span.record_exception(e)
            span.set_status(Status(StatusCode.ERROR))
            return jsonify({"status": "erro_simulado", "msg": str(e)}), 500

if __name__ == '__main__':
    # O ideal é rodar via 'opentelemetry-instrument', mas se rodar direto:
    app.run(host='0.0.0.0', port=8080)
