from flask import Flask

app = Flask(__name__)

# Configuração RUM via CDN (Trace + Logs Integrados)
# Configuração RUM via CDN (Versões Alinhadas e Corrigidas)
OTEL_RUM_CONFIG = """
<script type="module">
  // IMPORTS (Mantidos iguais ao anterior)
  import { WebTracerProvider } from 'https://esm.sh/@opentelemetry/sdk-trace-web@1.30.1';
  import { SimpleSpanProcessor, ConsoleSpanExporter } from 'https://esm.sh/@opentelemetry/sdk-trace-base@1.30.1';
  import { Resource } from 'https://esm.sh/@opentelemetry/resources@1.30.1';
  import { SemanticResourceAttributes } from 'https://esm.sh/@opentelemetry/semantic-conventions@1.28.0';
  import { OTLPTraceExporter } from 'https://esm.sh/@opentelemetry/exporter-trace-otlp-http@0.57.2';
  import { LoggerProvider, SimpleLogRecordProcessor } from 'https://esm.sh/@opentelemetry/sdk-logs@0.57.2';
  import { OTLPLogExporter } from 'https://esm.sh/@opentelemetry/exporter-logs-otlp-http@0.57.2';
  import { SeverityNumber } from 'https://esm.sh/@opentelemetry/api-logs@0.57.2';

  console.log("🚀 Iniciando RUM (Correção de Link)...");

  try {
      const resource = new Resource({
          [SemanticResourceAttributes.SERVICE_NAME]: 'flask-frontend-rum',
          [SemanticResourceAttributes.SERVICE_VERSION]: '3.1.0', // Versão atualizada
          'deployment.type': 'cdn_loading',
          'env': 'production'
      });

      // --- TRACES ---
      const collectorTraceUrl = 'https://otel-collector.129-213-28-76.sslip.io/v1/traces';
      const traceExporter = new OTLPTraceExporter({ url: collectorTraceUrl });
      const tracerProvider = new WebTracerProvider({ resource });
      tracerProvider.addSpanProcessor(new SimpleSpanProcessor(traceExporter));
      tracerProvider.addSpanProcessor(new SimpleSpanProcessor(new ConsoleSpanExporter()));
      tracerProvider.register();
      const tracer = tracerProvider.getTracer('flask-rum-cdn');
      
      const rootSpan = tracer.startSpan('carregamento_via_cdn', { startTime: performance.timeOrigin });

      // --- LOGS ---
      const collectorLogUrl = 'https://otel-collector.129-213-28-76.sslip.io/v1/logs';
      const logExporter = new OTLPLogExporter({ url: collectorLogUrl });
      const loggerProvider = new LoggerProvider({ resource });
      loggerProvider.addLogRecordProcessor(new SimpleLogRecordProcessor(logExporter));
      const logger = loggerProvider.getLogger('flask-frontend-logger');

      // ========================================================
      // A CORREÇÃO ESTÁ AQUI EMBAIXO
      // ========================================================
      window.logToSigNoz = (message, severity = 'INFO') => {
          const ctx = rootSpan.spanContext();
          
          console.log(`🔗 [LINK CHECK] TraceID: ${ctx.traceId} | Flags: ${ctx.traceFlags}`);

          logger.emit({
              body: message,
              severityNumber: severity === 'ERROR' ? SeverityNumber.ERROR : SeverityNumber.INFO,
              severityText: severity,
              timestamp: new Date(),
              
              // 1. Passamos os IDs oficiais
              traceId: ctx.traceId,
              spanId: ctx.spanId,
              
              // 2. O PULO DO GATO: Passamos as Flags (Isso valida o Trace)
              traceFlags: ctx.traceFlags, 

              attributes: {
                  'page.url': window.location.href,
                  'user_agent': navigator.userAgent,
                  // 3. BACKUP: Gravamos os IDs também como texto simples
                  // Se o link oficial falhar, você verá estes campos na lista de atributos!
                  'manual.trace_id': ctx.traceId,
                  'manual.span_id': ctx.spanId
              }
          });
      };

      window.addEventListener('load', () => {
          window.logToSigNoz("Página totalmente carregada!", "INFO");
          setTimeout(() => { rootSpan.end(); }, 200);
      });

      window.addEventListener('error', (e) => {
          window.logToSigNoz(`Erro JS: ${e.message}`, "ERROR");
      });

  } catch (e) { console.error("❌ Erro RUM:", e); }
</script>
"""

@app.route('/')
def hello():
    return f"""
    <!DOCTYPE html>
    <html lang="pt-br">
    <head>
        <meta charset="UTF-8">
        <title>RUM Profissional</title>
        {OTEL_RUM_CONFIG}
        <style>
            body {{ font-family: 'Segoe UI', sans-serif; display: flex; flex-direction: column; justify-content: center; align-items: center; height: 100vh; background-color: #f0f2f5; margin: 0; }}
            .card {{ background: white; padding: 40px; border-radius: 12px; box-shadow: 0 8px 24px rgba(0,0,0,0.12); text-align: center; max-width: 400px; }}
            .btn {{ margin-top: 20px; padding: 10px 20px; background: #007bff; color: white; border: none; border-radius: 6px; cursor: pointer; font-size: 16px; transition: 0.2s; }}
            .btn:hover {{ background: #0056b3; }}
            .btn-error {{ background: #dc3545; }}
            .btn-error:hover {{ background: #a71d2a; }}
            h1 {{ color: #333; margin-bottom: 10px; }}
            p {{ color: #666; }}
        </style>
    </head>
    <body>
        <div class="card">
            <h1>Monitoramento via Internet 🌐</h1>
            <h1>Monitoramento Full 🚀</h1>
            <p>Trace ID e Logs estão conectados agora.</p>
            
            <button class="btn" onclick="window.logToSigNoz('Usuário clicou no botão de teste', 'INFO')">
                Gerar Log de Info
            </button>
            
            <button class="btn btn-error" onclick="window.logToSigNoz('Falha simulada pelo usuário', 'ERROR')">
                Gerar Log de Erro
            </button>
        </div>
    </body>
    </html>
    """

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
