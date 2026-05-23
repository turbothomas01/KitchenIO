import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INTEGRATION = ROOT / "custom_components" / "kitchenio"


def test_home_assistant_manifest_is_config_flow_ready():
    manifest = json.loads((INTEGRATION / "manifest.json").read_text(encoding="utf-8"))

    assert manifest["domain"] == "kitchenio"
    assert manifest["name"] == "KitchenIO"
    assert manifest["config_flow"] is True
    assert "aiohttp" in manifest["requirements"]
    assert manifest["iot_class"] == "local_polling"


def test_home_assistant_integration_includes_logo_assets():
    for asset_name in ("icon.png", "logo.png"):
        asset = INTEGRATION / asset_name
        assert asset.exists(), f"missing HA integration logo asset: {asset_name}"
        assert asset.read_bytes().startswith(b"\x89PNG\r\n\x1a\n")


def test_github_readme_shows_logo():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")

    assert "docs/assets/kitchenio-logo.png" in readme
    assert "alt=\"KitchenIO logo\"" in readme


def test_products_are_displayed_as_one_summary_sensor_with_items_attribute():
    sensor = (INTEGRATION / "sensor.py").read_text(encoding="utf-8")
    coordinator = (INTEGRATION / "coordinator.py").read_text(encoding="utf-8")

    assert "KitchenIOProductSensor" in sensor
    assert "native_value" in sensor
    assert "extra_state_attributes" in sensor
    assert '"items"' in sensor
    assert '"product_table"' in sensor
    assert "len([item for item in self.coordinator.data" in sensor
    assert "async_products" in coordinator


def test_shopping_list_integration_uses_home_assistant_default_todo_service():
    services = (INTEGRATION / "services.py").read_text(encoding="utf-8")
    sync = (INTEGRATION / "shopping_sync.py").read_text(encoding="utf-8")

    assert "todo.add_item" not in services  # HA service is domain/service, not a string endpoint.
    assert '"todo"' in services
    assert '"add_item"' in services
    assert '"todo.shopping_list"' in services
    assert "/api/shopping-list" not in services
    assert "async_shopping_list" in sync
    assert "async_add_shopping_item" in sync
    assert "async_delete_shopping_item" in sync
    assert '"get_items"' in sync
    assert '"add_item"' in sync
    assert '"remove_item"' in sync
    assert "DEFAULT_SHOPPING_LIST_ENTITY" in sync
    assert "sync_shopping_list" in services


def test_docs_explain_hacs_install_and_default_shopping_list_strategy():
    docs = (ROOT / "docs" / "home-assistant.md").read_text(encoding="utf-8")

    assert "HACS" in docs
    assert "product list" in docs
    assert "todo.shopping_list" in docs
    assert "syncs both ways" in docs


def test_home_assistant_sync_uses_x_quantity_format_and_canonicalises_plain_items():
    sync = (INTEGRATION / "shopping_sync.py").read_text(encoding="utf-8")

    assert 'r"^(.+?)\\s+x(\\d+)\\s*$"' in sync
    assert 'canonical_text = f"{clean_name} x{clean_amount}"' in sync
    assert "_async_replace_ha_item" in sync
    assert "if item.text != item.canonical_text" in sync
