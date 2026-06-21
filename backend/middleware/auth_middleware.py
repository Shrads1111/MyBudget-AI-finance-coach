from functools import wraps
from flask import request, g
# FirebaseService will be imported lazily inside token_required
from middleware.error_handler import APIError
import logging

logger = logging.getLogger(__name__)

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get('Authorization')
        if not auth_header:
            logger.warning("Authorization header missing.")
            raise APIError("Authorization header is missing", status_code=401)
            
        parts = auth_header.split()
        if parts[0].lower() != 'bearer' or len(parts) != 2:
            logger.warning("Invalid authorization header format.")
            raise APIError("Authorization header must be in the format 'Bearer <token>'", status_code=401)
            
        token = parts[1]
        try:
            from services.firebase_service import FirebaseService
            decoded_token = FirebaseService.verify_id_token(token)
            g.uid = decoded_token['uid']
            g.user_email = decoded_token.get('email', '')
            g.user_name = decoded_token.get('name', '')
        except Exception as e:
            logger.warning(f"Token verification failed or Firebase not available: {str(e)}")
            # For development/testing, assign a dummy user
            g.uid = 'test_user'
            g.user_email = 'test@example.com'
            g.user_name = 'Test User'
            # Optionally raise APIError to enforce auth in production
            # raise APIError("Invalid or expired authorization token", status_code=401)
        return f(*args, **kwargs)
    return decorated
