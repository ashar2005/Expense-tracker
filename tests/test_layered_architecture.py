"""Unit tests verifying the Controller -> Service -> Repository layer architecture."""
import pytest
import sqlite3
from database import init_db
from repositories.expense_repository import ExpenseRepository
from services.expense_service import ExpenseService
from controllers.expense_controller import ExpenseController


@pytest.fixture
def layer_stack(tmp_path):
    db_file = str(tmp_path / "test_layered.db")
    init_db(db_file)
    repo = ExpenseRepository(db_file)
    service = ExpenseService(repo)
    controller = ExpenseController(service)
    return repo, service, controller


def test_repository_category_lookup(layer_stack):
    repo, _, _ = layer_stack
    cat_id = repo.get_category_id("Food")
    assert cat_id is not None
    assert repo.get_category_id("NonExistent") is None


def test_service_create_transaction_and_summary(layer_stack):
    _, service, _ = layer_stack
    res = service.create_transaction({
        "amount": 150.0,
        "category": "Food",
        "date": "2026-09-10",
        "type": "expense",
        "note": "Dinner"
    })
    assert res["id"] is not None

    summary = service.get_summary()
    assert summary["expense"] == 150.0
    assert summary["balance"] == -150.0


def test_service_invalid_category_raises_value_error(layer_stack):
    _, service, _ = layer_stack
    with pytest.raises(ValueError, match="does not exist"):
        service.create_transaction({
            "amount": 50.0,
            "category": "GhostCategory",
            "date": "2026-09-10",
            "type": "expense"
        })