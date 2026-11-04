import pytest
from Backend.validators import (is_valid_date, is_valid_month,
                                validate_budget, validate_transaction)
from tests.conftest import make_tx


def test_valid_transaction_has_no_errors():
    assert validate_transaction(make_tx()) == []


@pytest.mark.parametrize("field,value", [
    ("type", "transfer"), ("amount", "abc"), ("amount", -5), ("amount", 0),
    ("amount", None), ("category", ""), ("date", "10-09-2026"), ("date", "2026-02-30"),
])
def test_invalid_transaction_fields_are_reported(field, value):
    assert validate_transaction(make_tx(**{field: value})) != []


def test_multiple_errors_are_all_reported():
    errors = validate_transaction({})
    assert len(errors) == 4


def test_date_and_month_helpers():
    assert is_valid_date("2026-09-28")
    assert not is_valid_date("28/09/2026")
    assert is_valid_month("2026-09")
    assert not is_valid_month("2026-13")


def test_budget_validation():
    assert validate_budget({"category": "Food", "month": "2026-09", "limit": 500}) == []
    assert len(validate_budget({"category": "", "month": "bad", "limit": -1})) == 3
