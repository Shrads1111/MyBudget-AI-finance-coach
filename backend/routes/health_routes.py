from flask import Blueprint, jsonify

# Simple health endpoint used by the frontend
health_bp = Blueprint('health', __name__)

@health_bp.route('/api/health', methods=['GET'])
def health_check():
    try:
        from services.firebase_service import FirebaseService
        firebase_status = "initialized" if FirebaseService._initialized else "failed"
    except Exception:
        firebase_status = "failed"
    return jsonify({
        "status": "healthy",
        "firebase": firebase_status
    }), 200
