# KitchenIO Home Assistant integration

The recommended Home Assistant display is a **single stock summary sensor**:

- Entity: `sensor.kitchenio_stock`
- State: number of KitchenIO items currently in stock
- Attributes:
  - `items`: accessible list of stock items with `id`, `name`, `amount`, and `description`
  - `low_stock_items`: numeric items with amount `1` or less
  - `stock_table`: Markdown table for a dashboard Markdown card

This avoids creating one entity per pantry item, which gets noisy and hard to maintain as stock changes.

## Shopping list strategy

KitchenIO does not create a second shopping list in Home Assistant. It uses the default Home Assistant shopping list entity, usually `todo.shopping_list`, and syncs both ways with KitchenIO's dashboard.

The integration periodically syncs open shopping-list items every 30 seconds:

- Items added in Home Assistant appear in the KitchenIO dashboard.
- Items added in KitchenIO appear in Home Assistant's default shopping list.
- Items removed or completed after the first sync are removed from the other side.
- Home Assistant items written as `Milk (2)` become KitchenIO item `Milk` with amount `2`; items without an amount default to amount `1`.

The integration also provides the service `kitchenio.add_item_to_shopping_list` for automations. It can add either an existing KitchenIO stock item by `stock_item_id`, or a plain item by `name` and optional `amount`. Use `kitchenio.sync_shopping_list` if you want to force an immediate sync.

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

### Stock summary entity

Add an Entities card with:

```yaml
type: entities
entities:
  - entity: sensor.kitchenio_stock
```

### Accessible stock table

Add a Markdown card with:

```yaml
type: markdown
content: "{{ state_attr('sensor.kitchenio_stock', 'stock_table') }}"
```

### Default Home Assistant shopping list

Add the built-in Shopping List / To-do list card for:

```yaml
entity: todo.shopping_list
```

## Service examples

Add a KitchenIO stock item to Home Assistant's default shopping list:

```yaml
service: kitchenio.add_item_to_shopping_list
data:
  stock_item_id: 1
  shopping_list_entity: todo.shopping_list
```

Add a plain item:

```yaml
service: kitchenio.add_item_to_shopping_list
data:
  name: Milk
  amount: "2"
```
