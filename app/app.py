from flask import Flask

app = Flask(__name__)

@app.route('/')
def hello():
   ##return 'Olá, mundo! 👋', 200
   return 'Olá, Rancher Fleet! Agora vai.. Testes de automatização! 🚀', 200 - ERRO

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
