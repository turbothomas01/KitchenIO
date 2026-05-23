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
    main = soup.find("main")
    assert main is not None
    assert "settings-shell" in main.get("class", [])
    hero = soup.select_one(".settings-hero")
    assert hero is not None
    assert hero.find("h1", string="Settings") is not None
    assert hero.select_one("a.settings-back-link[href='/']") is not None
    grid = soup.select_one(".settings-grid")
    assert grid is not None
    assert soup.select_one("section.settings-panel[aria-labelledby='preferences-heading']") is not None
    assert soup.select_one("section.settings-panel[aria-labelledby='api-keys-heading']") is not None
    assert soup.select_one(".settings-card-header #preferences-heading") is not None
    assert soup.select_one(".settings-card-header #api-keys-heading") is not None
    assert soup.find("label", attrs={"for": "settings-language"}) is not None
    assert soup.find("label", attrs={"for": "settings-theme"}) is not None
    stylesheet = soup.find("link", rel="stylesheet")
    assert stylesheet is not None
    assert "styles.css?v=" in stylesheet["href"]
    assert soup.find("section", attrs={"aria-labelledby": "api-keys-heading"}) is not None

    saved = client.post("/settings", data={"language": "no", "theme": "dark"}, follow_redirects=False)
    assert saved.status_code == 303
    assert saved.headers["location"] == "/settings?saved=1"

    home = client.get("/")
    assert home.status_code == 200
    assert 'lang="no"' in home.text
    assert 'data-theme="dark"' in home.text
    assert "Produkter" in home.text


def test_settings_styles_are_modern_and_responsive():
    styles = Path("kitchenio/static/styles.css").read_text(encoding="utf-8")

    assert ".settings-shell" in styles
    assert ".settings-hero" in styles
    assert ".settings-grid" in styles
    assert ".settings-panel" in styles
    assert ".settings-card-header" in styles
    assert ".settings-back-link" in styles
    assert "grid-template-columns: minmax(0, 0.85fr) minmax(0, 1.15fr);" in styles
    assert "@media (max-width: 44rem)" in styles
    assert ".settings-grid" in styles.split("@media (max-width: 44rem)", 1)[1]


def test_home_uses_plus_button_that_opens_accessible_product_dialog(tmp_path: Path):
    client = make_client(tmp_path)

    response = client.get("/")
    assert response.status_code == 200
    soup = BeautifulSoup(response.text, "html.parser")

    add_product_button = soup.find("button", attrs={"id": "open-active-dialog"})
    assert add_product_button is not None
    assert add_product_button.get_text(strip=True) == "+"
    assert add_product_button["aria-label"] == "Add product"
    assert add_product_button["aria-haspopup"] == "dialog"
    assert add_product_button["aria-controls"] == "product-dialog"
    assert add_product_button["data-shopping-label"] == "Add to shopping list"

    product_dialog = soup.find("dialog", attrs={"id": "product-dialog", "aria-labelledby": "add-product-heading"})
    assert product_dialog is not None
    assert product_dialog.find("form", attrs={"action": "/ui/stock"}) is not None
    assert product_dialog.find("input", attrs={"name": "name"}) is not None
    assert product_dialog.find("input", attrs={"name": "amount"}) is not None
    assert product_dialog.find("button", attrs={"value": "cancel"}) is not None

    shopping_dialog = soup.find("dialog", attrs={"id": "shopping-dialog", "aria-labelledby": "add-shopping-heading"})
    assert shopping_dialog is not None
    assert shopping_dialog.find("form", attrs={"action": "/ui/shopping-list"}) is not None


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
