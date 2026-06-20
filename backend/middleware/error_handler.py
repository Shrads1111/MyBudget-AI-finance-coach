from flask import jsonify
from werkzeug.exceptions import HTTPException
import logging

logger = logging.getLogger(__name__)

class APIError(Exception):
    def __init__(self, message, status_code=400, payload=None):
        super().__init__()
        self.message = message
        self.status_code = status_code
        self.payload = payload

    def to_dict(self):
        rv = dict(self.payload or ())
        rv['error'] = True
        rv['message'] = self.message
        return rv

def register_error_handlers(app):
    @app.errorhandler(APIError)
    def handle_api_error(error):
        response = jsonify(error.to_dict())
        response.status_code = error.status_code
        logger.warning(f"APIError: {error.message} (status: {error.status_code})")
        return response

    @app.errorhandler(HTTPException)
    def handle_http_exception(error):
        response = jsonify({
            'error': True,
            'message': error.description
        })
        response.status_code = error.code
        logger.warning(f"HTTPException: {error.description} (status: {error.code})")
        return response

    @app.errorhandler(Exception)
    def handle_generic_exception(error):
        logger.error(f"Unhandled Exception: {str(error)}", exc_info=True)
        response = jsonify({
            'error': True,
            'message': 'An internal server error occurred.'
        })
        response.status_code = 500
        return response
