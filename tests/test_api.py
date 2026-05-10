from pathlib import Path

from fastapi.testclient import TestClient

from kitchenio.app import create_app


def make_client(tmp_path: Path) -> TestClient:
    return TestClient(create_app(tmp_path / "kitchenio-test.db"))


def test_stock_crud_and_move_to_shopping_list(tmp_path: Path):
    client = make_client(tmp_path)

    created = client.post(
        "/api/stock",
        json={"name": "Coffee", "description": "Beans", "amount": "1"},
    )
    assert created.status_code == 201
    stock_item = created.json()
    assert stock_item["name"] == "Coffee"
    assert stock_item["description"] == "Beans"
    assert stock_item["amount"] == "1"

    assert client.get("/api/stock").json() == [stock_item]

    updated = client.put(
        f"/api/stock/{stock_item['id']}",
        json={"name": "Coffee", "description": "Whole beans", "amount": "2"},
    )
    assert updated.status_code == 200
    assert updated.json()["amount"] == "2"

    moved = client.post(f"/api/stock/{stock_item['id']}/add-to-shopping-list")
    assert moved.status_code == 201
    assert moved.json()["item"] == "Coffee"
    assert moved.json()["stock_item_id"] == stock_item["id"]

    deleted = client.delete(f"/api/stock/{stock_item['id']}")
    assert deleted.status_code == 204
    assert client.get("/api/stock").json() == []


def test_shopping_list_plain_text_items_and_completed_status(tmp_path: Path):
    client = make_client(tmp_path)

    created = client.post("/api/shopping-list", json={"item": "Milk", "amount": "2"})
    assert created.status_code == 201
    shopping_item = created.json()
    assert shopping_item["item"] == "Milk"
    assert shopping_item["amount"] == "2"
    assert shopping_item["completed"] is False
    assert shopping_item["stock_item_id"] is None

    updated = client.put(
        f"/api/shopping-list/{shopping_item['id']}",
        json={"item": "Milk", "amount": "3", "completed": False},
    )
    assert updated.status_code == 200
    assert updated.json()["amount"] == "3"

    completed = client.post(f"/api/shopping-list/{shopping_item['id']}/complete")
    assert completed.status_code == 200
    assert completed.json()["completed"] is True

    deleted = client.delete(f"/api/shopping-list/{shopping_item['id']}")
    assert deleted.status_code == 204
    assert client.get("/api/shopping-list").json() == []


def test_validation_and_not_found_errors_are_clear(tmp_path: Path):
    client = make_client(tmp_path)

    missing_name = client.post("/api/stock", json={"name": "", "description": "", "amount": "1"})
    assert missing_name.status_code == 422

    blank_after_trim = client.post(
        "/api/stock",
        json={"name": "   ", "description": "", "amount": "  "},
    )
    assert blank_after_trim.status_code == 422
    assert client.get("/api/stock").json() == []

    blank_shopping_item = client.post("/api/shopping-list", json={"item": "   ", "amount": "1"})
    assert blank_shopping_item.status_code == 422
    assert client.get("/api/shopping-list").json() == []

    not_found = client.delete("/api/stock/999")
    assert not_found.status_code == 404
    assert not_found.json()["detail"] == "Stock item not found"
