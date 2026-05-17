from pathlib import Path

from bs4 import BeautifulSoup
from fastapi.testclient import TestClient

from kitchenio.app import create_app


def make_client(tmp_path: Path) -> TestClient:
    return TestClient(create_app(tmp_path / "kitchenio-test.db"))


def test_settings_page_persists_default_language_and_theme(tmp_path: Path):
    client = make_client(tmp_path)

    response = client.get("/settings")
    assert response.status_code == 200
    soup = BeautifulSoup(response.text, "html.parser")
    assert soup.find("main") is not None
    assert soup.find("h1", string="Settings") is not None
    assert soup.find("label", attrs={"for": "settings-language"}) is not None
    assert soup.find("label", attrs={"for": "settings-theme"}) is not None
    assert soup.find("section", attrs={"aria-labelledby": "stock-database-heading"}) is not None
    assert soup.find("section", attrs={"aria-labelledby": "api-keys-heading"}) is not None

    saved = client.post("/settings", data={"language": "no", "theme": "dark"}, follow_redirects=False)
    assert saved.status_code == 303
    assert saved.headers["location"] == "/settings?saved=1"

    home = client.get("/")
    assert home.status_code == 200
    assert 'lang="no"' in home.text
    assert 'data-theme="dark"' in home.text
    assert "Handleliste" in home.text


def test_home_uses_plus_buttons_that_open_accessible_add_dialogs(tmp_path: Path):
    client = make_client(tmp_path)
    client.post("/ui/stock", data={"name": "Coffee", "description": "", "amount": "1 bag"}, follow_redirects=False)
    client.post("/ui/stock", data={"name": "Milk", "description": "", "amount": "0"}, follow_redirects=False)

    response = client.get("/")
    assert response.status_code == 200
    soup = BeautifulSoup(response.text, "html.parser")

    add_stock_button = soup.find("button", attrs={"id": "open-stock-dialog"})
    assert add_stock_button is not None
    assert add_stock_button.get_text(strip=True).startswith("+")
    assert add_stock_button["aria-haspopup"] == "dialog"
    assert add_stock_button["aria-controls"] == "stock-dialog"

    stock_dialog = soup.find("dialog", attrs={"id": "stock-dialog", "aria-labelledby": "add-stock-heading"})
    assert stock_dialog is not None
    assert stock_dialog.find("form", attrs={"action": "/ui/stock/refill"}) is not None
    assert stock_dialog.find("select", attrs={"name": "stock_item_id"}) is not None
    assert stock_dialog.find("input", attrs={"name": "amount"}) is not None
    assert stock_dialog.find("form", attrs={"action": "/ui/stock"}) is None
    assert stock_dialog.find("button", attrs={"value": "cancel"}) is not None

    add_shopping_button = soup.find("button", attrs={"id": "open-shopping-dialog"})
    assert add_shopping_button is not None
    assert add_shopping_button.get_text(strip=True).startswith("+")
    assert add_shopping_button["aria-haspopup"] == "dialog"
    assert add_shopping_button["aria-controls"] == "shopping-dialog"

    shopping_dialog = soup.find("dialog", attrs={"id": "shopping-dialog", "aria-labelledby": "add-shopping-heading"})
    assert shopping_dialog is not None
    assert shopping_dialog.find("form", attrs={"action": "/ui/shopping-list"}) is not None
    assert shopping_dialog.find("button", attrs={"value": "cancel"}) is not None


def test_api_key_creation_shows_key_once_and_secures_api(tmp_path: Path):
    client = make_client(tmp_path)

    # Before keys exist, the API remains easy to bootstrap locally.
    assert client.get("/api/stock").status_code == 200

    created = client.post(
        "/settings/api-keys",
        data={"name": "Home Assistant"},
        follow_redirects=False,
    )
    assert created.status_code == 200
    soup = BeautifulSoup(created.text, "html.parser")
    key_output = soup.find("output", attrs={"id": "new-api-key"})
    assert key_output is not None
    api_key = key_output.get_text(strip=True)
    assert api_key.startswith("kio_")
    assert len(api_key) > 30
    assert "Copy this key now" in created.text

    settings_again = client.get("/settings")
    assert api_key not in settings_again.text
    assert "Home Assistant" in settings_again.text

    assert client.get("/api/stock").status_code == 401
    assert client.post(
        "/settings/api-keys",
        data={"name": "Hermes Agent"},
        follow_redirects=False,
    ).status_code == 401
    assert client.get("/api/stock", headers={"X-API-Key": api_key}).status_code == 200
    assert client.get("/api/stock", headers={"Authorization": f"Bearer {api_key}"}).status_code == 200

    second_key_response = client.post(
        "/settings/api-keys",
        data={"name": "Hermes Agent", "current_api_key": api_key},
        follow_redirects=False,
    )
    assert second_key_response.status_code == 200
    assert "Hermes Agent" in second_key_response.text

    added = client.post(
        "/api/shopping-list",
        headers={"X-API-Key": api_key},
        json={"item": "Milk", "amount": "1"},
    )
    assert added.status_code == 201


