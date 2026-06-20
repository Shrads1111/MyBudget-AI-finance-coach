from flask import Blueprint, request, jsonify, g
from middleware.auth_middleware import token_required
from services.simulator_service import SimulatorService

simulator_bp = Blueprint('simulator', __name__)

@simulator_bp.route('/api/ai/simulate', methods=['POST'])
@token_required
def simulate_scenario():
    data = request.get_json() or {}
    query = data.get("query")
    if not query:
        return jsonify({
            "error": True,
            "message": "Field 'query' is required"
        }), 400

    simulation = SimulatorService.simulate(g.uid, query)
    return jsonify(simulation), 200
