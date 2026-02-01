from flask import Flask

app = Flask(__name__)

# ==============================================================================
# CONFIGURAÇÃO RUM (REAL USER MONITORING) + LOGS INTEGRADOS
# Versão: 3.2.0 (Com correção de TraceFlags para Link no SigNoz)
# ==============================================================================
OTEL_RUM_CONFIG = """
<script type="module">
  // ---------------------------------------------------------
  // 1. IMPORTS DO OPENTELEMETRY (CDN)
  // ---------------------------------------------------------
  // Core e Tracing (v1.30.1)
  import { WebTracerProvider } from 'https://esm.sh/@opentelemetry/sdk-trace-web@1.30.1';
  import { SimpleSpanProcessor, ConsoleSpanExporter } from 'https://esm.sh/@opentelemetry/sdk-trace-base@1.30.1';
  import { Resource } from 'https://esm.sh/@opentelemetry/resources@1.30.1';
  import { SemanticResourceAttributes } from 'https://esm.sh/@opentelemetry/semantic-conventions@1.28.0';
  
  // Exporters e Logs (v0.57.2)
  import { OTLPTraceExporter } from 'https://esm.sh/@opentelemetry/exporter-trace-otlp-http@0.57.2';
  import { LoggerProvider, SimpleLogRecordProcessor } from 'https://esm.sh/@opentelemetry/sdk-logs@0.57.2'; // Usando sdk-logs correto
  import { OTLPLogExporter } from 'https://esm.sh/@opentelemetry/exporter-logs-otlp-http@0.57.2';
  import { SeverityNumber } from 'https://esm.sh/@opentelemetry/api-logs@0.57.2';

  console.log("🚀 Iniciando RUM v3.2.0 (Link de Logs Ativado)...");

  try {
      // -----------------------------------------------------
      // 2. DEFINIÇÃO DO RECURSO (QUEM É ESTE SERVIÇO?)
      // -----------------------------------------------------
      const resource = new Resource({
          [SemanticResourceAttributes.SERVICE_NAME]: 'flask-frontend-rum',
          [SemanticResourceAttributes.SERVICE_VERSION]: '3.2.0', // Versão nova
          'deployment.type': 'cdn_loading',
          'env': 'production'
      });

      // -----------------------------------------------------
      // 3. CONFIGURAÇÃO DE TRACES (LATÊNCIA)
      // -----------------------------------------------------
      const collectorTraceUrl = 'https://otel-collector.129-213-28-76.sslip.io/v1/traces';
      const traceExporter = new OTLPTraceExporter({ url: collectorTraceUrl });
      
      const tracerProvider = new WebTracerProvider({ resource });
      // Envia para o SigNoz
      tracerProvider.addSpanProcessor(new SimpleSpanProcessor(traceExporter));
      // Mostra no Console (F12) para debug
      tracerProvider.addSpanProcessor(new SimpleSpanProcessor(new ConsoleSpanExporter()));
      tracerProvider.register();

      const tracer = tracerProvider.getTracer('flask-rum-cdn');
      
      // INICIA O CRONÔMETRO (SPAN RAIZ)
      const rootSpan = tracer.startSpan('carregamento_via_cdn', {
          startTime: performance.timeOrigin
      });

      // -----------------------------------------------------
      // 4. CONFIGURAÇÃO DE LOGS (EVENTOS)
      // -----------------------------------------------------
      const collectorLogUrl = 'https://otel-collector.129-213-28-76.sslip.io/v1/logs';
      const logExporter = new OTLPLogExporter({ url: collectorLogUrl });
      
      const loggerProvider = new LoggerProvider({ resource });
      // SimpleLogRecordProcessor envia imediatamente (bom para testes)
      loggerProvider.addLogRecordProcessor(new SimpleLogRecordProcessor(logExporter));
      
      const logger = loggerProvider.getLogger('flask-frontend-logger');

      // -----------------------------------------------------
      // 5. FUNÇÃO MÁGICA DE ENVIO (COM LINK CORRIGIDO)
      // -----------------------------------------------------
      window.logToSigNoz = (message, severity = 'INFO') => {
          // Pega o contexto ATUAL do Trace (IDs)
          const ctx = rootSpan.spanContext();
          
          console.log(`🔗 [ENVIANDO] Log: "${message}" | TraceID: ${ctx.traceId}`);

          logger.emit({
              body: message,
              severityNumber: severity === 'ERROR' ? SeverityNumber.ERROR : SeverityNumber.INFO,
              severityText: severity,
              timestamp: new Date(),
              
              // --- O SEGREDO DO LINK ---
              traceId: ctx.traceId,     // ID do Rastreio
              spanId: ctx.spanId,       // ID do Span atual
              traceFlags: 1,            // 1 = SAMPLED (Obrigatório para o SigNoz indexar)
              // ------------------------

              attributes: {
                  'page.url': window.location.href,
                  'user_agent': navigator.userAgent,
                  'manual.trace_id': ctx.traceId // Backup para garantir
              }
          });
      };

      // -----------------------------------------------------
      // 6. GATILHOS (LISTENERS)
      // -----------------------------------------------------
      
      // Quando a página terminar de carregar
      window.addEventListener('load', () => {
          // 1. Envia o log "Sucesso" conectado ao trace
          window.logToSigNoz("Página totalmente carregada!", "INFO");
          
          // 2. Finaliza a contagem de tempo (Trace) com pequeno atraso
          // O atraso garante que o log saia antes do trace fechar
          setTimeout(() => {
              rootSpan.end();
              console.log("✅ Trace de carregamento finalizado.");
          }, 200);
      });

      // Captura erros de JavaScript automaticamente
      window.addEventListener('error', (e) => {
          window.logToSigNoz(`Erro JS Global: ${e.message}`, "ERROR");
      });

  } catch (e) {
      console.error("❌ Erro Crítico na Configuração RUM:", e);
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
        <title>RUM v3.2 - SigNoz</title>
        {OTEL_RUM_CONFIG}
        <style>
            body {{ font-family: 'Segoe UI', sans-serif; display: flex; flex-direction: column; justify-content: center; align-items: center; height: 100vh; background-color: #f4f6f8; margin: 0; }}
            .card {{ background: white; padding: 40px; border-radius: 12px; box-shadow: 0 4px 20px rgba(0,0,0,0.08); text-align: center; max-width: 450px; width: 100%; }}
            h1 {{ color: #2d3e50; margin-bottom: 10px; font-size: 24px; }}
            p {{ color: #6c757d; margin-bottom: 30px; }}
            
            .btn-group {{ display: flex; gap: 15px; justify-content: center; }}
            
            .btn {{ 
                padding: 12px 24px; 
                border: none; 
                border-radius: 8px; 
                cursor: pointer; 
                font-size: 14px; 
                font-weight: 600;
                transition: all 0.2s ease;
                display: flex; align-items: center; gap: 8px;
            }}
            
            .btn-info {{ background-color: #0066cc; color: white; }}
            .btn-info:hover {{ background-color: #0052a3; transform: translateY(-1px); }}
            
            .btn-error {{ background-color: #d93025; color: white; }}
            .btn-error:hover {{ background-color: #b31f16; transform: translateY(-1px); }}

            .status {{ margin-top: 20px; font-size: 12px; color: #aaa; }}
        </style>
    </head>
    <body>
        <div class="card">
            <h1>Monitoramento RUM v3.2 🚀</h1>
            <p>Os logs agora são vinculados ao Trace ID automaticamente.</p>
            
            <div class="btn-group">
                <button class="btn btn-info" onclick="window.logToSigNoz('Usuário interagiu com o botão INFO', 'INFO')">
                    📝 Gerar Log Info
                </button>
                
                <button class="btn btn-error" onclick="window.logToSigNoz('Simulação de Falha Crítica', 'ERROR')">
                    ⚠️ Gerar Erro
                </button>
            </div>
            
            <div class="status">Verifique o console (F12) para ver os IDs</div>
        </div>
    </body>
    </html>
    """

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
