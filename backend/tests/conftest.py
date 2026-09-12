import pytest
from backend import config


@pytest.fixture(autouse=True)
def no_live_providers(monkeypatch):
    """Regression tests must never consume real credentials from the local .env."""
    monkeypatch.setattr(config, 'API_KEY', '')
    monkeypatch.setattr(config, 'BASE_URL', '')
    monkeypatch.setattr(config, 'DEPLOYMENT', '')
    monkeypatch.setattr(config, 'OCR_KEY', '')
    monkeypatch.setattr(config, 'OCR_ENDPOINT', '')
    monkeypatch.delenv('CREWAI_MODEL', raising=False)


@pytest.fixture
def anyio_backend():
    return 'asyncio'
