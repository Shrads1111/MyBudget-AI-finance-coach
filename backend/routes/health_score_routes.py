from flask import Blueprint, jsonify, g
from middleware.auth_middleware import token_required
from services.health_score_service import HealthScoreService

health_score_bp = Blueprint('health_score', __name__)

@health_score_bp.route('/api/health-score', methods=['GET'])
@token_required
def get_health_score():
    score_data = HealthScoreService.calculate_health_score(g.uid)
    return jsonify(score_data), 200
