"""Data validation and type parsing utilities for ExpenseMate (Perfective Maintenance)."""
from datetime import datetime
from typing import Any, Tuple, Union


def parse_and_validate_amount(amount_input: Union[str, float, int]) -> float:
    """Perfective Refactoring: Centralized monetary value sanitizer and parser."""
    try:
        val = float(amount_input)
        if val <= 0:
            raise ValueError("Amount must be greater than zero.")
        return round(val, 2)
    except (TypeError, ValueError) as err:
        raise ValueError(f"Invalid monetary value ({amount_input}): {err}")


def is_valid_date(date_str: str) -> bool:
    """Validate ISO YYYY-MM-DD date string formatting."""
    if not date_str:
        return False
    try:
        datetime.strptime(date_str, "%Y-%m-%d")
        return True
    except ValueError:
        return False


def is_valid_month(month_str: str) -> bool:
    """Validate ISO YYYY-MM month string formatting."""
    if not month_str:
        return False
    try:
        datetime.strptime(month_str, "%Y-%m")
        return True
    except ValueError:
        return False


def validate_transaction(data: dict[str, Any]) -> Tuple[bool, str]:
    """Validate incoming transaction payload parameters."""
    if not data:
        return False, "Payload cannot be empty."

    try:
        parse_and_validate_amount(data.get("amount", 0))
    except ValueError as err:
        return False, str(err)

    if not is_valid_date(data.get("date") or data.get("transaction_date") or ""):
        return False, "Invalid or missing date (expected YYYY-MM-DD)."

    if not data.get("category") or not str(data["category"]).strip():
        return False, "Category name is required."

    return True, "Valid"


def validate_budget(data: dict[str, Any]) -> Tuple[bool, str]:
    """Validate incoming budget creation payload parameters."""
    if not data:
        return False, "Payload cannot be empty."

    try:
        parse_and_validate_amount(data.get("amount") or data.get("limit") or 0)
    except ValueError as err:
        return False, str(err)

    if not is_valid_month(data.get("month", "")):
        return False, "Invalid or missing month (expected YYYY-MM)."

    if not data.get("category") or not str(data["category"]).strip():
        return False, "Category name is required."

    return True, "Valid"