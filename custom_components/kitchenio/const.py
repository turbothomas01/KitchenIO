from __future__ import annotations

from datetime import timedelta

DOMAIN = "kitchenio"
PLATFORMS = ["sensor"]

CONF_API_KEY = "api_key"
CONF_URL = "url"
CONF_SHOPPING_LIST_ENTITY = "shopping_list_entity"

DEFAULT_NAME = "KitchenIO"
DEFAULT_SCAN_INTERVAL = timedelta(minutes=5)
DEFAULT_SHOPPING_SYNC_INTERVAL = timedelta(seconds=30)
DEFAULT_SHOPPING_LIST_ENTITY = "todo.shopping_list"

ATTR_ITEMS = "items"
ATTR_LOW_STOCK_ITEMS = "low_stock_items"
ATTR_STOCK_TABLE = "stock_table"
