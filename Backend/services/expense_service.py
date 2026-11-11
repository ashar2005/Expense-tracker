"""Domain logic and business calculations for ExpenseMate."""
from repositories.expense_repository import ExpenseRepository


class ExpenseService:
    def __init__(self, repository: ExpenseRepository = None):
        self.repo = repository or ExpenseRepository()

    def create_transaction(self, data):
        cat_name = data.get("category")
        cat_id = self.repo.get_category_id(cat_name)
        if not cat_id:
            raise ValueError(f"Category '{cat_name}' does not exist.")

        amount = float(data["amount"])
        t_type = str(data.get("type", "expense")).lower()
        t_date = data["date"]
        note = data.get("note") if data.get("note") is not None else data.get("description", "")

        tx_id = self.repo.add_transaction(t_type, amount, cat_id, t_date, note)
        alert = self.check_budget_alert(cat_name, t_date)
        return {"id": tx_id, "alert": alert}

    def check_budget_alert(self, category_name, date_str):
        if not category_name or not date_str:
            return None
        month = str(date_str)[:7]
        b_info = self.repo.get_budget_spending(category_name, month)
        if not b_info or b_info["limit"] <= 0:
            return None

        limit_val = float(b_info["limit"])
        spent_val = float(b_info["spent"])
        ratio = spent_val / limit_val

        if ratio >= 1.0:
            return {
                "level": "exceeded",
                "alert": True,
                "category": category_name,
                "spent": spent_val,
                "limit": limit_val,
                "message": f"{category_name} budget exceeded!"
            }
        elif ratio >= 0.8:
            return {
                "level": "warning",
                "alert": True,
                "category": category_name,
                "spent": spent_val,
                "limit": limit_val,
                "message": f"{category_name} budget warning threshold reached."
            }
        return None

    def get_summary(self, start=None, end=None):
        txs = self.repo.list_transactions(start=start, end=end)
        income = sum(t["amount"] for t in txs if t["type"].lower() == "income")
        expense = sum(t["amount"] for t in txs if t["type"].lower() == "expense")
        return {"income": income, "expense": expense, "balance": income - expense}