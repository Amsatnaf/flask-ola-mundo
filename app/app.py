from flask import Flask

app = Flask(__name__)

# Configuração RUM via CDN (Sem Build Local)
# O navegador baixa as bibliotecas prontas do esm.sh
OTEL_RUM_CONFIG = """
<script type="module">
  // Importando direto da Internet (CDN)
  import { WebTracerProvider } from 'https://esm.sh/@opentelemetry/sdk-trace-web@1.18.1';
  import { OTLPTraceExporter } from 'https://esm.sh/@opentelemetry/exporter-trace-otlp-http@0.57.1';
  import { SimpleSpanProcessor, ConsoleSpanExporter } from 'https://esm.sh/@opentelemetry/sdk-trace-base@1.18.1';
  import { Resource } from 'https://esm.sh/@opentelemetry/resources@1.18.1';
  import { SemanticResourceAttributes } from 'https://esm.sh/@opentelemetry/semantic-conventions@1.27.0';

  console.log("🚀 Iniciando RUM via CDN...");

  try {
      // 1. Configura o Exportador (Para onde vai o dado)
      const collectorUrl = 'https://otel-collector.129-213-28-76.sslip.io/v1/traces';
      const exporter = new OTLPTraceExporter({ url: collectorUrl });

      // 2. Define o Resource (Quem sou eu)
      const resource = new Resource({
          [SemanticResourceAttributes.SERVICE_NAME]: 'flask-frontend-rum',
          [SemanticResourceAttributes.SERVICE_VERSION]: '1.0.0',
          'deployment.type': 'cdn_loading'
      });

      // 3. Cria o Provedor
      const provider = new WebTracerProvider({ resource });

      // 4. Adiciona os Processadores (Agora funciona porque é o código oficial)
      provider.addSpanProcessor(new SimpleSpanProcessor(exporter));
      provider.addSpanProcessor(new SimpleSpanProcessor(new ConsoleSpanExporter())); // Log no Console

      provider.register();

      // 5. Cria o Trace
      const tracer = provider.getTracer('flask-rum-cdn');
      const span = tracer.startSpan('carregamento_via_cdn', {
          startTime: performance.timeOrigin
      });

      window.addEventListener('load', () => {
          span.end();
          console.log(`%c [SUCESSO] Trace enviado para ${collectorUrl}`, 'color: #00ff00; background: #333; padding: 4px;');
      });

  } catch (e) {
      console.error("❌ Erro no RUM via CDN:", e);
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
        <title>RUM via CDN</title>
        {OTEL_RUM_CONFIG}
        <style>
            body {{ font-family: sans-serif; display: flex; justify-content: center; align-items: center; height: 100vh; background-color: #eef; margin: 0; }}
            .card {{ background: white; padding: 30px; border-radius: 10px; box-shadow: 0 5px 15px rgba(0,0,0,0.1); text-align: center; }}
            .badge {{ background: #6f42c1; color: white; padding: 5px 10px; border-radius: 15px; font-size: 0.8em; }}
        </style>
    </head>
    <body>
        <div class="card">
            <h1>Monitoramento via Internet 🌐</h1>
            <p>Usando ES Modules direto do CDN.</p>
            <span class="badge">Modo CDN</span>
        </div>
    </body>
    </html>
    """

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
