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

KitchenIO does not create a second shopping list in Home Assistant. Use the default Home Assistant shopping list entity, usually `todo.shopping_list`.

The integration provides the service `kitchenio.add_item_to_shopping_list`. It can add either:

- a KitchenIO stock item by `stock_item_id`, or
- a plain item by `name` and optional `amount`.

Internally, it calls Home Assistant's `todo` domain `add_item` service for `todo.shopping_list`, so your existing Shopping List dashboard card, Assist voice commands, and mobile app list all stay in one place.

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
