FROM python:3.11-slim

# Evita arquivos .pyc e logs presos no buffer
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# 1. Instalação de Dependências
# (Lembre-se: O requirements.txt JÁ deve ter as libs do opentelemetry que passamos antes)
COPY app/requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# 2. [NOVO] Bootstrap do OpenTelemetry
# Esse comando varre suas bibliotecas instaladas (Flask, SQLAlchemy) e 
# instala automaticamente os plugins de instrumentação corretos para elas.
RUN opentelemetry-bootstrap -a install

# 3. Copia o código da aplicação
COPY app/ /app/

EXPOSE 8080

# 4. [NOVO] O Comando de Execução "Mágico"
# Em vez de rodar direto o python, rodamos o instrumentador que envolve o python.
# Isso garante que os traces sejam enviados sem você precisar mexer em cada função do código.
CMD ["opentelemetry-instrument", \
     "--traces_exporter", "otlp", \
     "--metrics_exporter", "otlp", \
     "--service_name", "flask-grafana-loja-loja", \
     "python", "app.py"]
