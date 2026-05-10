# KitchenIO

KitchenIO is a small self-hosted grocery and pantry management service. It is intentionally focused on only two things:

- **Stock**: what you have at home.
- **Shopping List**: what you need to buy.

It is similar in concept to Grocy, but deliberately minimal. There are no recipes, chores, batteries, calendars, meal planning, barcode scanning, or other unrelated features.

## Features

- Accessible web UI built with semantic HTML.
- Stock tab and Shopping List tab.
- Add, edit, delete, and list stock items.
- Add stock items directly to the shopping list.
- Add plain text shopping list items that are not in stock.
- Edit, delete, and mark shopping list items completed.
- Light and dark themes.
- English and Norwegian UI language.
- Settings page for default theme, default language, and API key creation.
- Optional API key protection for integrations: once a key exists, API calls require it.
- SQLite storage.
- REST API for Home Assistant, Hermes Agent, scripts, and automations.
- Accessible modal add screens opened from `+` buttons for Stock and Shopping List.
- Docker and Docker Compose support.
- Basic automated tests.

## Architecture

KitchenIO is intentionally simple for home hosting:

- **Backend**: FastAPI
- **Database**: SQLite
- **Frontend**: server-rendered HTML with minimal CSS
- **Container**: Docker image exposing port `8000`

No Node.js build step is required.

## Quick start with Docker Compose

```bash
git clone https://github.com/turbothomas01/KitchenIO.git
cd KitchenIO
docker compose up -d --build
```

Open:

```text
http://localhost:8000
```

Data is stored in the Docker volume `kitchenio-data`.

## Local development setup

```bash
git clone https://github.com/turbothomas01/KitchenIO.git
cd KitchenIO
python3 -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt -r requirements-dev.txt
python -m uvicorn kitchenio.app:app --reload
```

Open:

```text
http://localhost:8000
```

By default, the SQLite database is created at `data/kitchenio.db`. Override it with:

```bash
KITCHENIO_DB=/path/to/kitchenio.db python -m uvicorn kitchenio.app:app --reload
```

## Running tests

```bash
. .venv/bin/activate
python -m pytest -q
```

## Settings and API keys

Open the settings page from the KitchenIO header, or go directly to:

```text
http://localhost:8000/settings
```

The settings page lets you choose the default UI language and theme. It also lets you create API keys for trusted integrations such as Home Assistant and Hermes Agent.

API key behavior is intentionally simple for home setup:

- If no API key exists yet, the API is open on the local server so you can bootstrap KitchenIO.
- After you create the first API key, API endpoints require a valid key.
- The UI remains available locally for managing KitchenIO.
- Newly generated keys are shown once. Copy the key immediately.
- After the first key exists, creating additional keys from settings requires entering an existing API key.

Use either header format:

```http
X-API-Key: kio_your_key_here
```

or:

```http
Authorization: Bearer kio_your_key_here
```

## Accessibility notes

KitchenIO is designed accessibility-first:

- Semantic headings, forms, labels, lists, buttons, and landmarks.
- The main navigation uses accessible tab semantics.
- Every input has an associated `<label>`.
- Buttons use visible text.
- Keyboard users can reach every control with normal tab navigation.
- Focus indicators are visible in both themes.
- Completion state is communicated with text, not color alone.
- Light and dark themes maintain strong contrast.
- The language selector updates the document `lang` attribute.

## API documentation

Interactive OpenAPI documentation is available at:

```text
http://localhost:8000/docs
```

Raw OpenAPI JSON is available at:

```text
http://localhost:8000/openapi.json
```

### Health check

```http
GET /health
```

Response:

```json
{"status":"ok"}
```

### Stock endpoints

#### List stock items

```http
GET /api/stock
```

Example response:

```json
[
  {
    "id": 1,
    "name": "Coffee",
    "description": "Whole beans",
    "amount": "1"
  }
]
```

#### Add stock item

```http
POST /api/stock
Content-Type: application/json

{
  "name": "Coffee",
  "description": "Whole beans",
  "amount": "1"
}
```

#### Update stock item

```http
PUT /api/stock/1
Content-Type: application/json

{
  "name": "Coffee",
  "description": "Whole beans",
  "amount": "2"
}
```

#### Delete stock item

```http
DELETE /api/stock/1
```

#### Add stock item to shopping list

```http
POST /api/stock/1/add-to-shopping-list
```

