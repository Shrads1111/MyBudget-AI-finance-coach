import os
from pathlib import Path
from dotenv import load_dotenv

# Load env variables from backend/.env
env_path = Path(__file__).resolve().parent / '.env'
load_dotenv(dotenv_path=env_path)

class Config:
    GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
    FIREBASE_PROJECT_ID = os.getenv('FIREBASE_PROJECT_ID', 'mybudget-15057')
    FLASK_ENV = os.getenv('FLASK_ENV', 'development')
    PORT = int(os.getenv('PORT', 5000))
    DEBUG = FLASK_ENV == 'development'
    
    # Paths
    BASE_DIR = Path(__file__).resolve().parent
    FIREBASE_KEY_PATH = BASE_DIR / 'firebase' / 'serviceAccountKey.json'
    LOG_DIR = BASE_DIR / 'logs'
    LOG_FILE = LOG_DIR / 'app.log'

    @classmethod
    def validate(cls):
        """Validate critical configuration variables"""
        missing = []
        if not cls.GEMINI_API_KEY:
            missing.append('GEMINI_API_KEY')
        if not cls.FIREBASE_PROJECT_ID:
            missing.append('FIREBASE_PROJECT_ID')
        if not cls.FIREBASE_KEY_PATH.exists():
            missing.append(f'serviceAccountKey.json (not found at {cls.FIREBASE_KEY_PATH})')
            
        if missing:
            raise ValueError(f"Missing required configuration variables or files: {', '.join(missing)}")
