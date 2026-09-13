import os
from pathlib import Path
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]

def reload():
    global DATA, BASE_URL, API_KEY, DEPLOYMENT, OCR_ENDPOINT, OCR_KEY, CREWAI_MODEL, DEMO_DATA
    load_dotenv(ROOT / '.env', override=True)
    DATA = Path(os.getenv('DOSSIER_DATA_DIR', './.local-data'))
    if not DATA.is_absolute():
        DATA = ROOT / DATA
    BASE_URL = os.getenv('AZURE_OPENAI_BASE_URL', '').strip()
    API_KEY = os.getenv('AZURE_OPENAI_API_KEY', '').strip()
    DEPLOYMENT = os.getenv('AZURE_OPENAI_CHAT_DEPLOYMENT', '').strip()
    OCR_ENDPOINT = os.getenv('AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT', '').strip().rstrip('/')
    OCR_KEY = os.getenv('AZURE_DOCUMENT_INTELLIGENCE_KEY', '').strip()
    CREWAI_MODEL = os.getenv('CREWAI_MODEL', '').strip()
    DEMO_DATA = os.getenv('DOSSIER_DEMO_DATA', 'false').lower() == 'true'

reload()

def azure_ready():
    return bool(os.getenv('AZURE_OPENAI_BASE_URL', '').strip() and 
                os.getenv('AZURE_OPENAI_API_KEY', '').strip() and 
                os.getenv('AZURE_OPENAI_CHAT_DEPLOYMENT', '').strip())
