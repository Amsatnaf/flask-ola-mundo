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
    Testa se a página carrega e se a versão v3.3.0 (Fix JS Hex->Bytes) está ativa.
    """
    # 1. Faz a requisição
    response = client.get('/')

    # 2. Verifica se o site está NO AR
    assert response.status_code == 200

    # 3. Verifica se o TÍTULO VISUAL foi atualizado
    # No app.py v3.3 colocamos: <h1>RUM v3.3: Hex -> Bytes 🛠️</h1>
    assert b"RUM v3.3" in response.data

    # 4. VERIFICAÇÃO TÉCNICA DE VERSÃO:
    # Garante que a variável de versão foi atualizada
    assert b"SERVICE_VERSION]: '3.3.0'" in response.data

    # 5. VERIFICAÇÃO DA CORREÇÃO (NOVO):
    # Verifica se a função 'hexToBytes' existe no código fonte da página.
    # Isso garante que a lógica de conversão que adicionamos está lá.
    assert b"function hexToBytes(hex)" in response.data
