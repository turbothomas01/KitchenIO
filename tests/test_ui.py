import os
from pathlib import Path

from bs4 import BeautifulSoup
from fastapi.testclient import TestClient

from kitchenio.app import create_app, static_asset_version


def test_home_ui_has_accessible_structure_language_and_theme_controls(tmp_path: Path):
    client = TestClient(create_app(tmp_path / "kitchenio-test.db"))

    response = client.get("/?lang=en&theme=dark")
    assert response.status_code == 200
    soup = BeautifulSoup(response.text, "html.parser")

    assert soup.html["lang"] == "en"
    assert soup.body["data-theme"] == "dark"
    assert soup.find("main") is not None
    assert soup.find("nav", attrs={"aria-label": "Main sections"}) is None
    assert soup.find(attrs={"role": "tablist"}) is None
    assert soup.find(id="stock-panel") is None
    assert soup.find("a", href="/settings") is not None
    assert soup.select_one("header.site-header .header-title-row > a.settings-icon[href='/settings']") is not None
    stylesheet = soup.find("link", rel="stylesheet")
    assert stylesheet is not None
    assert "styles.css?v=" in stylesheet["href"]
    assert soup.find("script", src=lambda src: src and "tabs.js" in src) is None
    dialog_script = soup.find("script", src=lambda src: src and "dialogs.js" in src)
    assert dialog_script is not None
    assert "dialogs.js?v=" in dialog_script["src"]
    products_panel = soup.find("section", id="products-panel")
    assert products_panel is not None
    assert products_panel.find("h2") is None
    assert not products_panel.has_attr("hidden")

    product_dialog = soup.find("dialog", id="product-dialog")
    assert product_dialog["aria-modal"] == "true"

    forms = soup.find_all("form")
    assert forms
    for field in soup.find_all(["input", "textarea", "select"]):
        if field.get("type") == "hidden":
            continue
        field_id = field.get("id")
        assert field_id, f"field missing id: {field}"
        assert soup.find("label", attrs={"for": field_id}) is not None, field_id

    buttons = soup.find_all("button")
    assert buttons
    for button in buttons:
        assert button.get_text(strip=True) or button.get("aria-label")


def test_static_asset_version_changes_when_script_is_newer(tmp_path: Path):
    static_dir = tmp_path / "static"
    static_dir.mkdir()
    stylesheet = static_dir / "styles.css"
    dialog_script = static_dir / "dialogs.js"
    stylesheet.write_text("body {}", encoding="utf-8")
    dialog_script.write_text("console.log('dialogs')", encoding="utf-8")
    older = 1_700_000_000_000_000_000
    newer = older + 30

    os.utime(stylesheet, ns=(older, older))
    os.utime(dialog_script, ns=(newer, newer))

    assert static_asset_version(static_dir) == newer


def test_static_asset_version_reports_missing_asset(tmp_path: Path):
    static_dir = tmp_path / "static"
    static_dir.mkdir()
    (static_dir / "styles.css").write_text("body {}", encoding="utf-8")

    try:
        static_asset_version(static_dir)
    except RuntimeError as exc:
        assert "dialogs.js" in str(exc)
    else:
        raise AssertionError("expected RuntimeError for missing static asset")


def test_norwegian_ui_text_is_available(tmp_path: Path):
    client = TestClient(create_app(tmp_path / "kitchenio-test.db"))

    response = client.get("/?lang=no&theme=light")
    assert response.status_code == 200
    assert 'lang="no"' in response.text
    assert "Produkter" in response.text
    assert "Legg til produkt" in response.text


def test_mobile_product_counter_styles_are_present():
    styles = Path("kitchenio/static/styles.css").read_text()

    assert '.tabs [role="tablist"]' not in styles
    assert ".add-button" in styles
    assert "position: fixed;" in styles
    assert "right: max(1rem, env(safe-area-inset-right));" in styles
    assert "bottom: max(1rem, env(safe-area-inset-bottom));" in styles
    assert ".shopping-counter-row" in styles
    assert "grid-template-columns: auto minmax(0, 1fr) auto auto auto;" in styles
    assert "@media (max-width: 44rem) {\n  .site-header," not in styles


def test_settings_does_not_expose_stock_database_in_first_version(tmp_path: Path):
    client = TestClient(create_app(tmp_path / "kitchenio-test.db"))

    response = client.get("/settings?lang=en&theme=dark")
    assert response.status_code == 200
    soup = BeautifulSoup(response.text, "html.parser")

    assert soup.find(id="stock-database-heading") is None
    assert soup.find("form", action="/ui/stock") is None
    assert "Stock database" not in response.text


def test_shopping_list_rows_are_simple_checkbox_name_and_quantity_controls(tmp_path: Path):
    client = TestClient(create_app(tmp_path / "kitchenio-test.db"))
    created = client.post("/api/shopping-list", json={"item": "Milk", "amount": "2"})
    assert created.status_code == 201
    item_id = created.json()["id"]

    response = client.get("/?lang=en&theme=dark")
    assert response.status_code == 200
    soup = BeautifulSoup(response.text, "html.parser")

    row = soup.select_one(f"li.shopping-counter-row[data-shopping-item-id='{item_id}']")
    assert row is not None
    assert row.select_one("input[type='checkbox'][name='completed']") is not None
    assert row.select_one(".shopping-counter-name").get_text(strip=True) == "Milk"
    assert row.select_one(".shopping-counter-amount").get_text(strip=True) == "2"
    assert row.select_one("form[action$='/adjust'] input[name='delta'][value='-1']") is not None
    assert row.select_one("form[action$='/adjust'] input[name='delta'][value='1']") is not None
    assert row.find("input", attrs={"name": "item"}) is None
    assert row.find("input", attrs={"name": "amount"}) is None


def test_shopping_list_amount_can_be_adjusted_with_plus_and_minus(tmp_path: Path):
    client = TestClient(create_app(tmp_path / "kitchenio-test.db"))
    item_id = client.post("/api/shopping-list", json={"item": "Milk", "amount": "2"}).json()["id"]

    increased = client.post(f"/ui/shopping-list/{item_id}/adjust", data={"delta": "1"}, follow_redirects=False)
    assert increased.status_code == 303
    assert client.get("/api/shopping-list").json()[0]["amount"] == "3"

    decreased = client.post(f"/ui/shopping-list/{item_id}/adjust", data={"delta": "-1"}, follow_redirects=False)
    assert decreased.status_code == 303
    assert client.get("/api/shopping-list").json()[0]["amount"] == "2"


def test_shopping_counter_rows_stay_horizontal_on_mobile():
    styles = (Path(__file__).resolve().parents[1] / "kitchenio" / "static" / "styles.css").read_text(encoding="utf-8")

    mobile_section = styles.split("@media (max-width: 44rem)", 1)[1]
    assert ".shopping-counter-row," not in mobile_section
    assert "grid-template-columns: auto minmax(0, 1fr) auto auto auto;" in styles
