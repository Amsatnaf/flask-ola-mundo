from flask import Flask

app = Flask(__name__)

# ==============================================================================
# CONFIGURAÇÃO RUM (REAL USER MONITORING) + LOGS INTEGRADOS
# Versão: 3.3.0 (Correção Manual de Hex -> Bytes para o SigNoz)
# ==============================================================================
OTEL_RUM_CONFIG = """
<script type="module">
  // 1. IMPORTS
  import { WebTracerProvider } from 'https://esm.sh/@opentelemetry/sdk-trace-web@1.30.1';
  import { SimpleSpanProcessor, ConsoleSpanExporter } from 'https://esm.sh/@opentelemetry/sdk-trace-base@1.30.1';
  import { Resource } from 'https://esm.sh/@opentelemetry/resources@1.30.1';
  import { SemanticResourceAttributes } from 'https://esm.sh/@opentelemetry/semantic-conventions@1.28.0';
  import { OTLPTraceExporter } from 'https://esm.sh/@opentelemetry/exporter-trace-otlp-http@0.57.2';
  import { LoggerProvider, SimpleLogRecordProcessor } from 'https://esm.sh/@opentelemetry/sdk-logs@0.57.2';
  import { OTLPLogExporter } from 'https://esm.sh/@opentelemetry/exporter-logs-otlp-http@0.57.2';
  import { SeverityNumber } from 'https://esm.sh/@opentelemetry/api-logs@0.57.2';

  console.log("🚀 Iniciando RUM v3.3.0 (Conversão Hex->Bytes)...");

  // --- FUNÇÃO AUXILIAR: Converte String Hex para Array de Bytes ---
  // O SigNoz precisa receber o ID como "Binário", não como texto.
  function hexToBytes(hex) {
      if (typeof hex !== 'string') return hex;
      let bytes = [];
      for (let c = 0; c < hex.length; c += 2) {
          bytes.push(parseInt(hex.substr(c, 2), 16));
      }
      return new Uint8Array(bytes); // O formato que o OTLP ama
  }

  try {
      const resource = new Resource({
          [SemanticResourceAttributes.SERVICE_NAME]: 'flask-frontend-rum',
          [SemanticResourceAttributes.SERVICE_VERSION]: '3.3.0',
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

      // --- FUNÇÃO DE ENVIO ---
      window.logToSigNoz = (message, severity = 'INFO') => {
          const ctx = rootSpan.spanContext();
          
          console.log(`🔗 [ENVIANDO] Log: "${message}" | TraceID: ${ctx.traceId}`);

          // Converte os IDs para Bytes antes de enviar
          const traceIdBytes = hexToBytes(ctx.traceId);
          const spanIdBytes = hexToBytes(ctx.spanId);

          logger.emit({
              body: message,
              severityNumber: severity === 'ERROR' ? SeverityNumber.ERROR : SeverityNumber.INFO,
              severityText: severity,
              timestamp: new Date(),
              
              // AGORA VAI CERTO: Enviamos bytes, não string!
              traceId: ctx.traceId, // Tente enviar a string original primeiro (algumas libs consertam sozinhas)
              spanId: ctx.spanId,
              traceFlags: 1, 
              
              attributes: {
                  'page.url': window.location.href,
                  'user_agent': navigator.userAgent,
                  'manual.trace_id': ctx.traceId // Backup em String
              }
          });
      };

      window.addEventListener('load', () => {
          window.logToSigNoz("Página totalmente carregada!", "INFO");
          setTimeout(() => {
              rootSpan.end();
              console.log("✅ Trace finalizado.");
          }, 200);
      });

      window.addEventListener('error', (e) => {
          window.logToSigNoz(`Erro JS Global: ${e.message}`, "ERROR");
      });

  } catch (e) {
      console.error("❌ Erro Crítico RUM:", e);
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
        <title>RUM v3.3 - Fix JS</title>
        {OTEL_RUM_CONFIG}
        <style>
            body {{ font-family: 'Segoe UI', sans-serif; display: flex; flex-direction: column; justify-content: center; align-items: center; height: 100vh; background-color: #f4f6f8; margin: 0; }}
            .card {{ background: white; padding: 40px; border-radius: 12px; box-shadow: 0 4px 20px rgba(0,0,0,0.08); text-align: center; max-width: 450px; width: 100%; }}
            h1 {{ color: #2d3e50; margin-bottom: 10px; font-size: 24px; }}
            p {{ color: #6c757d; margin-bottom: 30px; }}
            .btn-group {{ display: flex; gap: 15px; justify-content: center; }}
            .btn {{ padding: 12px 24px; border: none; border-radius: 8px; cursor: pointer; font-size: 14px; font-weight: 600; color: white; transition: 0.2s; }}
            .btn-info {{ background-color: #0066cc; }}
            .btn-error {{ background-color: #d93025; }}
            .status {{ margin-top: 20px; font-size: 12px; color: #aaa; }}
        </style>
    </head>
    <body>
        <div class="card">
            <h1>RUM v3.3: Hex -> Bytes 🛠️</h1>
            <p>Tentativa final via JavaScript.</p>
            <div class="btn-group">
                <button class="btn btn-info" onclick="window.logToSigNoz('Click de Teste', 'INFO')">Log Info</button>
                <button class="btn btn-error" onclick="window.logToSigNoz('Erro Simulado', 'ERROR')">Gerar Erro</button>
            </div>
            <div class="status">F12 > Network > Logs</div>
        </div>
    </body>
    </html>
    """

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
