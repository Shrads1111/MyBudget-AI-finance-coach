from flask import Blueprint, jsonify, g
from middleware.auth_middleware import token_required
from services.pattern_detection_service import PatternDetectionService

pattern_bp = Blueprint('patterns', __name__)

@pattern_bp.route('/api/analytics/patterns', methods=['GET'])
@token_required
def get_spending_patterns():
    patterns = PatternDetectionService.detect_patterns(g.uid)
    return jsonify(patterns), 200
