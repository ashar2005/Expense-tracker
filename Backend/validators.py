"""Rewritten validation engine for ExpenseMate data schemas."""
import datetime

VALID_TYPES = {"expense", "income"}


def validate_transaction(data):
    """Validates transaction input payloads.
    
    Returns an empty list [] if valid, or a list of descriptive error strings if invalid.
    """
    if not data:
        return ["amount is required", "category is required", "type must be expense or income", "date is required"]

    errors = []

    # 1. Amount validation
    if "amount" not in data or data["amount"] is None or data["amount"] == "":
        errors.append("amount is required")
    else:
        try:
            val = float(data["amount"])
            if val <= 0:
                errors.append("amount must be positive")
        except (ValueError, TypeError):
            errors.append("amount must be a valid number")

    # 2. Category validation
    if not data.get("category") or not str(data.get("category")).strip():
        errors.append("category is required")

    # 3. Transaction Type validation
    if "type" not in data or str(data.get("type")).lower() not in VALID_TYPES:
        errors.append("type must be expense or income")

    # 4. Date format validation (YYYY-MM-DD)
    if not data.get("date"):
        errors.append("date is required")
    else:
        try:
            datetime.date.fromisoformat(str(data["date"]))
        except ValueError:
            errors.append("date must be YYYY-MM-DD")

    return errors


def validate_budget(data):
    """Validates category budget limits and target month entries.
    
    Returns [] if valid, or a list of descriptive error strings if invalid.
    """
    if not data:
        return ["category is required", "month is required", "limit is required"]

    errors = []

    if not data.get("category") or not str(data.get("category")).strip():
        errors.append("category is required")

    if not data.get("month") or not str(data.get("month")).strip():
        errors.append("month is required")

    limit_val = data.get("limit") if "limit" in data else data.get("amount")
    if limit_val is None or limit_val == "":
        errors.append("limit is required")
    else:
        try:
            val = float(limit_val)
            if val <= 0:
                errors.append("limit must be positive")
        except (ValueError, TypeError):
            errors.append("limit must be a valid number")

    return errors