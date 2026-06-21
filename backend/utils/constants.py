EXPENSE_CATEGORIES = [
    "Food",
    "Transport",
    "Subscriptions",
    "Entertainment",
    "Education",
    "Bills",
    "Income",
    "Other"
]

BUDGET_CATEGORIES = [
    "Food",
    "Transport",
    "Subscriptions",
    "Entertainment",
    "Education",
    "Bills",
    "Other"
]

INCOME_CATEGORIES = {
    "Income",
    "Salary",
    "Freelancing",
    "Refund",
    "Interest",
    "Bonus",
    "Other Income"
}

def is_income(category):
    if not category:
        return False
    return str(category).strip().title() in {c.title() for c in INCOME_CATEGORIES}

