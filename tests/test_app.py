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
    Testa se a página carrega e se a versão v3.2.0 (com Link de Logs) está ativa.
    """
    # 1. Faz a requisição ao site
    response = client.get('/')

    # 2. Verifica se o site está NO AR (Código 200 OK)
    assert response.status_code == 200

    # 3. Verifica se o TÍTULO VISUAL mudou para a versão nova
    # No app.py colocamos: <h1>Monitoramento RUM v3.2 🚀</h1>
    # O 'b' é necessário porque o response.data vem em bytes.
    # Usamos uma parte do texto para facilitar.
    assert b"Monitoramento RUM v3.2" in response.data

    # 4. VERIFICAÇÃO TÉCNICA (A mais importante):
    # Garante que o código JavaScript contém a configuração da versão 3.2.0
    # Se essa linha falhar, significa que você esqueceu de atualizar o script do RUM.
    assert b"SERVICE_VERSION]: '3.2.0'" in response.data

    # 5. Verifica se a flag de correção de logs (TraceFlags: 1) está presente
    # Isso garante que a lógica de "Forçar Link" que criamos realmente existe no código.
    assert b"traceFlags: 1" in response.data
