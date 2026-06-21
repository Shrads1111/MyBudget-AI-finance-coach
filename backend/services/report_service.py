import io
import datetime
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors
from services.analytics_service import AnalyticsService
from services.health_score_service import HealthScoreService
from services.pattern_detection_service import PatternDetectionService
# FirebaseService is imported lazily inside generate_pdf_report to avoid protobuf crash at import time.
import logging

logger = logging.getLogger(__name__)

class ReportService:
    @staticmethod
    def generate_pdf_report(uid, month=None):
        try:
            # 1. Fetch live user data
            if not month:
                month = datetime.datetime.utcnow().strftime("%Y-%m")
                
            from services.firebase_service import FirebaseService
            db = FirebaseService.get_db()
            user_doc = db.collection("users").document(uid).get()
            user_name = "User"
            user_email = ""
            if user_doc.exists:
                udata = user_doc.to_dict()
                user_name = udata.get("display_name", "Student")
                user_email = udata.get("email", "")

            summary_data = AnalyticsService.get_dashboard_summary(uid)
            health_data = HealthScoreService.calculate_health_score(uid)
            patterns_data = PatternDetectionService.detect_patterns(uid)

            # 2. Setup ReportLab PDF document
            buffer = io.BytesIO()
            doc = SimpleDocTemplate(
                buffer,
                pagesize=letter,
                rightMargin=40,
                leftMargin=40,
                topMargin=40,
                bottomMargin=40
            )

            story = []
            styles = getSampleStyleSheet()

            # Custom Paragraph styles
            title_style = ParagraphStyle(
                'ReportTitle',
                parent=styles['Normal'],
                fontName='Helvetica-Bold',
                fontSize=22,
                leading=26,
                textColor=colors.HexColor('#6366f1'), # Indigo primary glow
                spaceAfter=15
            )

            h1_style = ParagraphStyle(
                'SectionHeader',
                parent=styles['Normal'],
                fontName='Helvetica-Bold',
                fontSize=14,
                leading=18,
                textColor=colors.HexColor('#1f2937'),
                spaceBefore=12,
                spaceAfter=8,
                keepWithNext=True
            )

            body_style = ParagraphStyle(
                'BodyText',
                parent=styles['Normal'],
                fontName='Helvetica',
                fontSize=10,
                leading=14,
                textColor=colors.HexColor('#4b5563')
            )

            bold_body_style = ParagraphStyle(
                'BoldBodyText',
                parent=body_style,
                fontName='Helvetica-Bold'
            )

            # Title
            story.append(Paragraph("MyBudget &mdash; Monthly Financial Report", title_style))
            
            # Metadata Grid
            metadata_text = f"""
            <b>Statement Month:</b> {month} &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;
            <b>Prepared For:</b> {user_name} ({user_email}) &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;
            <b>Generated On:</b> {datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}
            """
            story.append(Paragraph(metadata_text, body_style))
            story.append(Spacer(1, 15))

            # 1. KPI Summaries Table
            kpi_elements = [
                ["Metric", "Value"],
                ["Total Expenses (Non-Income)", f"INR {summary_data['summary']['total_expenses']:,}"],
                ["Current Month Expenses", f"INR {summary_data['summary']['monthly_expenses']:,}"],
                ["Financial Health Score", f"{health_data['score']}/100 (Grade: {health_data['grade']})"],
                ["Active Savings Goals Count", str(summary_data['summary']['active_goals_count'])]
            ]
            
            kpi_table = Table(kpi_elements, colWidths=[200, 300])
            kpi_table.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#f3f4f6')),
                ('TEXTCOLOR', (0,0), (-1,0), colors.HexColor('#374151')),
                ('ALIGN', (0,0), (-1,-1), 'LEFT'),
                ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
                ('FONTSIZE', (0,0), (-1,-1), 10),
                ('BOTTOMPADDING', (0,0), (-1,-1), 6),
                ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#e5e7eb')),
            ]))
            story.append(Paragraph("Executive Summary", h1_style))
            story.append(kpi_table)
            story.append(Spacer(1, 15))

            # 2. Budget Utilization Summary Table
            story.append(Paragraph("Budget Limits & Utilization", h1_style))
            if summary_data.get("budget_utilization"):
                budget_elements = [["Category", "Limit (Cap)", "Spent Amount", "Remaining", "Utilization Ratio"]]
                for b in summary_data["budget_utilization"]:
                    budget_elements.append([
                        b["category"],
                        f"INR {b['limit']:,}",
                        f"INR {b['spent']:,}",
                        f"INR {b['remaining']:,}",
                        f"{b['utilization_percentage']}%"
                    ])
                
                budget_table = Table(budget_elements, colWidths=[110, 100, 100, 100, 90])
                budget_table.setStyle(TableStyle([
                    ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#f3f4f6')),
                    ('TEXTCOLOR', (0,0), (-1,0), colors.HexColor('#374151')),
                    ('ALIGN', (0,0), (-1,-1), 'LEFT'),
                    ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0,0), (-1,-1), 9),
                    ('BOTTOMPADDING', (0,0), (-1,-1), 5),
                    ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#e5e7eb')),
                ]))
                story.append(budget_table)
            else:
                story.append(Paragraph("No category budgets configured for this month.", body_style))
            story.append(Spacer(1, 15))

            # 3. Financial Health score details
            story.append(Paragraph(f"Financial Health score: {health_data['score']}/100", h1_style))
            score_text = f"<b>Grade:</b> {health_data['grade']} <br/>"
            score_text += "<b>Breakdown of Score Elements:</b><br/>"
            score_text += f"- Savings Rate (max 30): {health_data['breakdown']['savings']} <br/>"
            score_text += f"- Budget Discipline (max 25): {health_data['breakdown']['budget']} <br/>"
            score_text += f"- Savings Goal Progress (max 20): {health_data['breakdown']['goals']} <br/>"
            score_text += f"- Expense Stability (max 15): {health_data['breakdown']['stability']} <br/>"
            score_text += f"- Logging Consistency (max 10): {health_data['breakdown']['consistency']} <br/>"
            story.append(Paragraph(score_text, body_style))
            
            # Tips
            story.append(Spacer(1, 6))
            story.append(Paragraph("Health Score Advice:", bold_body_style))
            for rec in health_data.get("recommendations", []):
                story.append(Paragraph(f"&bull; {rec}", body_style))
            story.append(Spacer(1, 15))

            # 4. Spending Pattern Insights
            story.append(Paragraph("Spending Pattern Detections", h1_style))
            if patterns_data:
                for pat in patterns_data:
                    story.append(Paragraph(f"&bull; <b>[{pat.get('type','INFO').upper()}]</b> {pat['message']}", body_style))
            else:
                story.append(Paragraph("No unusual patterns detected this period.", body_style))
            story.append(Spacer(1, 15))

            # Footer footnote
            story.append(Paragraph("This monthly financial statement was generated automatically by the MyBudget AI engine.", ParagraphStyle('Foot', parent=body_style, fontSize=8, spaceBefore=30)))

            # Build document
            doc.build(story)
            buffer.seek(0)
            return buffer
        except Exception as e:
            logger.error(f"Error compiling PDF monthly report: {str(e)}")
            raise e
