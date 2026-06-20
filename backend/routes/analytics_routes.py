from flask import Blueprint, jsonify, g
from middleware.auth_middleware import token_required
from services.analytics_service import AnalyticsService

analytics_bp = Blueprint('analytics', __name__)

@analytics_bp.route('/api/dashboard/summary', methods=['GET'])
@token_required
def get_dashboard_summary():
    summary = AnalyticsService.get_dashboard_summary(g.uid)
    return jsonify(summary), 200
