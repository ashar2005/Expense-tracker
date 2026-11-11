"""HTTP controller for handling transaction and expense endpoints."""
from flask import jsonify, request
from services.expense_service import ExpenseService
from validators import validate_transaction


class ExpenseController:
    def __init__(self, service: ExpenseService = None):
        self.service = service or ExpenseService()

    def add_transaction(self):
        payload = request.get_json() or {}
        errors = validate_transaction(payload)
        if errors:
            return jsonify({"errors": errors, "message": "; ".join(errors)}), 400

        try:
            result = self.service.create_transaction(payload)
            return jsonify(result), 201
        except ValueError as err:
            return jsonify({"error": str(err), "message": str(err)}), 400
        except Exception as err:
            return jsonify({"error": "Internal server error", "details": str(err)}), 500

    def get_summary(self):
        start = request.args.get("start")
        end = request.args.get("end")
        result = self.service.get_summary(start=start, end=end)
        return jsonify(result), 200