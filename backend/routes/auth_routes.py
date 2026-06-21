from flask import Blueprint, jsonify, request

# Stub authentication routes – only for UI compatibility. No real user storage.
auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/api/auth/signup', methods=['POST', 'GET'])
def signup():
    # In production the frontend uses Firebase SDK; this stub simply returns success.
    # Accept any payload; ignore validation for now.
    return jsonify({"message": "Signup stub successful"}), 201

@auth_bp.route('/api/auth/login', methods=['POST', 'GET'])
def login():
    # Return a dummy JWT token; the UI will replace it with the Firebase token.
    dummy_token = "dummy-token"
    return jsonify({"token": dummy_token}), 200
