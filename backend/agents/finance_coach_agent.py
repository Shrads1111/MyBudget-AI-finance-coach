from services.expense_service import ExpenseService
from services.group_service import GroupService
from services.firebase_service import FirebaseService
import logging

logger = logging.getLogger(__name__)

class FinanceCoachAgent:
    @staticmethod
    def analyze(uid):
        """
        Provides student-focused financial suggestions (hostel budgeting, pocket money tracking, splits, courses).
        """
        try:
            # Gather user profile context, groups, and expenses
            expenses = ExpenseService.get_expenses(uid, limit=100)["expenses"]
            
            # Check groups to see if they split flat bills
            db = FirebaseService.get_db()
            groups_docs = db.collection("group_budgets").where("members", "array_contains", uid).stream()
            group_count = len(list(groups_docs))

            # Student pocket money estimation (if they have an "Income" category transaction)
            income_txns = [float(e["amount"]) for e in expenses if e["category"] == "Income"]
            estimated_pocket_money = sum(income_txns) if income_txns else 10000.0 # Default fallback student budget

            food_spend = sum(float(e["amount"]) for e in expenses if e["category"] == "Food")
            edu_spend = sum(float(e["amount"]) for e in expenses if e["category"] == "Education")

            student_tips = []

            # Tip 1: Pocket money management
            if not income_txns:
                student_tips.append(
                    "You haven't recorded recurring pocket money or stipend. "
                    "Log it as an 'Income' category transaction to help track your monthly allowance limits."
                )
            else:
                student_tips.append(
                    f"Estimated monthly allowance: ₹{estimated_pocket_money:.2f}. "
                    "Try the 50/30/20 rule: 50% for hostel mess & rent, 30% for canteen & hangs, 20% for savings."
                )

            # Tip 2: Hostel mess and food costs
            if food_spend > 3000:
                student_tips.append(
                    f"You spent ₹{food_spend:.2f} on food. Eating outside hostel mess or ordering online is a major drain. "
                    "Set a rule of ordering food only on weekends to keep canteen costs low."
                )

            # Tip 3: Semester splits
            if group_count == 0:
                student_tips.append(
                    "You are not in any split groups yet. "
                    "Create a 'Flatmates Rent/Bills' group under MyBudget to split internet, electricity, and room grocery bills seamlessly."
                )
            else:
                student_tips.append(
                    f"Active sharing groups: {group_count}. Keep up the splits! "
                    "Splitting subscription costs like Spotify or Netflix student pack can save up to ₹150/month."
                )

            # Tip 4: Semester planning
            if edu_spend == 0:
                student_tips.append(
                    "Plan ahead for semester books, stationery, and certification fees. "
                    "Adding ₹500/month to an 'Education' budget avoids sudden cash crunches before exams."
                )
            else:
                student_tips.append(
                    f"Education investments this period: ₹{edu_spend:.2f}. Good job on investing in learning!"
                )

            return {
                "agent": "Finance Coach Agent",
                "status": "Success",
                "estimated_pocket_money": estimated_pocket_money,
                "active_group_shares": group_count,
                "student_tips": student_tips
            }
        except Exception as e:
            logger.error(f"FinanceCoachAgent error: {str(e)}")
            return {
                "agent": "Finance Coach Agent",
                "status": "Error",
                "error_message": str(e)
            }
