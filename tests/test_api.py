import io
from tests.conftest import make_tx


def test_health(client):
    assert client.get("/health").get_json() == {"status": "ok"}


def test_add_and_list_transaction(client):
    res = client.post("/transactions", json=make_tx())
    assert res.status_code == 201 and res.get_json()["alert"] is None
    rows = client.get("/transactions").get_json()
    assert len(rows) == 1 and rows[0]["category"] == "Food"


def test_invalid_transaction_returns_400_with_message(client):
    res = client.post("/transactions", json=make_tx(amount="abc"))
    assert res.status_code == 400 and "amount" in res.get_json()["error"]


def test_update_and_delete_transaction(client):
    tx_id = client.post("/transactions", json=make_tx()).get_json()["id"]
    assert client.put(f"/transactions/{tx_id}", json=make_tx(amount=7)).status_code == 200
    assert client.get("/transactions").get_json()[0]["amount"] == 7
    assert client.delete(f"/transactions/{tx_id}").status_code == 200
    assert client.delete(f"/transactions/{tx_id}").status_code == 400


def test_budget_alert_is_returned_when_threshold_crossed(client):
    client.post("/budgets", json={"category": "Food", "month": "2026-09", "limit": 1000})
    res = client.post("/transactions", json=make_tx(amount=850))
    assert res.get_json()["alert"]["level"] == "warning"
    res = client.post("/transactions", json=make_tx(amount=200))
    assert res.get_json()["alert"]["level"] == "exceeded"


def test_budget_status_endpoint_requires_month(client):
    assert client.get("/budgets").status_code == 400
    assert client.get("/budgets?month=2026-09").get_json() == []


def test_categories_endpoints(client):
    assert client.post("/categories", json={"name": "Gym"}).status_code == 201
    assert "Gym" in client.get("/categories").get_json()
    assert client.post("/categories", json={"name": "Gym"}).status_code == 400
    assert client.delete("/categories/Gym").status_code == 200


def test_analytics_endpoints(client):
    client.post("/transactions", json=make_tx(amount=100))
    client.post("/transactions", json=make_tx(type="income", category="Salary", amount=500))
    assert client.get("/summary").get_json()["balance"] == 400
    assert client.get("/analytics/category?month=2026-09").get_json()[0]["category"] == "Food"
    assert client.get("/analytics/monthly").get_json()[0]["month"] == "2026-09"
    assert client.get("/analytics/category").status_code == 400


def test_csv_export_and_import(client):
    client.post("/transactions", json=make_tx())
    res = client.get("/export/csv")
    assert res.mimetype == "text/csv" and b"Food" in res.data
    upload = {"file": (io.BytesIO(b"date,type,category,amount,note\n2026-09-02,expense,Bills,30,x\n"), "in.csv")}
    res = client.post("/import/csv", data=upload, content_type="multipart/form-data")
    assert res.get_json()["imported"] == 1


def test_csv_import_without_file_is_400(client):
    assert client.post("/import/csv").status_code == 400
