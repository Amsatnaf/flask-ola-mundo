import time
import os
import logging
from flask import Flask, jsonify, request
from flask_sqlalchemy import SQLAlchemy

# --- Imports OpenTelemetry (Backend) ---
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPTraceExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.semconv.resource import ResourceAttributes

# --- Instrumentadores ---
from opentelemetry.instrumentation.flask import FlaskInstrumentation
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentation

# 1. Definicao do Recurso (Signoz)
resource = Resource(attributes={
    ResourceAttributes.SERVICE_NAME: "flask-backend-oci",
    ResourceAttributes.DEPLOYMENT_ENVIRONMENT: "production",
    "cloud.provider": "oracle_oci",
    "db.system": "mysql_gcp"
})

# 2. Configurar Trace Provider
COLLECTOR_ENDPOINT = "https://otel-collector.129-213-28-76.sslip.io/v1/traces"

trace.set_tracer_provider(TracerProvider(resource=resource))
tracer = trace.get_tracer(__name__)

otlp_exporter = OTLPTraceExporter(endpoint=COLLECTOR_ENDPOINT)
span_processor = BatchSpanProcessor(otlp_exporter)
trace.get_tracer_provider().add_span_processor(span_processor)

app = Flask(__name__)

# 3. Instrumentar Flask
FlaskInstrumentation().instrument(app=app)

# 4. Configurar Banco de Dados (Secrets do K8s)
db_user = os.getenv("DB_USER", "root")
db_pass = os.getenv("DB_PASS", "senha")
db_host = os.getenv("DB_HOST", "127.0.0.1")
db_name = os.getenv("DB_NAME", "loja_rum")

app.config['SQLALCHEMY_DATABASE_URI'] = f'mysql+pymysql://{db_user}:{db_pass}@{db_host}/{db_name}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    'pool_recycle': 280,
    'pool_pre_ping': True
}

db = SQLAlchemy(app)
SQLAlchemyInstrumentation().instrument(engine=db.engine)

