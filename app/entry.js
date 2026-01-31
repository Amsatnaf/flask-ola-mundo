import * as api from '@opentelemetry/api';
import * as sdkTraceWeb from '@opentelemetry/sdk-trace-web';
import * as sdkTraceBase from '@opentelemetry/sdk-trace-base';
import * as exporterTraceOTLPHttp from '@opentelemetry/exporter-trace-otlp-http';
import * as resources from '@opentelemetry/resources';
import * as semanticConventions from '@opentelemetry/semantic-conventions';

// Disponibiliza tudo no objeto global "window.otel"
window.otel = {
  api,
  sdkTraceWeb,
  sdkTraceBase,
  exporterTraceOTLPHttp,
  resources,
  semanticConventions
};
