import pytest
from app.app import app

@pytest.fixture
def client():
    with app.test_client() as client:
        yield client

def test_app_structure_and_rum_injection(client):
    """
    Teste Genérico de Sanidade (Smoke Test).
    Valida se a aplicação responde e se os componentes CRÍTICOS do RUM estão presentes,
    independentemente da versão ou estratégia (Logs vs Events).
    """
    # 1. Faz a requisição
    response = client.get('/')
    
    # Decodifica os bytes para string para facilitar a busca
    html = response.data.decode('utf-8')

    # ------------------------------------------------------------------
    # CHECK 1: DISPONIBILIDADE
    # O site tem que carregar.
    # ------------------------------------------------------------------
    assert response.status_code == 200
    assert "<!DOCTYPE html>" in html

    # ------------------------------------------------------------------
    # CHECK 2: PRESENÇA DO OPENTELEMETRY
    # Não importa a versão, tem que ter imports do '@opentelemetry'.
    # Isso garante que o bloco <script> não foi apagado sem querer.
    # ------------------------------------------------------------------
    assert "@opentelemetry/sdk-trace-web" in html
    assert "@opentelemetry/resources" in html

    # ------------------------------------------------------------------
    # CHECK 3: CONFIGURAÇÃO DO SERVIDOR (COLLECTOR)
    # Verifica se o endpoint do SigNoz está configurado no código.
    # O teste passa se encontrar o domínio do seu collector.
    # ------------------------------------------------------------------
    assert "otel-collector.129-213-28-76.sslip.io" in html

    # ------------------------------------------------------------------
    # CHECK 4: IDENTIDADE DO SERVIÇO
    # Garante que o nome do serviço está correto (importante para achar no SigNoz)
    # ------------------------------------------------------------------
    assert "flask-frontend-rum" in html

    print("\n✅ O App está no ar e o script RUM está injetado corretamente.")
