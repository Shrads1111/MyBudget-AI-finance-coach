import importlib
import logging
from config import Config

logger = logging.getLogger(__name__)

class FirebaseService:
    _initialized = False
    _db = None

    @classmethod
    def initialize(cls):
        if not cls._initialized:
            try:
                # Lazy import firebase libraries
                firebase_admin = importlib.import_module('firebase_admin')
                credentials = importlib.import_module('firebase_admin.credentials')
                firestore = importlib.import_module('firebase_admin.firestore')
                importlib.import_module('firebase_admin.auth')  # ensure auth module is loaded
                Config.validate()
                if not firebase_admin._apps:
                    cred = credentials.Certificate(str(Config.FIREBASE_KEY_PATH))
                    firebase_admin.initialize_app(cred, {
                        'projectId': Config.FIREBASE_PROJECT_ID
                    })
                cls._db = firestore.client()
                cls._initialized = True
                logger.info("Firebase Admin successfully initialized.")
            except Exception as e:
                # If firebase libraries cannot be imported (e.g., protobuf mismatch), fall back to dummy mode.
                cls._initialized = False
                cls._db = None
                logger.warning(f"Firebase initialization skipped due to error: {str(e)}")
                # Do not re‑raise; allow the app to continue in dev mode.

    @classmethod
    def get_db(cls):
        if not cls._initialized:
            # Attempt lazy init; if it fails, return None
            try:
                cls.initialize()
            except Exception:
                pass
        return cls._db

    @classmethod
    def verify_id_token(cls, id_token):
        # Ensure firebase is initialized; if not, verification cannot proceed.
        if not cls._initialized:
            try:
                cls.initialize()
            except Exception:
                raise Exception("Firebase services unavailable; token verification cannot be performed")
        try:
            # Import auth module directly — cannot rely on local var from initialize()
            auth = importlib.import_module('firebase_admin.auth')
            decoded_token = auth.verify_id_token(id_token)
            return decoded_token
        except Exception as e:
            logger.warning(f"Failed token verification: {str(e)}")
            raise e
