from flask import Blueprint, jsonify, g
from middleware.auth_middleware import token_required
from services.goal_planner_service import GoalPlannerService

goal_planner_bp = Blueprint('goal_planner', __name__)

@goal_planner_bp.route('/api/goals/<id>/planner', methods=['GET'])
@token_required
def get_goal_plan(id):
    plan = GoalPlannerService.get_goal_plan(g.uid, id)
    return jsonify(plan), 200
