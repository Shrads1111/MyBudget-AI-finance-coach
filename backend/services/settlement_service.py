import logging

logger = logging.getLogger(__name__)

class SettlementService:
    @staticmethod
    def simplify_debts(balances: dict) -> list:
        """
        Standard greedy debt simplification algorithm to minimize total transactions.
        - Input: dict mapping member UID to float balance (positive means they are owed, negative means they owe).
        - Output: list of dicts with keys 'from', 'to', and 'amount' representing optimized settlements.
        """
        # Round balances to 2 decimal places
        rounded_balances = {m: round(float(bal), 2) for m, bal in balances.items()}

        debtors = [] # Negative balances (owes money)
        creditors = [] # Positive balances (is owed money)

        for m, bal in rounded_balances.items():
            if bal < -0.01:
                debtors.append({"member": m, "amount": -bal})
            elif bal > 0.01:
                creditors.append({"member": m, "amount": bal})

        # Sort to simplify matching
        debtors.sort(key=lambda x: x["amount"], reverse=True)
        creditors.sort(key=lambda x: x["amount"], reverse=True)

        settlements = []
        d_idx = 0
        c_idx = 0

        while d_idx < len(debtors) and c_idx < len(creditors):
            deb = debtors[d_idx]
            cred = creditors[c_idx]

            settled_amount = min(deb["amount"], cred["amount"])
            if settled_amount > 0.01:
                settlements.append({
                    "from": deb["member"],
                    "to": cred["member"],
                    "amount": round(settled_amount, 2)
                })

            deb["amount"] -= settled_amount
            cred["amount"] -= settled_amount

            if deb["amount"] <= 0.01:
                d_idx += 1
            if cred["amount"] <= 0.01:
                c_idx += 1

        return settlements
