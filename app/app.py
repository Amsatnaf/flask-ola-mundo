import time
from flask import Flask, jsonify

app = Flask(__name__)

# ... (Mantenha o bloco OTEL_RUM_CONFIG igualzinho ao anterior) ...
# Vou colocar aqui apenas a parte que mudou no JavaScript e no Python

OTEL_RUM_CONFIG = """
<script type="module">
  // ... (Imports iguais ao anterior) ...
  import { WebTracerProvider } from 'https://esm.sh/@opentelemetry/sdk-trace-web@1.30.1';
  import { SimpleSpanProcessor } from 'https://esm.sh/@opentelemetry/sdk-trace-base@1.30.1';
  import { Resource } from 'https://esm.sh/@opentelemetry/resources@1.30.1';
  import { SemanticResourceAttributes } from 'https://esm.sh/@opentelemetry/semantic-conventions@1.28.0';
  import { OTLPTraceExporter } from 'https://esm.sh/@opentelemetry/exporter-trace-otlp-http@0.57.2';

  try {
      const resource = new Resource({
          [SemanticResourceAttributes.SERVICE_NAME]: 'flask-frontend-rum',
          'deployment.type': 'production_real',
          'env': 'production'
      });

      const collectorTraceUrl = 'https://otel-collector.129-213-28-76.sslip.io/v1/traces';
      const traceExporter = new OTLPTraceExporter({ url: collectorTraceUrl });
      const tracerProvider = new WebTracerProvider({ resource });
      tracerProvider.addSpanProcessor(new SimpleSpanProcessor(traceExporter));
      tracerProvider.register();
      const tracer = tracerProvider.getTracer('flask-rum-cdn');

      // 1. Trace de Load
      const loadSpan = tracer.startSpan('page_load', { startTime: performance.timeOrigin });
      window.addEventListener('load', () => setTimeout(() => loadSpan.end(), 100));

      // 2. Função Inteligente
      window.realAction = (actionType) => {
          console.log(`Disparando ação: ${actionType}`);
          
          // Cria o trace do clique (RUM)
          const span = tracer.startSpan('user_interaction', { attributes: { 'action': actionType } });
          span.addEvent('Iniciando requisição ao backend...');

          // --- AQUI A MÁGICA: CHAMA O BACKEND DE VERDADE ---
          fetch('/checkout', { method: 'POST' })
            .then(response => {
                span.addEvent('Resposta do Backend Recebida');
                if(actionType === 'ERROR') throw new Error("Simulação de Erro");
                span.end(); // Sucesso
            })
            .catch(err => {
                span.setStatus({ code: 2, message: err.message });
                span.end(); // Erro
            });
      };

  } catch (e) { console.error(e); }
</script>
"""

@app.route('/')
def hello():
    return f"""
    <!DOCTYPE html>
    <html lang="pt-br">
    <head><meta charset="UTF-8"><title>Full Stack RUM</title>{OTEL_RUM_CONFIG}</head>
    <body style="font-family: sans-serif; text-align: center; padding: 50px;">
        <h1>Full Stack Monitor 🚀</h1>
        <p>RUM completo, Frontend e Backend</p>
        <button style="padding:15px; background:blue; color:white;" onclick="window.realAction('COMPRAR')">🛒 Comprar (POST)</button>
        <button style="padding:15px; background:red; color:white;" onclick="window.realAction('ERROR')">❌ Erro (POST)</button>
    </body>
    </html>
    """

# --- NOVA ROTA DO BACKEND ---
@app.route('/checkout', methods=['POST'])
def checkout_backend():
    # Simula um processamento de compra
    time.sleep(0.1) # Demora 100ms
    return jsonify({"status": "compra_realizada", "message": "O Python processou isso!"})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
