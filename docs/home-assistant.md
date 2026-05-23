# KitchenIO Home Assistant integration

KitchenIO version 1 has two simple tabs:

- **Products**: local KitchenIO product list with amounts and plus/minus controls.
- **Shopping List**: items to buy, synced with Home Assistant's built-in shopping list.

## Shopping list sync strategy

KitchenIO does not create a second shopping list in Home Assistant. It uses the default Home Assistant shopping list entity, usually `todo.shopping_list`, and syncs both ways with KitchenIO's Shopping List tab.

The integration periodically syncs open shopping-list items every 30 seconds:

- Items added in Home Assistant appear in KitchenIO's Shopping List tab.
- Items added in KitchenIO's Shopping List tab appear in Home Assistant's default shopping list.
- Items removed or completed after the first sync are removed from the other side.
- Home Assistant items are canonicalized as `Milk x1`, `Milk x2`, and so on. Items added as plain text, for example `Milk`, sync to KitchenIO as amount `1` and then back to Home Assistant as `Milk x1`.
- Legacy items written as `Milk (2)` are still understood and rewritten as `Milk x2`.

The integration also provides:

- `kitchenio.add_item_to_shopping_list` for automations.
- `kitchenio.sync_shopping_list` for immediate sync.
- A `Products` summary sensor exposing active KitchenIO products as `items` plus a `product_table` Markdown attribute.

## Install with HACS custom repository

1. In HACS, open **Integrations**.
2. Choose **Custom repositories**.
3. Add this repository URL:
   `https://github.com/turbothomas01/KitchenIO`
4. Category: **Integration**.
5. Install **KitchenIO** and restart Home Assistant.
6. Go to **Settings → Devices & services → Add integration → KitchenIO**.
7. Enter your KitchenIO URL, for example `http://192.168.0.133:8000`, and an API key if you created one.

## Dashboard examples

### Default Home Assistant shopping list

Add the built-in Shopping List / To-do list card for:

```yaml
entity: todo.shopping_list
```

### Product summary card

Add an Entities card with the KitchenIO `Products` sensor, or add a Markdown card using the sensor's `product_table` attribute.

## Service examples

Add a shopping-list item:

```yaml
service: kitchenio.add_item_to_shopping_list
data:
  name: Milk
  amount: "2"
  shopping_list_entity: todo.shopping_list
```

Force an immediate sync:

```yaml
service: kitchenio.sync_shopping_list
data: {}
```
