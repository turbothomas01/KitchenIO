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
    assert "Legg til i lager" in response.text
