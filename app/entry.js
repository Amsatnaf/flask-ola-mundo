import { BasicTracerProvider, SimpleSpanProcessor, ConsoleSpanExporter } from '@opentelemetry/sdk-trace-base';
import { OTLPTraceExporter } from '@opentelemetry/exporter-trace-otlp-http';
import { resourceFromAttributes } from '@opentelemetry/resources';
import { SemanticResourceAttributes } from '@opentelemetry/semantic-conventions';

function setupRUM(serviceName, collectorUrl) {
    console.log("☢️ Iniciando RUM (Modo Nuclear)...");

    const exporter = new OTLPTraceExporter({ url: collectorUrl });
    const consoleExporter = new ConsoleSpanExporter();
    
    // Processadores que queremos adicionar
    const p1 = new SimpleSpanProcessor(exporter);
    const p2 = new SimpleSpanProcessor(consoleExporter);

    const resource = resourceFromAttributes({
        [SemanticResourceAttributes.SERVICE_NAME]: serviceName,
        [SemanticResourceAttributes.SERVICE_VERSION]: '1.0.0'
    });

    const provider = new BasicTracerProvider({ resource });

    // --- A CIRURGIA ---
    try {
        // Tentativa 1: O jeito certo (provavelmente vai falhar)
        if (typeof provider.addSpanProcessor === 'function') {
            console.log("✅ Usando addSpanProcessor padrão");
            provider.addSpanProcessor(p1);
            provider.addSpanProcessor(p2);
        } 
        // Tentativa 2: Injeção direta na lista interna do MultiSpanProcessor
        else if (provider._activeSpanProcessor && Array.isArray(provider._activeSpanProcessor._spanProcessors)) {
            console.warn("⚠️ Injetando direto no Array _spanProcessors");
            provider._activeSpanProcessor._spanProcessors.push(p1);
            provider._activeSpanProcessor._spanProcessors.push(p2);
        }
        // Tentativa 3: Se tudo falhar, tenta achar onde os processadores estão escondidos
        else {
             console.error("❌ Estrutura desconhecida:", provider);
        }
    } catch (e) {
        console.error("Erro na injeção:", e);
    }

    provider.register();

    return provider.getTracer('rum-nuclear');
}

window.otel = { setupRUM };
