import time
import os
import logging
from flask import Flask, jsonify, request
from flask_sqlalchemy import SQLAlchemy
from opentelemetry import trace

# Pega o tracer que o SigNoz injetou
tracer = trace.get_tracer(__name__)

app = Flask(__name__)

# Configurações de Banco (Lê das variáveis de ambiente do K8s)
db_user = os.getenv("DB_USER", "root")
db_pass = os.getenv("DB_PASS", "senha")
db_host = os.getenv("DB_HOST", "127.0.0.1")
db_name = os.getenv("DB_NAME", "loja_rum")

app.config['SQLALCHEMY_DATABASE_URI'] = f'mysql+pymysql://{db_user}:{db_pass}@{db_host}/{db_name}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {'pool_recycle': 280, 'pool_pre_ping': True}

db = SQLAlchemy(app)

class Pedido(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    produto = db.Column(db.String(50))
    status = db.Column(db.String(20))
    valor = db.Column(db.Float)
    timestamp_epoch = db.Column(db.Float)

# Tenta criar tabelas ao iniciar (se falhar, loga o erro mas não crasha o app)
with app.app_context():
    try:
        db.create_all()
        print(f"INFO: Conectado ao banco em {db_host}")
    except Exception as e:
        print(f"ERRO DE CONEXAO DB: {e}")

# --- HTML RUM (Otimizado) ---
RUM_HTML = """
<!DOCTYPE html>
<html lang="pt-br">
<head>
    <meta charset="UTF-8">
    <title>Teste Conexão DB</title>
    <script type="module">
      import { context, trace } from 'https://esm.sh/@opentelemetry/api@1.7.0';
      import { WebTracerProvider } from 'https://esm.sh/@opentelemetry/sdk-trace-web@1.30.1';
      import { BatchSpanProcessor } from 'https://esm.sh/@opentelemetry/sdk-trace-base@1.30.1';
      import { Resource } from 'https://esm.sh/@opentelemetry/resources@1.30.1';
      import { SemanticResourceAttributes } from 'https://esm.sh/@opentelemetry/semantic-conventions@1.28.0';
      import { OTLPTraceExporter } from 'https://esm.sh/@opentelemetry/exporter-trace-otlp-http@0.57.2';
      import { FetchInstrumentation } from 'https://esm.sh/@opentelemetry/instrumentation-fetch@0.34.0';
      import { W3CTraceContextPropagator } from 'https://esm.sh/@opentelemetry/core@1.30.1';

      const provider = new WebTracerProvider({
          resource: new Resource({ [SemanticResourceAttributes.SERVICE_NAME]: 'flask-frontend-teste' })
      });
      provider.addSpanProcessor(new BatchSpanProcessor(new OTLPTraceExporter({ 
          url: 'https://otel-collector.129-213-28-76.sslip.io/v1/traces' 
      })));
      provider.register({ propagator: new W3CTraceContextPropagator() });
      
      new FetchInstrumentation({ propagateTraceHeaderCorsUrls: [/.+/] }).setTracerProvider(provider);
      const tracer = provider.getTracer('frontend-teste');

      window.acao = (tipo) => {
          const span = tracer.startSpan(`click_${tipo}`);
          context.with(trace.setSpan(context.active(), span), () => {
              fetch('/checkout', { method: 'POST' })
                .then(r => r.json())
                .then(d => { alert(d.status + " - ID: " + d.id); span.end(); })
                .catch(e => { alert("Erro: " + e); span.end(); });
          });
      };
    </script>
</head>
<body style="padding: 50px; text-align: center;">
    <h1>🧪 Ambiente de Teste</h1>
    <button onclick="window.acao('teste_db')" style="padding: 20px; font-size: 20px;">TESTAR BANCO AGORA</button>
</body>
</html>
"""

@app.route('/')
def home():
    return RUM_HTML

@app.route('/checkout', methods=['POST'])
def checkout():
    # Cria span filho manualmente
    with tracer.start_as_current_span("teste_insercao_banco"):
        try:
            # O SQLAlchemy instrumentado pelo SigNoz vai criar o span do INSERT automaticamente
            novo = Pedido(produto="Teste Conexao", status="OK", valor=1.0, timestamp_epoch=time.time())
            db.session.add(novo)
            db.session.commit()
            return jsonify({"status": "sucesso_total", "id": novo.id})
        except Exception as e:
            trace.get_current_span().record_exception(e)
            return jsonify({"status": "erro_backend", "msg": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, threaded=True)
