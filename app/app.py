from flask import Flask

app = Flask(__name__)

OTEL_RUM_CONFIG = """
<script type="module">
  import { WebTracerProvider } from 'https://esm.sh/@opentelemetry/sdk-trace-web@1.30.1';
  import { SimpleSpanProcessor, ConsoleSpanExporter } from 'https://esm.sh/@opentelemetry/sdk-trace-base@1.30.1';
  import { Resource } from 'https://esm.sh/@opentelemetry/resources@1.30.1';
  import { SemanticResourceAttributes } from 'https://esm.sh/@opentelemetry/semantic-conventions@1.28.0';
  import { OTLPTraceExporter } from 'https://esm.sh/@opentelemetry/exporter-trace-otlp-http@0.57.2';

  try {
      const resource = new Resource({
          [SemanticResourceAttributes.SERVICE_NAME]: 'flask-frontend-rum',
          'deployment.type': 'manual_test', // Mudei o nome pra facilitar achar
          'env': 'production'
      });

      const collectorTraceUrl = 'https://otel-collector.129-213-28-76.sslip.io/v1/traces';
      const traceExporter = new OTLPTraceExporter({ url: collectorTraceUrl });
      
      const tracerProvider = new WebTracerProvider({ resource });
      tracerProvider.addSpanProcessor(new SimpleSpanProcessor(traceExporter));
      tracerProvider.addSpanProcessor(new SimpleSpanProcessor(new ConsoleSpanExporter()));
      tracerProvider.register();

      const tracer = tracerProvider.getTracer('flask-rum-cdn');
      
      // Inicia o Trace
      window.rootSpan = tracer.startSpan('sessao_usuario_manual', { 
          startTime: performance.timeOrigin 
      });

      console.log("🔴 GRAVANDO TRACE... Você tem 15 segundos para clicar nos botões!");

      window.logToSigNoz = (message, severity = 'INFO') => {
          console.log(`🖱️ CLIQUE: "${message}"`);

          // Adiciona o evento ao Trace que está aberto
          window.rootSpan.addEvent(message, {
              'log.severity': severity,
              'user_action': 'click'
          });
          
          if (severity === 'ERROR') {
              window.rootSpan.setStatus({ code: 2, message: "Usuário reportou erro" });
              alert("Erro registrado! O Trace deve ficar VERMELHO no SigNoz.");
          } else {
              alert("Evento Info registrado!");
          }
      };

      // O GRANDE SEGREDO: Esperar 15 segundos antes de enviar
      setTimeout(() => {
          window.rootSpan.end();
          console.log("✅ FIM DA GRAVAÇÃO. Trace enviado para o SigNoz.");
          alert("Sessão finalizada! Agora vá olhar o SigNoz.");
      }, 15000); // 15 Segundos

  } catch (e) {
      console.error("Erro RUM:", e);
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
        <title>Teste Manual RUM</title>
        {OTEL_RUM_CONFIG}
        <style>
            body {{ font-family: sans-serif; text-align: center; padding: 50px; }}
            .btn {{ padding: 15px 30px; font-size: 18px; margin: 10px; cursor: pointer; }}
            .btn-info {{ background: #2196F3; color: white; border: none; }}
            .btn-error {{ background: #f44336; color: white; border: none; }}
        </style>
    </head>
    <body>
        <h1>Teste de Eventos (15 Segundos) ⏱️</h1>
        <p>A página está gravando. Clique nos botões abaixo antes do alerta final.</p>
        
        <button class="btn btn-info" onclick="window.logToSigNoz('Cliquei no Botão Azul', 'INFO')">
            1. Registrar Info
        </button>

        <button class="btn btn-error" onclick="window.logToSigNoz('Falha no Pagamento', 'ERROR')">
            2. Simular Erro
        </button>
    </body>
    </html>
    """

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
