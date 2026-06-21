# google.generativeai is imported lazily inside methods to avoid
# protobuf C-extension crash on Python 3.14 at import time.
from config import Config
import logging

logger = logging.getLogger(__name__)

class AIService:
    _initialized = False

    @classmethod
    def initialize(cls):
        if not cls._initialized:
            try:
                import google.generativeai as genai
                Config.validate()
                genai.configure(api_key=Config.GEMINI_API_KEY)
                cls._initialized = True
                logger.info("Gemini AI successfully configured.")
            except Exception as e:
                logger.error(f"Error configuring Gemini AI: {str(e)}")
                raise e

    @classmethod
    def generate_content(cls, prompt, model_name="gemini-2.5-flash"):
        import google.generativeai as genai
        if not cls._initialized:
            cls.initialize()
        
        models_to_try = [model_name]
        # Append fallback model if it's not already the primary model
        if "gemini-flash-lite-latest" not in models_to_try:
            models_to_try.append("gemini-flash-lite-latest")
            
        last_error = None
        for current_model in models_to_try:
            try:
                logger.info(f"Attempting Gemini generation with model: {current_model}")
                model = genai.GenerativeModel(current_model)
                response = model.generate_content(prompt)
                return response.text
            except Exception as e:
                logger.warning(f"Gemini generation failed for model {current_model}: {str(e)}")
                last_error = e
        
        logger.error("All Gemini models failed to generate content.")
        raise last_error
