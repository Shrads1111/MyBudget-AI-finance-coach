from flask import Blueprint, send_file, request, g
from middleware.auth_middleware import token_required
from services.report_service import ReportService

report_bp = Blueprint('reports', __name__)

@report_bp.route('/api/reports/monthly', methods=['GET'])
@token_required
def get_monthly_report():
    month = request.args.get('month') # Optional YYYY-MM
    pdf_buffer = ReportService.generate_pdf_report(g.uid, month)
    
    # Format standard output filename
    filename = f"MyBudget_Statement_{month or 'current'}.pdf"
    
    return send_file(
        pdf_buffer,
        mimetype='application/pdf',
        as_attachment=True,
        download_name=filename
    )
