import pytest
from Backend import models
from tests.conftest import make_tx


# ----- transactions (FR-01, FR-02) -----
def test_add_transaction_returns_id_and_is_listed(conn):
    tx_id = models.add_transaction(conn, make_tx())
    rows = models.list_transactions(conn)
    assert rows[0]["id"] == tx_id and rows[0]["amount"] == 100


def test_add_rejects_unknown_category(conn):
    with pytest.raises(ValueError, match="does not exist"):
        models.add_transaction(conn, make_tx(category="Nope"))


def test_add_rejects_invalid_input(conn):
    with pytest.raises(ValueError, match="amount"):
        models.add_transaction(conn, make_tx(amount=-1))


def test_update_transaction(conn):
    tx_id = models.add_transaction(conn, make_tx())
    models.update_transaction(conn, tx_id, make_tx(amount=250, category="Bills"))
    row = models.list_transactions(conn)[0]
    assert row["amount"] == 250 and row["category"] == "Bills"


def test_update_missing_transaction_fails(conn):
    with pytest.raises(ValueError, match="not found"):
        models.update_transaction(conn, 999, make_tx())


def test_delete_transaction(conn):
    tx_id = models.add_transaction(conn, make_tx())
    models.delete_transaction(conn, tx_id)
    assert models.list_transactions(conn) == []
    with pytest.raises(ValueError):
        models.delete_transaction(conn, tx_id)


def test_filters(conn):
    models.add_transaction(conn, make_tx(date="2026-09-01"))
    models.add_transaction(conn, make_tx(date="2026-10-01", category="Bills"))
    models.add_transaction(conn, make_tx(date="2026-10-05", type="income", category="Salary"))
    assert len(models.list_transactions(conn, start="2026-10-01")) == 2
    assert len(models.list_transactions(conn, end="2026-09-30")) == 1
    assert len(models.list_transactions(conn, category="Bills")) == 1
    assert len(models.list_transactions(conn, type_="income")) == 1


def test_sorting_by_amount(conn):
    models.add_transaction(conn, make_tx(amount=50))
    models.add_transaction(conn, make_tx(amount=300))
    rows = models.list_transactions(conn, sort="amount", order="asc")
    assert [r["amount"] for r in rows] == [50, 300]


def test_sort_column_is_whitelisted_against_sql_injection(conn):
    models.add_transaction(conn, make_tx())
    rows = models.list_transactions(conn, sort="amount; DROP TABLE transactions;--")
    assert len(rows) == 1


# ----- categories (FR-03) -----
def test_default_categories_exist(conn):
    assert "Food" in models.list_categories(conn)


def test_add_and_delete_custom_category(conn):
    models.add_category(conn, "Gym")
    assert "Gym" in models.list_categories(conn)
    models.delete_category(conn, "Gym")
    assert "Gym" not in models.list_categories(conn)


def test_duplicate_or_empty_category_rejected(conn):
    with pytest.raises(ValueError, match="already exists"):
        models.add_category(conn, "Food")
    with pytest.raises(ValueError, match="required"):
        models.add_category(conn, "  ")


def test_cannot_delete_category_in_use(conn):
    models.add_transaction(conn, make_tx())
    with pytest.raises(ValueError, match="in use"):
        models.delete_category(conn, "Food")


def test_delete_missing_category(conn):
    with pytest.raises(ValueError, match="not found"):
        models.delete_category(conn, "Ghost")


# ----- budgets and alerts (FR-04, FR-05) -----
def budget(limit=1000):
    return {"category": "Food", "month": "2026-09", "limit": limit}


def test_budget_status_percent(conn):
    models.set_budget(conn, budget(1000))
    models.add_transaction(conn, make_tx(amount=250))
    status = models.budget_status(conn, "2026-09")[0]
    assert status["percent"] == 25.0 and status["level"] == "ok"


def test_set_budget_twice_updates_limit(conn):
    models.set_budget(conn, budget(1000))
    models.set_budget(conn, budget(2000))
    statuses = models.budget_status(conn, "2026-09")
    assert len(statuses) == 1 and statuses[0]["limit"] == 2000


def test_invalid_budget_rejected(conn):
    with pytest.raises(ValueError):
        models.set_budget(conn, {"category": "Food", "month": "x", "limit": -1})


@pytest.mark.parametrize("amount,expected", [
    (799, None), (800, "warning"), (999, "warning"), (1000, "exceeded"), (1500, "exceeded"),
])
def test_alert_thresholds(conn, amount, expected):
    models.set_budget(conn, budget(1000))
    models.add_transaction(conn, make_tx(amount=amount))
    alert = models.check_alert(conn, "Food", "2026-09-10")
    assert (alert["level"] if alert else None) == expected


def test_income_does_not_count_towards_budget(conn):
    models.set_budget(conn, budget(1000))
    models.add_transaction(conn, make_tx(type="income", amount=5000))
    assert models.budget_status(conn, "2026-09")[0]["spent"] == 0


def test_other_month_does_not_count_towards_budget(conn):
    models.set_budget(conn, budget(1000))
    models.add_transaction(conn, make_tx(amount=900, date="2026-08-31"))
    assert models.check_alert(conn, "Food", "2026-09-10") is None


# ----- analytics (FR-06, FR-07) -----
def test_summary_totals(conn):
    models.add_transaction(conn, make_tx(type="income", category="Salary", amount=5000))
    models.add_transaction(conn, make_tx(amount=1200))
    assert models.summary(conn) == {"income": 5000, "expense": 1200, "balance": 3800}


def test_summary_respects_date_range(conn):
    models.add_transaction(conn, make_tx(date="2026-08-01", amount=10))
    models.add_transaction(conn, make_tx(date="2026-09-01", amount=20))
    assert models.summary(conn, start="2026-09-01")["expense"] == 20


def test_category_totals_only_expenses_for_month(conn):
    models.add_transaction(conn, make_tx(amount=100))
    models.add_transaction(conn, make_tx(amount=50, category="Bills"))
    models.add_transaction(conn, make_tx(amount=999, date="2026-08-01"))
    models.add_transaction(conn, make_tx(type="income", category="Salary", amount=5000))
    totals = models.category_totals(conn, "2026-09")
    assert totals == [{"category": "Food", "total": 100}, {"category": "Bills", "total": 50}]


def test_monthly_totals(conn):
    models.add_transaction(conn, make_tx(date="2026-08-05", amount=10))
    models.add_transaction(conn, make_tx(date="2026-09-05", type="income", category="Salary", amount=90))
    assert models.monthly_totals(conn) == [
        {"month": "2026-08", "income": 0, "expense": 10},
        {"month": "2026-09", "income": 90, "expense": 0},
    ]
