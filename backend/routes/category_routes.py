from flask import Blueprint, request, jsonify, g
from middleware.auth_middleware import token_required
from services.category_service import CategoryService

category_bp = Blueprint('categories', __name__)


@category_bp.route('/api/categories', methods=['GET'])
@token_required
def get_categories():
    """Returns default categories merged with user's custom categories."""
    categories = CategoryService.get_categories(g.uid)
    return jsonify(categories), 200


@category_bp.route('/api/categories', methods=['POST'])
@token_required
def add_category():
    """Creates a new custom category for the authenticated user."""
    data = request.get_json() or {}
    name = data.get("name", "").strip()
    categories = CategoryService.add_category(g.uid, name)
    return jsonify(categories), 201