This creates a shopping list item using the stock item's name and amount.

### Shopping list endpoints

#### List shopping list items

```http
GET /api/shopping-list
```

Example response:

```json
[
  {
    "id": 1,
    "item": "Milk",
    "amount": "2",
    "completed": false,
    "stock_item_id": null
  }
]
```

#### Add shopping list item

Plain text item:

```http
POST /api/shopping-list
Content-Type: application/json

{
  "item": "Milk",
  "amount": "2"
}
```

Item linked to stock:

```http
POST /api/shopping-list
Content-Type: application/json

{
  "item": "Coffee",
  "amount": "1",
  "stock_item_id": 1
}
```

#### Update shopping list item

```http
PUT /api/shopping-list/1
Content-Type: application/json

{
  "item": "Milk",
  "amount": "3",
  "completed": false,
  "stock_item_id": null
}
```

#### Delete shopping list item

```http
DELETE /api/shopping-list/1
```

#### Mark shopping list item completed

```http
POST /api/shopping-list/1/complete
```

## Home Assistant examples

Replace `http://kitchenio.local:8000` with your KitchenIO URL. If you have created an API key in KitchenIO settings, include it in each REST call.

Example header:

```yaml
headers:
  X-API-Key: !secret kitchenio_api_key
```

### REST sensor for stock

```yaml
sensor:
  - platform: rest
    name: KitchenIO Stock
    resource: http://kitchenio.local:8000/api/stock
    headers:
      X-API-Key: !secret kitchenio_api_key
    value_template: "{{ value_json | count }}"
    json_attributes:
      - id
      - name
      - description
      - amount
```

### REST command: add item to shopping list

```yaml
rest_command:
  kitchenio_add_shopping_item:
    url: http://kitchenio.local:8000/api/shopping-list
    method: POST
    headers:
      content-type: application/json
      X-API-Key: !secret kitchenio_api_key
    payload: >
      {
        "item": "{{ item }}",
        "amount": "{{ amount }}"
      }
```

Call it from an automation or script:

```yaml
action: rest_command.kitchenio_add_shopping_item
data:
  item: Milk
  amount: "2"
```

### Automation example

```yaml
alias: Add milk to KitchenIO shopping list from helper
trigger:
  - platform: state
    entity_id: input_button.add_milk_to_shopping_list
action:
  - service: rest_command.kitchenio_add_shopping_item
    data:
      item: Milk
      amount: "1"
```

## Hermes Agent usage examples

KitchenIO's API uses simple JSON, predictable endpoints, and a single API key header, so Hermes Agent can call it directly. Create a key on `/settings`, store it securely, and send it as `X-API-Key`.

Examples of commands Hermes Agent can perform:

- “Add milk to the shopping list”
  - `POST /api/shopping-list` with `{"item":"milk","amount":"1"}`
- “Add 2 bread to the shopping list”
  - `POST /api/shopping-list` with `{"item":"bread","amount":"2"}`
- “Show what is in stock”
  - `GET /api/stock`
- “Add coffee to stock with amount 1”
  - `POST /api/stock` with `{"name":"coffee","description":"","amount":"1"}`
- “Move eggs from stock to shopping list”
  - `GET /api/stock`, find `eggs`, then `POST /api/stock/{id}/add-to-shopping-list`

Example curl commands:

```bash
curl http://localhost:8000/api/stock \
  -H "X-API-Key: $KITCHENIO_API_KEY"

curl -X POST http://localhost:8000/api/stock \
  -H 'Content-Type: application/json' \
  -H "X-API-Key: $KITCHENIO_API_KEY" \
  -d '{"name":"Coffee","description":"Whole beans","amount":"1"}'

curl -X POST http://localhost:8000/api/shopping-list \
  -H 'Content-Type: application/json' \
  -H "X-API-Key: $KITCHENIO_API_KEY" \
  -d '{"item":"Milk","amount":"2"}'
```

## Error handling

- Missing or invalid fields return `422 Unprocessable Entity` with validation details.
- Unknown stock items return `404` with `Stock item not found`.
- Unknown shopping list items return `404` with `Shopping list item not found`.

## Roadmap boundaries

KitchenIO is intentionally focused. Please do not add Grocy-like extras unless explicitly requested later, such as:

- recipes
- chores
- batteries
- calendars
- meal planning
- barcode scanning
