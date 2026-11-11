import datetime

VALID_TYPES = {"expense", "income"}

def validate_transaction(data):
    """
    Validates transaction data.
    Returns an empty list [] if valid, or a list of error strings if invalid.
    """
    errors = []
    if not data:
        return ["Payload cannot be empty."]

    # Amount validation
    if "amount" not in data or data["amount"] is None:
        errors.append("amount is required")
    else:
        try:
            val = float(data["amount"])
            if val <= 0:
                errors.append("amount must be positive")
        except (ValueError, TypeError):
            errors.append("amount must be a valid number")

    # Category validation
    if not data.get("category"):
        errors.append("category is required")

    # Type validation
    if data.get("type") not in VALID_TYPES:
        errors.append("type must be expense or income")

    # Date validation
    if not data.get("date"):
        errors.append("date is required")
    else:
        try:
            datetime.date.fromisoformat(str(data["date"]))
        except ValueError:
            errors.append("date must be YYYY-MM-DD")

    return errors


def validate_budget(data):
    """
    Validates budget input data.
    Returns [] if valid, or a list of error strings if invalid.
    """
    errors = []
    if not data:
        return ["Payload cannot be empty."]

    if not data.get("category"):
        errors.append("category is required")

    if not data.get("month"):
        errors.append("month is required")

    if "limit" not in data or data["limit"] is None:
        errors.append("limit is required")
    else:
        try:
            val = float(data["limit"])
            if val <= 0:
                errors.append("limit must be positive")
        except (ValueError, TypeError):
            errors.append("limit must be a valid number")

    return errors