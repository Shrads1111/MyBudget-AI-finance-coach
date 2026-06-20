from functools import wraps
from flask import request, g
from services.firebase_service import FirebaseService
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
            decoded_token = FirebaseService.verify_id_token(token)
            g.uid = decoded_token['uid']
            g.user_email = decoded_token.get('email', '')
            g.user_name = decoded_token.get('name', '')
        except Exception as e:
            logger.warning(f"Unauthorized access attempt: {str(e)}")
            raise APIError("Invalid or expired authorization token", status_code=401)
            
        return f(*args, **kwargs)
    return decorated
