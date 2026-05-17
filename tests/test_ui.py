from pathlib import Path

from bs4 import BeautifulSoup
from fastapi.testclient import TestClient

from kitchenio.app import create_app


def test_home_ui_has_accessible_structure_language_and_theme_controls(tmp_path: Path):
    client = TestClient(create_app(tmp_path / "kitchenio-test.db"))

    response = client.get("/?lang=en&theme=dark")
    assert response.status_code == 200
    soup = BeautifulSoup(response.text, "html.parser")

    assert soup.html["lang"] == "en"
    assert soup.body["data-theme"] == "dark"
    assert soup.find("main") is not None
    assert soup.find("nav", attrs={"aria-label": "Main sections"}) is not None
    assert soup.find(attrs={"role": "tablist", "aria-label": "Main sections"}) is not None

    tabs = soup.find_all(attrs={"role": "tab"})
    assert [tab.get_text(strip=True) for tab in tabs] == ["Stock", "Shopping List"]
    assert all(tab.has_attr("aria-controls") for tab in tabs)
    assert all(tab.has_attr("aria-selected") for tab in tabs)
    assert soup.find("a", href="/settings") is not None
    assert soup.select_one("header.site-header .header-title-row > a.settings-icon[href='/settings']") is not None
    stylesheet = soup.find("link", rel="stylesheet")
    assert stylesheet is not None
    assert "styles.css?v=" in stylesheet["href"]
    assert soup.find("section", id="stock-panel").find("h2") is None
    assert soup.find("section", id="shopping-panel").find("h2") is None

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


def test_norwegian_ui_text_is_available(tmp_path: Path):
    client = TestClient(create_app(tmp_path / "kitchenio-test.db"))

    response = client.get("/?lang=no&theme=light")
    assert response.status_code == 200
    assert 'lang="no"' in response.text
    assert "Handleliste" in response.text
    assert "Fyll på lager" in response.text


def test_mobile_header_tabs_and_stock_counter_styles_are_present():
    styles = Path("kitchenio/static/styles.css").read_text()

    assert '.tabs [role="tablist"]' in styles
    assert "grid-template-columns: repeat(2, minmax(0, 1fr));" in styles
    assert '  .tabs [role="tab"] {' in styles
    assert "width: 100%;" in styles
    assert ".add-button" in styles
    assert "position: fixed;" in styles
    assert "right: max(1rem, env(safe-area-inset-right));" in styles
    assert "bottom: max(1rem, env(safe-area-inset-bottom));" in styles
    assert ".stock-counter-card" in styles
    assert "grid-template-columns: auto minmax(0, 1fr) auto;" in styles
    assert "@media (max-width: 44rem) {\n  .site-header," not in styles
