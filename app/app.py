from flask import Flask

app = Flask(__name__)

# Configuração RUM via CDN (Trace + Logs Integrados)
OTEL_RUM_CONFIG = """
<script type="module">
  // 1. Imports de Trace
  import { WebTracerProvider } from 'https://esm.sh/@opentelemetry/sdk-trace-web@1.18.1';
  import { OTLPTraceExporter } from 'https://esm.sh/@opentelemetry/exporter-trace-otlp-http@0.57.1';
  import { SimpleSpanProcessor, ConsoleSpanExporter } from 'https://esm.sh/@opentelemetry/sdk-trace-base@1.18.1';
  import { Resource } from 'https://esm.sh/@opentelemetry/resources@1.18.1';
  import { SemanticResourceAttributes } from 'https://esm.sh/@opentelemetry/semantic-conventions@1.27.0';

  // 2. Imports de LOGS (Novidade!)
  import { LoggerProvider, SimpleLogRecordProcessor } from 'https://esm.sh/@opentelemetry/sdk-logs@0.57.1';
  import { OTLPLogExporter } from 'https://esm.sh/@opentelemetry/exporter-logs-otlp-http@0.57.1';
  import { SeverityNumber } from 'https://esm.sh/@opentelemetry/api-logs@0.57.1';

  console.log("🚀 Iniciando RUM Profissional (Trace + Logs)...");

  try {
      // --- CONFIG COMUM (Resource) ---
      // Define quem é o serviço uma única vez para usar em Traces e Logs
      const resource = new Resource({
          [SemanticResourceAttributes.SERVICE_NAME]: 'flask-frontend-rum',
          [SemanticResourceAttributes.SERVICE_VERSION]: '2.0.0', // Versão atualizada
          'deployment.type': 'cdn_loading',
          'env': 'production'
      });

      // ==========================================
      // PARTE A: CONFIGURAÇÃO DE TRACES
      // ==========================================
      const collectorTraceUrl = 'https://otel-collector.129-213-28-76.sslip.io/v1/traces';
      const traceExporter = new OTLPTraceExporter({ url: collectorTraceUrl });
      
      const tracerProvider = new WebTracerProvider({ resource });
      tracerProvider.addSpanProcessor(new SimpleSpanProcessor(traceExporter));
      tracerProvider.addSpanProcessor(new SimpleSpanProcessor(new ConsoleSpanExporter())); // Debug local
      tracerProvider.register();

      const tracer = tracerProvider.getTracer('flask-rum-cdn');
      
      // Inicia o Trace Principal (Span Raiz)
      const rootSpan = tracer.startSpan('carregamento_via_cdn', {
          startTime: performance.timeOrigin
      });

      // ==========================================
      // PARTE B: CONFIGURAÇÃO DE LOGS (O Pulo do Gato)
      // ==========================================
      const collectorLogUrl = 'https://otel-collector.129-213-28-76.sslip.io/v1/logs'; // Note: /v1/logs
      const logExporter = new OTLPLogExporter({ url: collectorLogUrl });
      
      const loggerProvider = new LoggerProvider({ resource });
      // Usamos SimpleLogRecordProcessor para garantir envio imediato no teste
      loggerProvider.addLogRecordProcessor(new SimpleLogRecordProcessor(logExporter));
      
      const logger = loggerProvider.getLogger('flask-frontend-logger');

      // --- FUNÇÃO AUXILIAR PROFISSIONAL ---
      // Essa função envia o log para o SigNoz JÁ CONECTADO ao Trace ID atual
      window.logToSigNoz = (message, severity = 'INFO') => {
          
          // Pega o contexto do Span atual (Trace ID e Span ID)
          const spanContext = rootSpan.spanContext();

          logger.emit({
              body: message,
              severityNumber: severity === 'ERROR' ? SeverityNumber.ERROR : SeverityNumber.INFO,
              severityText: severity,
              timestamp: new Date(),
              // AQUI ESTÁ O SEGREDO: Injetamos o ID do Trace no Log
              traceId: spanContext.traceId,
              spanId: spanContext.spanId,
              attributes: {
                  'browser.language': navigator.language,
                  'page.url': window.location.href
              }
          });
          
          // Também mostra no console do navegador para debug
          console.log(`[SigNoz Sent] ${message}`);
      };

      // ==========================================
      // FINALIZAÇÃO DO CARREGAMENTO
      // ==========================================
      window.addEventListener('load', () => {
          // 1. Envia um Log dizendo que carregou
          window.logToSigNoz("Página totalmente carregada!", "INFO");
          
          // 2. Finaliza o Span (Trace)
          rootSpan.end();
          console.log(`%c [SUCESSO] Trace e Logs configurados`, 'color: #00ff00; background: #333; padding: 4px;');
      });

      // Captura erros globais e manda pro SigNoz
      window.addEventListener('error', (event) => {
          window.logToSigNoz(`Erro JS detectado: ${event.message}`, "ERROR");
      });

  } catch (e) {
      console.error("❌ Erro na configuração RUM:", e);
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