def test_front_page_refill_updates_existing_stock_instead_of_creating_new_item(tmp_path: Path):
    client = make_client(tmp_path)
    created = client.post(
        "/ui/stock",
        data={"name": "Coffee", "description": "Beans", "amount": "0"},
        follow_redirects=False,
    )
    assert created.status_code == 303
    assert created.headers["location"] == "/settings?saved=1"

    refill = client.post(
        "/ui/stock/refill",
        data={"stock_item_id": "1", "amount": "3", "lang": "en", "theme": "light"},
        follow_redirects=False,
    )
    assert refill.status_code == 303
    assert refill.headers["location"] == "/?lang=en&theme=light#stock-panel"

    stock = client.get("/api/stock").json()
    assert len(stock) == 1
    assert stock[0]["name"] == "Coffee"
    assert stock[0]["amount"] == "3"


def test_stock_counter_shows_only_positive_stock_and_moves_zero_to_refill(tmp_path: Path):
    client = make_client(tmp_path)
    client.post("/ui/stock", data={"name": "Coffee", "description": "", "amount": "2"}, follow_redirects=False)
    client.post("/ui/stock", data={"name": "Milk", "description": "", "amount": "0"}, follow_redirects=False)

    response = client.get("/")
    soup = BeautifulSoup(response.text, "html.parser")

    stock_cards = soup.select("li.stock-counter-card")
    assert len(stock_cards) == 1
    assert "Coffee" in stock_cards[0].get_text(" ", strip=True)
    assert "In stock: 2" in stock_cards[0].get_text(" ", strip=True)
    assert stock_cards[0].find("form", attrs={"action": "/ui/stock/1/adjust"}) is not None
    assert stock_cards[0].find("input", attrs={"name": "delta", "value": "-1"}) is not None
    assert stock_cards[0].find("input", attrs={"name": "delta", "value": "1"}) is not None
    assert stock_cards[0].find("form", attrs={"action": "/ui/stock/1/shopping-list"}) is not None

    refill_options = [option.get_text(strip=True) for option in soup.select("#refill-stock-item option")]
    assert refill_options == ["Milk"]

    for _ in range(2):
        decrement = client.post(
            "/ui/stock/1/adjust",
            data={"delta": "-1", "lang": "en", "theme": "light"},
            follow_redirects=False,
        )
        assert decrement.status_code == 303
    stock = client.get("/api/stock").json()
    assert stock[0]["amount"] == "0"

    response = client.get("/")
    soup = BeautifulSoup(response.text, "html.parser")
    assert not soup.select("li.stock-counter-card")
    refill_options = [option.get_text(strip=True) for option in soup.select("#refill-stock-item option")]
    assert refill_options == ["Coffee", "Milk"]


def test_legacy_non_numeric_stock_amount_remains_visible(tmp_path: Path):
    client = make_client(tmp_path)
    client.post(
        "/ui/stock",
        data={"name": "Coffee", "description": "Beans", "amount": "one bag"},
        follow_redirects=False,
    )

    response = client.get("/")
    soup = BeautifulSoup(response.text, "html.parser")

    stock_cards = soup.select("li.stock-counter-card")
    assert len(stock_cards) == 1
    assert "Coffee" in stock_cards[0].get_text(" ", strip=True)
    assert "In stock: one bag" in stock_cards[0].get_text(" ", strip=True)
    assert stock_cards[0].find("form", attrs={"action": "/ui/stock/1/adjust"}) is None
    assert not soup.select("#refill-stock-item option")

    adjusted = client.post(
        "/ui/stock/1/adjust",
        data={"delta": "1", "lang": "en", "theme": "light"},
        follow_redirects=False,
    )
    assert adjusted.status_code == 400
    assert client.get("/api/stock").json()[0]["amount"] == "one bag"


def test_stock_adjust_rejects_tampered_delta(tmp_path: Path):
    client = make_client(tmp_path)
    client.post("/ui/stock", data={"name": "Coffee", "description": "", "amount": "2"}, follow_redirects=False)

    response = client.post(
        "/ui/stock/1/adjust",
        data={"delta": "100000000000000000000000", "lang": "en", "theme": "light"},
        follow_redirects=False,
    )

    assert response.status_code == 400
    assert client.get("/api/stock").json()[0]["amount"] == "2"


def test_unusual_stock_amounts_do_not_crash_or_expand(tmp_path: Path):
    client = make_client(tmp_path)
    for amount in ["NaN", "Infinity", "1e1000", "1,5"]:
        client.post(
            "/ui/stock",
            data={"name": f"Amount {amount}", "description": "", "amount": amount},
            follow_redirects=False,
        )

    response = client.get("/")
    assert response.status_code == 200
    assert "Amount NaN" in response.text
    assert "In stock: NaN" in response.text
    assert "Amount Infinity" in response.text
    assert "In stock: Infinity" in response.text
    assert "Amount 1e1000" in response.text
    assert "In stock: 1e1000" in response.text
    assert "Amount 1,5" in response.text
    assert "In stock: 1.5" in response.text
