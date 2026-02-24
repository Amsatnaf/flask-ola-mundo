FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY app/requirements.txt /app/

# Instalamos as bibliotecas de instrumentação junto com seu requirements
RUN pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir \
    opentelemetry-distro \
    opentelemetry-exporter-otlp \
    opentelemetry-instrumentation-flask \
    opentelemetry-instrumentation-logging \
    opentelemetry-instrumentation-sqlalchemy

# Instala os componentes básicos do OpenTelemetry
RUN opentelemetry-bootstrap -a install

COPY app/ /app/

EXPOSE 8080

# O comando agora usa o wrapper para injetar a telemetria (Logs + Traces)
CMD ["opentelemetry-instrument", "--logs_exporter", "otlp", "python", "app.py"]
