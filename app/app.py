import time
from flask import Flask, jsonify

app = Flask(__name__)

# CONFIGURAÇÃO OTIMIZADA DO HEADER
# 1. modulepreload: Baixa os scripts pesados em paralelo com o HTML.
# 2. importmap: Define apelidos e fixa versões para evitar conflitos e downloads duplicados.
OTEL_HEAD_SETUP = """
<link rel="preconnect" href="https://esm.sh" crossorigin>
<link rel="modulepreload" href="https://esm.sh/@opentelemetry/api@1.7.0">
<link rel="modulepreload" href="https://esm.sh/@opentelemetry/sdk-trace-web@1.30.1">
<link rel="modulepreload" href="https://esm.sh/@opentelemetry/exporter-trace-otlp-http@0.57.2">

<script type="importmap">
{
  "imports": {
    "@opentelemetry/api": "https://esm.sh/@opentelemetry/api@1.7.0",
    "@opentelemetry/sdk-trace-web": "https://esm.sh/@opentelemetry/sdk-trace-web@1.30.1",
    "@opentelemetry/sdk-trace-base": "https://esm.sh/@opentelemetry/sdk-trace-base@1.30.1",
    "@opentelemetry/resources": "https://esm.sh/@opentelemetry/resources@1.30.1",
    "@opentelemetry/semantic-conventions": "https://esm.sh/@opentelemetry/semantic-conventions@1.28.0",
    "@opentelemetry/exporter-trace-otlp-http": "https://esm.sh/@opentelemetry/exporter-trace-otlp-http@0.57.2",
    "@opentelemetry/instrumentation-fetch": "https://esm.sh/@opentelemetry/instrumentation-fetch@0.34.0",
    "@opentelemetry/instrumentation-xml-http-request": "https://esm.sh/@opentelemetry/instrumentation-xml-http-request@0.34.0",
    "@opentelemetry/core": "https://esm.sh/@opentelemetry/core@1.30.1"
  }
}
</script>
"""

OTEL_RUM_SCRIPT = """
<script type="module">
  // Agora podemos importar pelos nomes limpos (como se fosse local)
  // O navegador usa o importmap acima para resolver as URLs
  import { propagation, context } from '@opentelemetry/api';
  import { WebTracerProvider } from '@opentelemetry/sdk-trace-web';
  import { SimpleSpanProcessor, BatchSpanProcessor } from '@opentelemetry/sdk-trace-base';
  import { Resource } from '@opentelemetry/resources';
  import { SemanticResourceAttributes } from '@opentelemetry/semantic-conventions';
  import { OTLPTraceExporter } from '@opentelemetry/exporter-trace-otlp-http';
  import { FetchInstrumentation } from '@opentelemetry/instrumentation-fetch';
  import { XMLHttpRequestInstrumentation } from '@opentelemetry/instrumentation-xml-http-request';
  import { W3CTraceContextPropagator } from '@opentelemetry/core';

  try {
      // Configuração de Resource
      const resource = new Resource({
          [SemanticResourceAttributes.SERVICE_NAME]: 'flask-frontend-rum',
          'deployment.environment': 'production',
          'browser.platform': navigator.platform
      });

      // Configuração do Exportador (Batching é essencial para performance)
      const collectorTraceUrl = 'https://otel-collector.129-213-28-76.sslip.io/v1/traces';
      const traceExporter = new OTLPTraceExporter({ url: collectorTraceUrl });
      
      const tracerProvider = new WebTracerProvider({ resource });
      
      // BatchSpanProcessor espera acumular spans ou um tempo X antes de enviar
      // Isso evita travar a rede no carregamento inicial
      tracerProvider.addSpanProcessor(new BatchSpanProcessor(traceExporter, {
          maxExportBatchSize: 5,
          scheduledDelayMillis: 1000
      }));
      
      tracerProvider.register({
          propagator: new W3CTraceContextPropagator() // Força propagador W3C Global
      });

      // Instrumentações Automáticas
      const fetchInstr = new FetchInstrumentation({
          propagateTraceHeaderCorsUrls: [/.+/], // Cuidado em PROD, restrinja isso
          clearTimingResources: true,
      });
      
      const xhrInstr = new XMLHttpRequestInstrumentation({
          propagateTraceHeaderCorsUrls: [/.+/],
      });
      
      // Registrar instrumentações no provedor (algumas versões pedem isso explicitamente)
      fetchInstr.setTracerProvider(tracerProvider);
      xhrInstr.setTracerProvider(tracerProvider);

      const tracer = tracerProvider.getTracer('flask-rum-v2');

      // --- Lógica de Negócio RUM ---

      // Span de Page Load
      // Dica: Usar 'pageshow' garante execução mesmo se vier do cache b/f
      window.addEventListener('pageshow', () => {
          const loadSpan = tracer.startSpan('document_load', { 
            startTime: performance.timeOrigin 
          });
          // Pequeno delay para garantir que o ciclo de eventos terminou
          setTimeout(() => loadSpan.end(), 0);
      });

      window.realAction = (actionType) => {
          console.log(`Action Triggered: ${actionType}`);
          
          // Inicia span
          const span = tracer.startSpan(`user_interaction_${actionType.toLowerCase()}`);
          
          // Usar context.with para garantir que o fetch pegue o parent correto
          context.with(propagation.setSpan(context.active(), span), () => {
              
              fetch('/checkout', { method: 'POST' })
                .then(res => res.json())
                .then(data => {
                    span.addEvent('backend_response_received');
                    if(actionType === 'ERROR') throw new Error("Erro Simulado pelo Usuário");
                    console.log(data);
                    span.setStatus({ code: 1 }); // OK
                })
                .catch(err => {
                    span.recordException(err);
                    span.setStatus({ code: 2, message: err.message }); // ERROR
                })
                .finally(() => {
                    span.end();
                });
          });
      };
      
      console.log("RUM Monitor Loaded via ImportMap");

  } catch (e) { 
      console.error("RUM Initialization Failed:", e); 
  }
</script>
"""

@app.route('/')
def hello():
    return f"""
    <!DOCTYPE html>
    <html lang="pt-br">
    <head>
        <meta charset="UTF-8">
        <title>RUM ImportMap</title>
        {OTEL_HEAD_SETUP}
        {OTEL_RUM_SCRIPT}
    </head>
    <body style="font-family: sans-serif; text-align: center; padding: 50px;">
        <h1>Full Stack Monitor 🚀</h1>
        <p>RUM completo !!</p>
        <p>Frontend e Backend</p>
        <div style="margin-top: 20px;">
            <button style="padding:15px; background:blue; color:white; cursor:pointer;" onclick="window.realAction('COMPRAR')">🛒 Comprar</button>
            <button style="padding:15px; background:red; color:white; cursor:pointer;" onclick="window.realAction('ERROR')">❌ Gerar Erro</button>
        </div>
    </body>
    </html>
    """

@app.route('/checkout', methods=['POST'])
def checkout_backend():
    time.sleep(0.1)
    return jsonify({"status": "ok", "trace_id_received": "Verifique os logs do collector"})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