# Modelo
class Pedido(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    produto = db.Column(db.String(50))
    status = db.Column(db.String(20))
    valor = db.Column(db.Float)
    timestamp_epoch = db.Column(db.Float)

# Cria tabelas ao iniciar
with app.app_context():
    try:
        db.create_all()
        print(f"INFO: Conectado ao MySQL em {db_host}")
    except Exception as e:
        print(f"ERROR: Falha conexao DB: {e}")

# --- HTML FRONTEND (Versao ESTAVEL sem Import Maps) ---
RUM_HTML = """
<!DOCTYPE html>
<html lang="pt-br">
<head>
    <meta charset="UTF-8">
    <title>Loja Multi-Cloud Trace</title>
    
    <link rel="preconnect" href="https://esm.sh" crossorigin>

    <script type="module">
      // IMPORTANTE: Voltamos para URLs diretas para evitar erros de resolucao
      // O esm.sh resolve as dependencias internas automaticamente.
      
      import { propagation, context } from 'https://esm.sh/@opentelemetry/api@1.7.0';
      import { WebTracerProvider } from 'https://esm.sh/@opentelemetry/sdk-trace-web@1.30.1';
      import { BatchSpanProcessor } from 'https://esm.sh/@opentelemetry/sdk-trace-base@1.30.1';
      import { Resource } from 'https://esm.sh/@opentelemetry/resources@1.30.1';
      import { SemanticResourceAttributes } from 'https://esm.sh/@opentelemetry/semantic-conventions@1.28.0';
      import { OTLPTraceExporter } from 'https://esm.sh/@opentelemetry/exporter-trace-otlp-http@0.57.2';
      import { FetchInstrumentation } from 'https://esm.sh/@opentelemetry/instrumentation-fetch@0.34.0';
      import { W3CTraceContextPropagator } from 'https://esm.sh/@opentelemetry/core@1.30.1';

      try {
          console.log("Iniciando RUM...");
          
          const collectorUrl = 'https://otel-collector.129-213-28-76.sslip.io/v1/traces';
          
          const resource = new Resource({
              [SemanticResourceAttributes.SERVICE_NAME]: 'flask-frontend-rum',
              'client.browser': navigator.userAgent
          });

          const provider = new WebTracerProvider({ resource });
          
          // BatchSpanProcessor = Performance
          provider.addSpanProcessor(new BatchSpanProcessor(new OTLPTraceExporter({ url: collectorUrl })));
          
          // Propagador W3C = Conecta o Frontend ao Backend
          provider.register({ propagator: new W3CTraceContextPropagator() });

          // Instrumentar Fetch (AJAX)
          const fetchInstr = new FetchInstrumentation({
              propagateTraceHeaderCorsUrls: [/.+/],
          });
          fetchInstr.setTracerProvider(provider);

          const tracer = provider.getTracer('loja-frontend-tracer');
          
          // Disponibiliza o tracer globalmente para debug se precisar
          window.otelTracer = tracer;
          window.otelContext = context;
          window.otelPropagation = propagation;

          console.log("RUM Carregado com Sucesso!");

          // Funcao dos Botoes
          window.realAction = (actionType) => {
              console.log("Click detectado:", actionType);
              
              if (!tracer) {
                  alert("Erro: O sistema de RUM nao carregou corretamente.");
                  return;
              }

              const span = tracer.startSpan(`click_${actionType.toLowerCase()}`);
              
              // Executa o fetch dentro do contexto do span
              context.with(propagation.setSpan(context.active(), span), () => {
                  
                  const endpoint = actionType === 'COMPRAR' ? '/checkout' : '/simular_erro';
                  
                  fetch(endpoint, { method: 'POST' })
                    .then(r => {
                        if (!r.ok) throw new Error(r.statusText);
                        return r.json();
                    })
                    .then(data => {
                        console.log("Resposta Backend:", data);
                        span.setStatus({ code: 1 }); // OK
                        alert("Sucesso! ID: " + (data.id || 'OK'));
                    })
                    .catch(err => {
                        console.error("Erro na requisicao:", err);
                        span.recordException(err);
                        span.setStatus({ code: 2, message: err.message }); // ERROR
                        alert("Erro! Veja o console (F12).");
                    })
                    .finally(() => {
                        span.end();
                    });
              });
          };

      } catch (e) {
          console.error("Erro fatal ao iniciar OpenTelemetry:", e);
          alert("Erro ao carregar sistema de monitoramento.");
      }
    </script>
</head>
<body style="font-family: 'Segoe UI', sans-serif; text-align: center; padding: 50px; background-color: #f0f2f5;">
    <h1>🛒 Loja Multi-Cloud (Estável)</h1>
    <p>Frontend -> Backend (OCI) -> Database (GCP)</p>
    <div style="margin-top: 40px;">
        <button style="padding:15px 30px; background:#007bff; color:white; border:none; border-radius:5px; cursor:pointer; font-size:16px;" 
            onclick="window.realAction('COMPRAR')">🛍️ Fazer Compra</button>
        
        <button style="padding:15px 30px; background:#dc3545; color:white; border:none; border-radius:5px; cursor:pointer; font-size:16px; margin-left:15px;" 
            onclick="window.realAction('ERROR')">💣 Simular Erro</button>
    </div>
</body>
</html>
"""

@app.route('/')
def home():
    return RUM_HTML

@app.route('/checkout', methods=['POST'])
def checkout():
    with tracer.start_as_current_span("backend_checkout"):
        try:
            time.sleep(0.05)
            novo = Pedido(produto="Notebook Gamer", status="PAGO", valor=3500.00, timestamp_epoch=time.time())
            db.session.add(novo)
            db.session.commit()
            return jsonify({"status": "sucesso", "id": novo.id})
        except Exception as e:
            db.session.rollback()
            trace.get_current_span().record_exception(e)
            return jsonify({"status": "erro", "msg": str(e)}), 500

@app.route('/simular_erro', methods=['POST'])
def simular_erro():
    with tracer.start_as_current_span("backend_erro_simulado"):
        try:
            falha = Pedido(produto="Erro", status="FALHA", valor=0.0, timestamp_epoch=time.time())
            db.session.add(falha)
            db.session.commit()
            raise ValueError("Erro Forcado no Python OCI!")
        except Exception as e:
            trace.get_current_span().record_exception(e)
            trace.get_current_span().set_status(trace.Status(trace.StatusCode.ERROR))
            return jsonify({"status": "erro_capturado", "msg": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, threaded=True)
