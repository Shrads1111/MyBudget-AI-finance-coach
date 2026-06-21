from flask import Blueprint, request, jsonify, g
from middleware.auth_middleware import token_required
from services.expense_service import ExpenseService

expense_bp = Blueprint('expenses', __name__)

@expense_bp.route('/api/expenses', methods=['POST'])
@token_required
def create_expense():
    data = request.get_json() or {}
    # Validate allowed fields
    from utils.validator import Validator
    allowed_fields = ['amount', 'category', 'date', 'description', 'account_id', 'type']
    Validator.validate_allowed_fields(data, allowed_fields)
    # Validate required fields via service validators will handle amount, category, date
    # Ensure amount is positive and rounded (handled in Validator.validate_amount)
    # No further checks here
    expense = ExpenseService.create_expense(g.uid, data)
    return jsonify(expense), 201

@expense_bp.route('/api/expenses', methods=['GET'])
@token_required
def get_expenses():
    category = request.args.get('category')
    month = request.args.get('month') # YYYY-MM
    year = request.args.get('year') # YYYY
    sort_by = request.args.get('sort_by', 'date')
    sort_order = request.args.get('sort_order', 'desc')
    
    try:
        # Validate pagination params
        from utils.validator import Validator
        limit_raw = request.args.get('limit', 10)
        offset_raw = request.args.get('offset', 0)
        limit = Validator.validate_positive_int(limit_raw, 'limit')
        offset = Validator.validate_positive_int(offset_raw, 'offset')
        # Validate sorting params
        sort_by_raw = request.args.get('sort_by', 'date')
        sort_order_raw = request.args.get('sort_order', 'desc')
        sort_by, sort_order = Validator.validate_sort_params(sort_by_raw, sort_order_raw, allowed_sort_fields=['date', 'amount', 'category'])
    except ValueError:
        limit = 10
        offset = 0
        
    result = ExpenseService.get_expenses(
        uid=g.uid,
        category=category,
        month=month,
        year=year,
        sort_by=sort_by,
        sort_order=sort_order,
        limit=limit,
        offset=offset
    )
    return jsonify(result), 200

@expense_bp.route('/api/expenses/<id>', methods=['GET'])
@token_required
def get_expense(id):
    expense = ExpenseService.get_expense_by_id(g.uid, id)
    return jsonify(expense), 200

@expense_bp.route('/api/expenses/<id>', methods=['PUT'])
@token_required
def update_expense(id):
    data = request.get_json() or {}
    # Validate allowed fields for update
    from utils.validator import Validator
    allowed_fields = ['amount', 'category', 'date', 'description', 'account_id', 'type']
    Validator.validate_allowed_fields(data, allowed_fields)
    # Validate pagination and sort params are handled in get_expenses
    # Individual field validations are performed in service update
    expense = ExpenseService.update_expense(g.uid, id, data)
    return jsonify(expense), 200

@expense_bp.route('/api/expenses/<id>', methods=['DELETE'])
@token_required
def delete_expense(id):
    result = ExpenseService.delete_expense(g.uid, id)
    return jsonify(result), 200

@expense_bp.route('/api/transactions/import-pdf', methods=['POST'])
@token_required
def import_pdf_transactions():
    """
    Receives an uploaded PDF file, validates it, extracts text,
    parses transactions using AI, runs duplicate detection, and returns the result.
    """
    import os
    import logging
    from services.pdf_import_service import PDFImportService

    logger = logging.getLogger(__name__)

    # 1. Validate file exists in request
    if 'file' not in request.files:
        return jsonify({"error": "No file uploaded"}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No file selected"}), 400

    # Validate file extension
    if not file.filename.lower().endswith('.pdf'):
        return jsonify({"error": "Only PDF files are supported"}), 400

    # 2. Validate file size (max 20 MB)
    try:
        file.seek(0, os.SEEK_END)
        file_size = file.tell()
        file.seek(0)  # Reset pointer to beginning of file
        if file_size > 20 * 1024 * 1024:
            return jsonify({"error": "File size exceeds the 20 MB limit"}), 400
    except Exception as e:
        return jsonify({"error": f"Failed to check file size: {str(e)}"}), 400

    # 3. Save to a temporary file
    temp_path = None
    try:
        # Create temp folder inside workspace if it doesn't exist
        temp_dir = os.path.join(os.path.dirname(__file__), "..", "temp")
        os.makedirs(temp_dir, exist_ok=True)
        
        # Use a unique identifier to avoid conflicts
        import uuid
        temp_path = os.path.join(temp_dir, f"import_{g.uid}_{uuid.uuid4().hex}.pdf")
        file.save(temp_path)

        # 4. Extract text
        extracted_text = PDFImportService.extract_text(temp_path)
        if not extracted_text or len(extracted_text.strip()) < 10:
            return jsonify({"error": "Unable to extract transaction data from this PDF."}), 422

        # 5. Parse transactions via AI
        parsed = PDFImportService.parse_transactions(extracted_text)
        if not parsed:
            return jsonify({"error": "No transactions found."}), 422

        # 6. Detect duplicates
        analyzed = PDFImportService.detect_duplicates(g.uid, parsed)

        return jsonify({
            "success": True,
            "transactions": analyzed
        }), 200

    except Exception as e:
        logger.error(f"Error handling PDF import: {str(e)}")
        return jsonify({"error": f"Internal server error: {str(e)}"}), 500

    finally:
        # 7. Secure cleanup of temporary file
        if temp_path and os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except Exception as ce:
                logger.error(f"Cleanup error: failed to delete {temp_path}: {str(ce)}")
