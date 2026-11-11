"""Flask REST server (Business Logic Layer entry point)."""
import calendar
from datetime import datetime
from flask import Flask, Response, g, jsonify, request
from flask_cors import CORS

# Robust import resolution for both root and Backend execution
try:
    from Backend import csv_utils, models
    from Backend.database import get_connection, init_db
except ImportError:
    import csv_utils
    import models
    from database import get_connection, init_db

DEFAULT_DB = "expensemate.db"


def clean_budget(b):
    """Ensure budget objects have numeric amount/spent/remaining fields."""
    amount = float(b.get("amount") or b.get("limit") or 0.0)
    spent = float(b.get("spent") or 0.0)
    remaining = amount - spent
    percent = (spent / amount * 100) if amount > 0 else 0.0
    return {
        "id": b.get("id"),
        "category": b.get("category"),
        "amount": amount,
        "limit": amount,
        "spent": spent,
        "remaining": remaining,
        "percent": percent,
        "alert": spent > amount if amount > 0 else False
    }


def clean_category(c):
    """Ensure category summary objects have numeric amount fields."""
    return {
        "category": c.get("category"),
        "amount": float(c.get("amount") or c.get("total") or 0.0)
    }


def create_app(db_path=DEFAULT_DB):
    app = Flask(__name__)
    CORS(app)
    init_db(db_path)

    def conn():
        if "conn" not in g:
            g.conn = get_connection(db_path)
        return g.conn

    @app.teardown_appcontext
    def close_conn(_exc):
        connection = g.pop("conn", None)
        if connection is not None:
            connection.close()

    @app.errorhandler(ValueError)
    def bad_request(exc):
        return jsonify({"error": str(exc), "message": str(exc)}), 400

    @app.route("/health")
    @app.route("/api/health")
    def health():
        return jsonify({"status": "ok"})

    # ----- ADAPTIVE MAINTENANCE: Multi-Currency Converter -----
    @app.route("/convert", methods=["POST"])
    @app.route("/api/convert", methods=["POST"])
    def convert_currency():
        """Adapt ExpenseMate to support multi-currency calculations."""
        data = request.get_json(silent=True) or {}
        amount = float(data.get("amount", 0.0))
        target_currency = str(data.get("currency", "USD")).upper()

        rates = {
            "USD": 1.0,
            "EUR": 0.92,
            "PKR": 278.50,
            "GBP": 0.78
        }

        if target_currency not in rates:
            raise ValueError(f"Unsupported currency '{target_currency}'. Supported: USD, EUR, PKR, GBP")

        converted_amount = round(amount * rates[target_currency], 2)
        return jsonify({
            "original_amount": amount,
            "target_currency": target_currency,
            "converted_amount": converted_amount
        }), 200

    # ----- Dashboard Aggregate -----
    @app.route("/api/dashboard", methods=["GET"])
    def get_dashboard():
        month = request.args.get("month")
        if not month:
            now = datetime.now()
            month = f"{now.year}-{now.month:02d}"

        year, m = map(int, month.split("-"))
        last_day = calendar.monthrange(year, m)[1]
        start_date = f"{month}-01"
        end_date = f"{month}-{last_day:02d}"

        summary_data = models.summary(conn(), start_date, end_date) or {}
        raw_budgets = models.budget_status(conn(), month) or []
        raw_categories = models.category_totals(conn(), month) or []

        budgets_data = [clean_budget(b) for b in raw_budgets]
        categories_data = [clean_category(c) for c in raw_categories]

        income = float(summary_data.get("income") or 0.0)
        expense = float(summary_data.get("expense") or 0.0)
        balance = income - expense

        return jsonify({
            "month": month,
            "income": income,
            "expense": expense,
            "balance": balance,
            "budgets": budgets_data,
            "categories": categories_data
        })

    # ----- Transactions -----
    @app.route("/transactions", methods=["GET"])
    @app.route("/api/transactions", methods=["GET"])
    def get_transactions():
        a = request.args
        month = a.get("month")
        start = a.get("start")
        end = a.get("end")

        if month and not (start or end):
            year, m = map(int, month.split("-"))
            last_day = calendar.monthrange(year, m)[1]
            start = f"{month}-01"
            end = f"{month}-{last_day:02d}"

        txs = models.list_transactions(
            conn(), start=start, end=end, category=a.get("category"),
            type_=a.get("type"), sort=a.get("sort", "date"), order=a.get("order", "desc")) or []

        cleaned = []
        for t in txs:
            item = dict(t) if hasattr(t, "keys") or isinstance(t, dict) else t
            t_type = str(item.get("type", "expense")).lower()
            t_date = item.get("transaction_date") or item.get("date")
            cleaned.append({
                "id": item.get("id"),
                "amount": float(item.get("amount") or 0.0),
                "category": item.get("category"),
                "description": item.get("description") or item.get("note") or "",
                "note": item.get("note") or item.get("description") or "",
                "type": t_type,
                "transaction_date": t_date,
                "date": t_date
            })

        return jsonify(cleaned)

    @app.route("/transactions", methods=["POST"])
    @app.route("/api/transactions", methods=["POST"])
    def post_transaction():
        data = request.get_json(silent=True) or {}

        t_type = str(data.get("type", "expense")).lower()
        data["type"] = t_type
        if "transaction_date" in data and "date" not in data:
            data["date"] = data["transaction_date"]
        elif "date" in data and "transaction_date" not in data:
            data["transaction_date"] = data["date"]

        tx_id = models.add_transaction(conn(), data)
        alert = None
        if t_type == "expense":
            alert = models.check_alert(conn(), data.get("category"), data.get("date"))
        return jsonify({"id": tx_id, "alert": alert}), 201

    @app.route("/transactions/<int:tx_id>", methods=["PUT"])
    @app.route("/api/transactions/<int:tx_id>", methods=["PUT"])
    def put_transaction(tx_id):
        models.update_transaction(conn(), tx_id, request.get_json(silent=True) or {})
        return jsonify({"status": "updated"})

    @app.route("/transactions/<int:tx_id>", methods=["DELETE"])
    @app.route("/api/transactions/<int:tx_id>", methods=["DELETE"])
    def remove_transaction(tx_id):
        models.delete_transaction(conn(), tx_id)
        return jsonify({"status": "deleted"})

    # ----- Categories -----
    @app.route("/categories", methods=["GET"])
    @app.route("/api/categories", methods=["GET"])
    def get_categories():
        return jsonify(models.list_categories(conn()))

    @app.route("/categories", methods=["POST"])
    @app.route("/api/categories", methods=["POST"])
    def post_category():
        models.add_category(conn(), (request.get_json(silent=True) or {}).get("name"))
        return jsonify({"status": "created"}), 201

    @app.route("/categories/<name>", methods=["DELETE"])
    @app.route("/api/categories/<name>", methods=["DELETE"])
    def remove_category(name):
        models.delete_category(conn(), name)
        return jsonify({"status": "deleted"})

    # ----- Budgets -----
    @app.route("/budgets", methods=["GET"])
    @app.route("/api/budgets", methods=["GET"])
    def get_budgets():
        month = request.args.get("month")
        if not month:
            raise ValueError("month query parameter is required (YYYY-MM)")
        raw_budgets = models.budget_status(conn(), month) or []
        return jsonify([clean_budget(b) for b in raw_budgets])

    @app.route("/budgets", methods=["POST"])
    @app.route("/api/budgets", methods=["POST"])
    def post_budget():
        data = request.get_json(silent=True) or {}
        if "amount" in data and "limit" not in data:
            data["limit"] = data["amount"]
        if "limit" in data and "amount" not in data:
            data["amount"] = data["limit"]

        models.set_budget(conn(), data)
        return jsonify({"status": "saved"}), 201

    @app.route("/budgets/<int:budget_id>", methods=["DELETE"])
    @app.route("/api/budgets/<int:budget_id>", methods=["DELETE"])
    def remove_budget_by_id(budget_id):
        models.delete_budget(conn(), budget_id)
        return jsonify({"status": "deleted"})

    # ----- Analytics & Summaries -----
    @app.route("/summary", methods=["GET"])
    @app.route("/api/summary", methods=["GET"])
    def get_summary():
        return jsonify(models.summary(conn(), request.args.get("start"), request.args.get("end")))

    @app.route("/analytics/category", methods=["GET"])
    @app.route("/api/analytics/category", methods=["GET"])
    def get_category_analytics():
        month = request.args.get("month")
        if not month:
            raise ValueError("month query parameter is required (YYYY-MM)")
        return jsonify(models.category_totals(conn(), month))

    @app.route("/analytics/monthly", methods=["GET"])
    @app.route("/api/analytics/monthly", methods=["GET"])
    def get_monthly_analytics():
        return jsonify(models.monthly_totals(conn()))

    # ----- CSV Export & Import -----
    @app.route("/export/csv", methods=["GET"])
    @app.route("/api/export", methods=["GET"])
    def export_csv():
        month = request.args.get("month")
        start = request.args.get("start")
        end = request.args.get("end")
        if month and not (start or end):
            year, m = map(int, month.split("-"))
            last_day = calendar.monthrange(year, m)[1]
            start = f"{month}-01"
            end = f"{month}-{last_day:02d}"

        text = csv_utils.export_csv_text(conn(), start, end)
        return Response(text, mimetype="text/csv",
                        headers={"Content-Disposition": "attachment; filename=expensemate.csv"})

    @app.route("/import/csv", methods=["POST"])
    @app.route("/api/import", methods=["POST"])
    def import_csv():
        upload = request.files.get("file")
        if upload is None:
            raise ValueError("no file uploaded (form field name must be 'file')")
        return jsonify(csv_utils.import_csv(conn(), upload.stream))

    # Optional Layer Blueprint Registration
    try:
        from Backend.controllers.expense_controller import expense_bp
        app.register_blueprint(expense_bp)
    except ImportError:
        try:
            from controllers.expense_controller import expense_bp
            app.register_blueprint(expense_bp)
        except ImportError:
            pass

    return app


if __name__ == "__main__":
    create_app().run(port=5000, debug=True)