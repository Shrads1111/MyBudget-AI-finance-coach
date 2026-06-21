from flask import Blueprint, jsonify, request, g
from middleware.auth_middleware import token_required
from services.account_service import AccountService
from middleware.error_handler import APIError
from utils.validator import Validator
import logging

logger = logging.getLogger(__name__)

account_bp = Blueprint('accounts', __name__)

@account_bp.route('/api/accounts', methods=['GET'])
@token_required
def get_accounts():
    uid = g.uid
    accounts = AccountService.get_accounts(uid)
    return jsonify(accounts), 200

@account_bp.route('/api/accounts', methods=['POST'])
@token_required
def create_account():
    uid = g.uid
    data = request.get_json() or {}
    # Validate allowed fields
    from utils.validator import Validator
    allowed_fields = ['name', 'type', 'initial_balance', 'last_details']
    Validator.validate_allowed_fields(data, allowed_fields)
    # Validate required name
    name = data.get('name')
    if not name or not str(name).strip():
        raise APIError('Account name is required', status_code=400)
    # Validate type if provided
    acc_type = data.get('type')
    if acc_type is not None and not str(acc_type).strip():
        raise APIError('Account type must be a non-empty string', status_code=400)
    # Validate initial_balance if provided
    if 'initial_balance' in data:
        try:
            bal = float(data['initial_balance'])
            if bal < 0:
                raise APIError('initial_balance must be non-negative', status_code=400)
            data['initial_balance'] = round(bal, 2)
        except (ValueError, TypeError):
            raise APIError('initial_balance must be a valid number', status_code=400)
    account = AccountService.create_account(uid, data)
    return jsonify(account), 201

@account_bp.route('/api/accounts/<account_id>', methods=['DELETE'])
@token_required
def delete_account(account_id):
    uid = g.uid
    result = AccountService.delete_account(uid, account_id)
    return jsonify(result), 200
