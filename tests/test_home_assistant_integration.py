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


def test_stock_is_displayed_as_one_summary_sensor_with_items_attribute():
    sensor = (INTEGRATION / "sensor.py").read_text(encoding="utf-8")

    assert "KitchenIOStockSensor" in sensor
    assert "native_value" in sensor
    assert "extra_state_attributes" in sensor
    assert '"items"' in sensor
    assert '"stock_table"' in sensor
    assert "len([item for item in self.coordinator.data" in sensor


def test_shopping_list_integration_uses_home_assistant_default_todo_service():
    services = (INTEGRATION / "services.py").read_text(encoding="utf-8")

    assert "todo.add_item" not in services  # HA service is domain/service, not a string endpoint.
    assert '"todo"' in services
    assert '"add_item"' in services
    assert '"todo.shopping_list"' in services
    assert "/api/shopping-list" not in services


def test_docs_explain_hacs_install_and_default_shopping_list_strategy():
    docs = (ROOT / "docs" / "home-assistant.md").read_text(encoding="utf-8")

    assert "HACS" in docs
    assert "sensor.kitchenio_stock" in docs
    assert "todo.shopping_list" in docs
    assert "single stock summary sensor" in docs
    assert "does not create a second shopping list" in docs
