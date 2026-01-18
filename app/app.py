from flask import Flask

app = Flask(__name__)

@app.route('/')
def hello():
   ##return 'Olá, mundo! 👋', 200
   return 'Olá, CI - CD com Rancher Fleet e GitHub! 🚀', 200
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
