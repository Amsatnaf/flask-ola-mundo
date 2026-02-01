# 1. Importa o framework 'pytest', que é a ferramenta que vai rodar os testes
import pytest

# 2. Importa a variável 'app' (sua aplicação Flask) de dentro da pasta/arquivo 'app/app.py'
from app.app import app

# ---------------------------------------------------------------------------
# FIXTURE (PREPARAÇÃO)
# ---------------------------------------------------------------------------
# O @pytest.fixture indica que esta função prepara um recurso para ser usado nos testes.
@pytest.fixture
def client():
    # 3. Cria um contexto com o 'test_client()'. 
    # Isso simula um navegador web na memória, sem precisar abrir porta de internet.
    with app.test_client() as client:
        
        # 4. O comando 'yield' entrega esse cliente simulado para a função de teste.
        # O teste roda, e quando acabar, o sistema limpa a memória automaticamente.
        yield client

# ---------------------------------------------------------------------------
# O TESTE (EXECUÇÃO)
# ---------------------------------------------------------------------------
# Define a função de teste. O pytest reconhece ela porque começa com "test_".
# Ela recebe o 'client' que criamos ali em cima.
def test_home_page(client):
    """
    Docstring: Testa se a pagina inicial responde 200 OK 
    E se contém a correção crítica do RUM v3.1.0
    """
    
    # 5. AÇÃO: O cliente simulado faz um GET (acessa) a rota raiz ('/').
    # A resposta do servidor (HTML, Status Code, Headers) fica guardada na variável 'response'.
    response = client.get('/')

    # -----------------------------------------------------------------------
    # VALIDAÇÕES (ASSERTS) - Onde o teste passa ou falha
    # -----------------------------------------------------------------------

    # 6. Verifica o STATUS da resposta HTTP.
    # 200 significa "OK/Sucesso". Se fosse 404 (Não achou) ou 500 (Erro), o teste falharia aqui.
    assert response.status_code == 200

    # 7. Verifica se o texto "Monitoramento Full" existe dentro dos dados da resposta (response.data).
    # O 'b' antes das aspas indica que estamos procurando BYTES, não texto normal (string),
    # pois o Flask retorna o HTML cru em formato de bytes.
    assert b"Monitoramento Full" in response.data

    # 8. VERIFICAÇÃO DE VERSÃO (CRÍTICO):
    # Aqui procuramos exatamente pelo trecho de código JavaScript que define a versão.
    # Isso garante que o arquivo app.py está rodando a versão 3.1.0 com o fix dos logs.
    # Se alguém subir a versão 2.0.0 ou 3.0.0 antiga, esse teste falha e bloqueia o deploy.
    assert b"SERVICE_VERSION]: '3.1.0'" in response.data
    
    # 9. (Opcional) Verifica a mensagem de log no console.
    # Explicação do comando complexo abaixo:
    # A resposta original contém acentos UTF-8 (ç e ã) em bytes (\xc3\xa7 e \xc3\xa3).
    # O comando .replace() troca esses bytes estranhos por "ca" (ASCII simples).
    # Assim, podemos procurar por "Correcao" sem nos preocuparmos com erros de codificação.
    assert b"Iniciando RUM (Correcao de Link)" in response.data.replace(b'\xc3\xa7\xc3\xa3', b'ca')
