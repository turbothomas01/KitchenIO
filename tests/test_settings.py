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
    assert stock_dialog.find("form", attrs={"action": "/ui/stock"}) is not None
    choices = stock_dialog.find("div", attrs={"class": "dialog-choices"})
    assert choices is not None
    assert choices.find("button", attrs={"data-dialog-panel": "stock-create-panel"}) is not None
    assert choices.find("button", attrs={"data-dialog-panel": "stock-bought-panel"}) is not None
    assert stock_dialog.find(id="stock-create-panel") is not None
    assert stock_dialog.find(id="stock-bought-panel") is not None
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
