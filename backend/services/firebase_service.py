import firebase_admin
from firebase_admin import credentials, firestore, auth
from config import Config
import logging

logger = logging.getLogger(__name__)

class FirebaseService:
    _initialized = False
    _db = None

    @classmethod
    def initialize(cls):
        if not cls._initialized:
            try:
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
                logger.error(f"Error initializing Firebase Admin: {str(e)}")
                raise e

    @classmethod
    def get_db(cls):
        if not cls._initialized:
            cls.initialize()
        return cls._db

    @classmethod
    def verify_id_token(cls, id_token):
        if not cls._initialized:
            cls.initialize()
        try:
            decoded_token = auth.verify_id_token(id_token)
            return decoded_token
        except Exception as e:
            logger.warning(f"Failed token verification: {str(e)}")
            raise e
