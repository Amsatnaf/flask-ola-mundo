import time
import os
import logging
from flask import Flask, jsonify, request
from flask_sqlalchemy import SQLAlchemy

# --- OPENTELEMETRY ---
# IMPORTANTE: Nao importamos mais os Exporters nem Providers.
# Deixamos a Auto-Instrumentacao do SigNoz (Annotation) cuidar disso.
from opentelemetry import trace

# Apenas pegamos o tracer global que o SigNoz ja configurou para nos
tracer = trace.get_tracer(__name__)

app = Flask(__name__)

# NOTA: Nao precisamos chamar FlaskInstrumentation().instrument()
# A Auto-Instrumentacao do SigNoz faz isso sozinha quando o Pod sobe.

# --- Configuração do Banco de Dados ---
# Lendo Secrets do K8s
db_user = os.getenv("DB_USER", "root")
db_pass = os.getenv("DB_PASS", "senha")
db_host = os.getenv("DB_HOST", "127.0.0.1")
db_name = os.getenv("DB_NAME", "loja_rum")

# Conexao Segura
app.config['SQLALCHEMY_DATABASE_URI'] = f'mysql+pymysql://{db_user}:{db_pass}@{db_host}/{db_name}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    'pool_recycle': 280,
    'pool_pre_ping': True
}

db = SQLAlchemy(app)

# NOTA: Nao precisamos chamar SQLAlchemyInstrumentation().instrument()
# O agente do SigNoz detecta o SQLAlchemy e instrumenta sozinho.

# --- Modelo ---
class Pedido(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    produto = db.Column(db.String(50))
    status = db.Column(db.String(20))
    valor = db.Column(db.Float)
    timestamp_epoch = db.Column(db.Float)

# Cria tabelas (resiliencia)
with app.app_context():
    try:
        db.create_all()
        print(f"INFO: DB Conectado em {db_host}")
    except Exception as e:
        print(f"ERRO: DB inacessivel: {e}")

# --- FRONTEND RUM (Mantido igual, pois roda no navegador) ---
RUM_HTML = """
<!DOCTYPE html>
<html lang="pt-br">
<head>
    <meta charset="UTF-8">
    <title>Loja SigNoz RUM</title>
    <link rel="preconnect" href="https://esm.sh" crossorigin>
    <script type="module">
      // Frontend RUM continua independente
      import { propagation, context } from 'https://esm.sh/@opentelemetry/api@1.7.0';
      import { WebTracerProvider } from 'https://esm.sh/@opentelemetry/sdk-trace-web@1.30.1';
      import { BatchSpanProcessor } from 'https://esm.sh/@opentelemetry/sdk-trace-base@1.30.1';
      import { Resource } from 'https://esm.sh/@opentelemetry/resources@1.30.1';
      import { SemanticResourceAttributes } from 'https://esm.sh/@opentelemetry/semantic-conventions@1.28.0';
      import { OTLPTraceExporter } from 'https://esm.sh/@opentelemetry/exporter-trace-otlp-http@0.57.2';
      import { FetchInstrumentation } from 'https://esm.sh/@opentelemetry/instrumentation-fetch@0.34.0';
      import { W3CTraceContextPropagator } from 'https://esm.sh/@opentelemetry/core@1.30.1';

      try {
          const collectorUrl = 'https://otel-collector.129-213-28-76.sslip.io/v1/traces';
          const resource = new Resource({
              [SemanticResourceAttributes.SERVICE_NAME]: 'flask-frontend-rum',
          });
          const provider = new WebTracerProvider({ resource });
          provider.addSpanProcessor(new BatchSpanProcessor(new OTLPTraceExporter({ url: collectorUrl })));
          provider.register({ propagator: new W3CTraceContextPropagator() });

          new FetchInstrumentation({ propagateTraceHeaderCorsUrls: [/.+/] }).setTracerProvider(provider);
          
          const tracer = provider.getTracer('frontend');
          window.realAction = (actionType) => {
              const span = tracer.startSpan(`click_${actionType.toLowerCase()}`);
              context.with(propagation.setSpan(context.active(), span), () => {
                  fetch(actionType === 'COMPRAR' ? '/checkout' : '/simular_erro', { method: 'POST' })
                    .then(r => r.json())
                    .then(d => { span.end(); alert(d.status); })
                    .catch(e => { span.recordException(e); span.end(); });
              });
          };
      } catch (e) { console.error(e); }
    </script>
</head>
<body style="font-family: sans-serif; text-align: center; padding: 50px;">
    <h1>🛒 Loja Integrada SigNoz</h1>
    <button style="padding:15px; background:blue; color:white;" onclick="window.realAction('COMPRAR')">Comprar</button>
    <button style="padding:15px; background:red; color:white;" onclick="window.realAction('ERROR')">Erro</button>
</body>
</html>
"""

@app.route('/')
def home():
    return RUM_HTML

@app.route('/checkout', methods=['POST'])
def checkout():
    # AQUI ESTA O SEGREDO:
    # O SigNoz ja iniciou um span 'HTTP POST /checkout'.
    # Nos criamos um FILHO dele manualmente.
    with tracer.start_as_current_span("processar_logica_negocio"):
        try:
            time.sleep(0.05) # Span Manual (50ms)
            
            # O Agente do SigNoz vai pegar essa chamada ao DB automaticamente
            # e criar o span "INSERT INTO..." como filho deste bloco.
            novo = Pedido(produto="Notebook", status="PAGO", valor=3500.0, timestamp_epoch=time.time())
            db.session.add(novo)
            db.session.commit()
            
            return jsonify({"status": "compra_sucesso", "id": novo.id})
        except Exception as e:
            db.session.rollback()
            return jsonify({"status": "erro", "msg": str(e)}), 500

@app.route('/simular_erro', methods=['POST'])
def simular_erro():
    with tracer.start_as_current_span("logica_falha"):
        try:
            # Tenta gravar
            falha = Pedido(produto="Erro", status="FALHA", valor=0.0, timestamp_epoch=time.time())
            db.session.add(falha)
            db.session.commit()
            raise ValueError("Erro Python Forcado!")
        except Exception as e:
            # O SigNoz pega a excecao automatica do Flask, mas registrar aqui ajuda no contexto
            trace.get_current_span().record_exception(e)
            return jsonify({"status": "erro_capturado", "msg": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, threaded=True)
