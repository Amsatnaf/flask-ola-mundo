from flask import Flask
from prometheus_flask_exporter import PrometheusMetrics # <--- ADICIONAR ISSO

app = Flask(__name__)
metrics = PrometheusMetrics(app) # <--- ADICIONAR ISSO (Liga o monitoramento)

# Opcional: Adicionar informações estáticas
metrics.info('app_info', 'Application info', version='1.0.3')

@app.route('/')
def hello():
<<<<<<< HEAD
   ##return 'Olá, mundo! 👋', 200
   return 'Olá, CI - CD com Rancher Fleet e GitHub! 🚀', 200
=======
  ##return 'Olá, mundo! 👋', 200
    return 'Olá, CI - CD com Rancher Fleet e GitHub - Coloquei metricas de monitoramento! 🚀', 200

>>>>>>> nova-mensagem
if __name__ == '__main__':
    # Importante: host 0.0.0.0 para funcionar no Docker
    app.run(host='0.0.0.0', port=8080)
