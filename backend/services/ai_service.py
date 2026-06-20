import google.generativeai as genai
from config import Config
import logging

logger = logging.getLogger(__name__)

class AIService:
    _initialized = False

    @classmethod
    def initialize(cls):
        if not cls._initialized:
            try:
                Config.validate()
                genai.configure(api_key=Config.GEMINI_API_KEY)
                cls._initialized = True
                logger.info("Gemini AI successfully configured.")
            except Exception as e:
                logger.error(f"Error configuring Gemini AI: {str(e)}")
                raise e

    @classmethod
    def generate_content(cls, prompt, model_name="gemini-2.5-flash"):
        if not cls._initialized:
            cls.initialize()
        try:
            model = genai.GenerativeModel(model_name)
            response = model.generate_content(prompt)
            return response.text
        except Exception as e:
            logger.error(f"Gemini generation failure: {str(e)}")
            raise e
