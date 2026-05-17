from __future__ import annotations

import hashlib
import os
import re
import secrets
import sqlite3
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from fastapi import Depends, FastAPI, Form, Header, HTTPException, Query, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, ConfigDict, Field, field_validator

PACKAGE_DIR = Path(__file__).resolve().parent
DEFAULT_DB = Path(os.getenv("KITCHENIO_DB", "data/kitchenio.db"))
SUPPORTED_LANGUAGES = {"en", "no"}
SUPPORTED_THEMES = {"light", "dark"}
SAFE_STOCK_COUNT_RE = re.compile(r"^[+-]?\d{1,6}(?:[,.]\d{1,3})?$")

TRANSLATIONS: dict[str, dict[str, str]] = {
    "en": {
        "app_name": "KitchenIO",
        "tagline": "Minimal stock and shopping list management for your home.",
        "main_sections": "Main sections",
        "preferences": "Preferences",
        "settings": "Settings",
        "settings_intro": "Choose the default language and theme for KitchenIO.",
        "api_keys": "API keys",
        "api_key_intro": "Create API keys for Home Assistant, Hermes Agent, and other trusted local integrations.",
        "api_key_name": "API key name",
        "current_api_key": "Current API key",
        "current_api_key_help": "Required when API keys already exist.",
        "create_api_key": "Create API key",
        "created_api_key": "Created API key",
        "copy_key_now": "Copy this key now. KitchenIO will not show it again.",
        "existing_api_keys": "Existing API keys",
        "no_api_keys": "No API keys yet. Until you create one, the local API is open for setup.",
        "created": "Created",
        "back_home": "Back to KitchenIO",
        "saved": "Settings saved.",
        "language": "Language",
        "theme": "Theme",
        "english": "English",
        "norwegian": "Norwegian",
        "light": "Light",
        "dark": "Dark",
        "apply": "Apply",
        "stock": "Stock",
        "shopping_list": "Shopping List",
        "add_stock": "Add to stock",
        "create_stock_item": "Create stock database item",
        "add_bought_stock": "Refill existing stock item",
        "close": "Close",
        "edit_stock": "Edit stock item",
        "stock_items": "In stock",
        "no_stock": "No items are currently in stock.",
        "stock_database": "Stock database",
        "stock_database_intro": "Create new stock database items here. The front page + button only refills items that already exist.",
        "select_stock_item": "Stock item",
        "refill_amount": "New stock amount",
        "no_stock_for_refill": "All stock database items are already in stock, or no stock database items exist yet.",
        "increase_stock": "Increase stock",
        "decrease_stock": "Decrease stock",
        "in_stock_count": "In stock",
        "settings_icon_label": "Open settings",
        "name": "Name",
        "description": "Description",
        "amount": "Amount",
        "actions": "Actions",
        "save": "Save",
        "delete": "Delete",
        "add_to_shopping_list": "Add to shopping list",
        "add_shopping": "Add shopping item",
        "edit_shopping": "Edit shopping item",
        "shopping_items": "Shopping list items",
        "no_shopping": "No shopping list items yet.",
        "item": "Item",
        "completed": "Completed",
        "mark_completed": "Mark completed",
        "yes": "Yes",
        "no": "No",
        "from_stock": "From stock",
        "plain_text_hint": "Plain text items do not need to exist in stock.",
    },
    "no": {
        "app_name": "KitchenIO",
        "tagline": "Minimal lager- og handlelistehåndtering for hjemmet.",
        "main_sections": "Hovedseksjoner",
        "preferences": "Innstillinger",
        "settings": "Innstillinger",
        "settings_intro": "Velg standard språk og tema for KitchenIO.",
        "api_keys": "API-nøkler",
        "api_key_intro": "Opprett API-nøkler for Home Assistant, Hermes Agent og andre betrodde lokale integrasjoner.",
        "api_key_name": "Navn på API-nøkkel",
        "current_api_key": "Nåværende API-nøkkel",
        "current_api_key_help": "Påkrevd når API-nøkler allerede finnes.",
        "create_api_key": "Opprett API-nøkkel",
        "created_api_key": "Opprettet API-nøkkel",
        "copy_key_now": "Kopier denne nøkkelen nå. KitchenIO viser den ikke igjen.",
        "existing_api_keys": "Eksisterende API-nøkler",
        "no_api_keys": "Ingen API-nøkler ennå. Frem til du oppretter en, er det lokale API-et åpent for oppsett.",
        "created": "Opprettet",
        "back_home": "Tilbake til KitchenIO",
        "saved": "Innstillingene er lagret.",
        "language": "Språk",
        "theme": "Tema",
        "english": "Engelsk",
        "norwegian": "Norsk",
        "light": "Lyst",
        "dark": "Mørkt",
        "apply": "Bruk",
        "stock": "Lager",
        "shopping_list": "Handleliste",
        "add_stock": "Fyll på lager",
        "create_stock_item": "Opprett vare i lagerdatabasen",
        "add_bought_stock": "Fyll på eksisterende lagervare",
        "close": "Lukk",
        "edit_stock": "Rediger lagervare",
        "stock_items": "På lager",
        "no_stock": "Ingen varer er på lager akkurat nå.",
        "stock_database": "Lagerdatabase",
        "stock_database_intro": "Opprett nye lagervarer her. Plussknappen på forsiden fyller bare på varer som allerede finnes.",
        "select_stock_item": "Lagervare",
        "refill_amount": "Ny lagermengde",
        "no_stock_for_refill": "Alle lagervarer er allerede på lager, eller ingen lagervarer finnes ennå.",
        "increase_stock": "Øk lager",
        "decrease_stock": "Reduser lager",
        "in_stock_count": "På lager",
        "settings_icon_label": "Åpne innstillinger",
        "name": "Navn",
        "description": "Beskrivelse",
        "amount": "Mengde",
        "actions": "Handlinger",
        "save": "Lagre",
        "delete": "Slett",
        "add_to_shopping_list": "Legg til i handleliste",
        "add_shopping": "Legg til handlelistevare",
        "edit_shopping": "Rediger handlelistevare",
        "shopping_items": "Handlelistevarer",
        "no_shopping": "Ingen handlelistevarer ennå.",
        "item": "Vare",
        "completed": "Fullført",
        "mark_completed": "Merk som fullført",
        "yes": "Ja",
        "no": "Nei",
        "from_stock": "Fra lager",
        "plain_text_hint": "Fritekstvarer trenger ikke finnes på lager.",
    },
}


class KitchenIOModel(BaseModel):
    @field_validator("name", "item", "amount", check_fields=False)
    @classmethod
    def strip_required_text(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("Field must not be blank")
        return stripped

    @field_validator("description", check_fields=False)
    @classmethod
    def strip_optional_text(cls, value: str) -> str:
        return value.strip()


class StockCreate(KitchenIOModel):
    name: str = Field(min_length=1, max_length=200)
    description: str = Field(default="", max_length=1000)
    amount: str = Field(min_length=1, max_length=100)


class StockUpdate(StockCreate):
    pass


class StockItem(StockCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int


class ShoppingCreate(KitchenIOModel):
    item: str = Field(min_length=1, max_length=200)
    amount: str = Field(min_length=1, max_length=100)
    stock_item_id: int | None = None


class ShoppingUpdate(ShoppingCreate):
    completed: bool = False


class ShoppingItem(ShoppingUpdate):
    model_config = ConfigDict(from_attributes=True)
    id: int


def normalize_language(lang: str | None) -> str:
    return lang if lang in SUPPORTED_LANGUAGES else "en"


def normalize_theme(theme: str | None) -> str:
    return theme if theme in SUPPORTED_THEMES else "light"


def parse_stock_count(amount: str | int | float | Decimal | None) -> Decimal | None:
    if amount is None:
        return Decimal("0")
    text = str(amount).strip()
    if not text:
        return Decimal("0")
    first_token = text.split(maxsplit=1)[0]
    if not SAFE_STOCK_COUNT_RE.fullmatch(first_token):
        return None
    count = Decimal(first_token.replace(",", "."))
    return count if count.is_finite() else None


def format_stock_count(amount: Decimal) -> str:
    if amount == amount.to_integral_value():
        return str(int(amount))
    return format(amount.normalize(), "f")


def enrich_stock_item(item: dict[str, Any]) -> dict[str, Any]:
    count = parse_stock_count(item.get("amount"))
    enriched = dict(item)
    enriched["stock_count"] = str(item.get("amount") or "0") if count is None else format_stock_count(count)
    enriched["stock_count_is_numeric"] = count is not None
    enriched["is_in_stock"] = count is None or count > 0
    return enriched


def dict_from_row(row: sqlite3.Row) -> dict[str, Any]:
    item = dict(row)
    if "completed" in item:
        item["completed"] = bool(item["completed"])
    return item


def utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def hash_api_key(api_key: str) -> str:
    return hashlib.sha256(api_key.encode("utf-8")).hexdigest()


def get_settings(conn: sqlite3.Connection) -> dict[str, str]:
    rows = conn.execute("SELECT key, value FROM settings").fetchall()
    settings_map = {row["key"]: row["value"] for row in rows}
    return {
        "language": normalize_language(settings_map.get("language")),
        "theme": normalize_theme(settings_map.get("theme")),
    }


def save_settings(conn: sqlite3.Connection, language: str, theme: str) -> dict[str, str]:
    normalized = {"language": normalize_language(language), "theme": normalize_theme(theme)}
    for key, value in normalized.items():
        conn.execute(
            "INSERT INTO settings (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (key, value),
        )
    conn.commit()
    return normalized


def list_api_keys(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    return [
        dict_from_row(row)
        for row in conn.execute(
            "SELECT id, name, created_at, last_used_at FROM api_keys ORDER BY created_at DESC"
        )
    ]


def create_api_key_record(conn: sqlite3.Connection, name: str) -> str:
    clean_name = name.strip()
    if not clean_name:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="API key name is required")
    api_key = f"kio_{secrets.token_urlsafe(32)}"
    conn.execute(
        "INSERT INTO api_keys (name, key_hash, created_at) VALUES (?, ?, ?)",
        (clean_name, hash_api_key(api_key), utc_now()),
    )
    conn.commit()
    return api_key


def any_api_keys(conn: sqlite3.Connection) -> bool:
    return conn.execute("SELECT 1 FROM api_keys LIMIT 1").fetchone() is not None


def verify_api_key(conn: sqlite3.Connection, api_key: str | None) -> bool:
    if not api_key:
        return False
    key_hash = hash_api_key(api_key)
    row = conn.execute("SELECT id FROM api_keys WHERE key_hash = ?", (key_hash,)).fetchone()
    if row is None:
        return False
    conn.execute("UPDATE api_keys SET last_used_at = ? WHERE id = ?", (utc_now(), row["id"]))
    conn.commit()
    return True


def api_key_from_headers(x_api_key: str | None, authorization: str | None) -> str | None:
    if x_api_key:
        return x_api_key
    if authorization and authorization.lower().startswith("bearer "):
        return authorization[7:].strip()
    return None


def masked_key_label() -> str:
    return "kio_••••••••••••••••"


def init_db(db_path: Path) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(db_path) as conn:
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS stock_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                description TEXT NOT NULL DEFAULT '',
                amount TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS shopping_list_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                item TEXT NOT NULL,
                amount TEXT NOT NULL,
                completed INTEGER NOT NULL DEFAULT 0,
                stock_item_id INTEGER REFERENCES stock_items(id) ON DELETE SET NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS api_keys (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                key_hash TEXT NOT NULL UNIQUE,
                created_at TEXT NOT NULL,
                last_used_at TEXT
            )
            """
        )
        conn.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('language', 'en')")
        conn.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('theme', 'light')")


def get_connection(db_path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def create_app(db_path: str | Path = DEFAULT_DB) -> FastAPI:
    resolved_db = Path(db_path)
    init_db(resolved_db)
    app = FastAPI(
        title="KitchenIO API",
        description="Minimal stock and shopping list API for Home Assistant and Hermes Agent.",
        version="0.1.0",
    )
    app.state.db_path = resolved_db
    templates = Jinja2Templates(directory=str(PACKAGE_DIR / "templates"))
    asset_version = int((PACKAGE_DIR / "static" / "styles.css").stat().st_mtime)
    app.mount("/static", StaticFiles(directory=str(PACKAGE_DIR / "static")), name="static")

    def db() -> sqlite3.Connection:
        conn = get_connection(app.state.db_path)
        try:
            yield conn
        finally:
            conn.close()

    def require_api_key(
        conn: sqlite3.Connection = Depends(db),
        x_api_key: str | None = Header(default=None),
        authorization: str | None = Header(default=None),
    ) -> None:
        if not any_api_keys(conn):
            return
        api_key = api_key_from_headers(x_api_key, authorization)
        if verify_api_key(conn, api_key):
            return
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Valid API key required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/", response_class=HTMLResponse)
    def home(
        request: Request,
        conn: sqlite3.Connection = Depends(db),
        lang: str | None = Query(default=None),
        theme: str | None = Query(default=None),
    ) -> HTMLResponse:
        persisted_settings = get_settings(conn)
        current_lang = normalize_language(lang or persisted_settings["language"])
        current_theme = normalize_theme(theme or persisted_settings["theme"])
        stock = [enrich_stock_item(dict_from_row(row)) for row in conn.execute("SELECT * FROM stock_items ORDER BY name")]
        in_stock_items = [item for item in stock if item["is_in_stock"]]
        refill_items = [item for item in stock if not item["is_in_stock"]]
        shopping = [
            dict_from_row(row)
            for row in conn.execute("SELECT * FROM shopping_list_items ORDER BY completed, item")
        ]
        return templates.TemplateResponse(
            request,
            "index.html",
            {
                "t": TRANSLATIONS[current_lang],
                "lang": current_lang,
                "theme": current_theme,
                "stock_items": in_stock_items,
                "refill_items": refill_items,
                "shopping_items": shopping,
                "asset_version": asset_version,
            },
        )

    @app.get("/settings", response_class=HTMLResponse)
    def settings_page(
        request: Request,
        conn: sqlite3.Connection = Depends(db),
        saved: bool = Query(default=False),
    ) -> HTMLResponse:
        persisted_settings = get_settings(conn)
        current_lang = persisted_settings["language"]
        return templates.TemplateResponse(
            request,
            "settings.html",
            {
                "t": TRANSLATIONS[current_lang],
                "lang": current_lang,
                "theme": persisted_settings["theme"],
                "settings": persisted_settings,
                "api_keys": list_api_keys(conn),
                "stock_items": [dict_from_row(row) for row in conn.execute("SELECT * FROM stock_items ORDER BY name")],
                "has_api_keys": any_api_keys(conn),
                "new_api_key": None,
                "saved": saved,
                "masked_key_label": masked_key_label(),
            },
        )

    @app.post("/settings")
    def save_settings_page(
        conn: sqlite3.Connection = Depends(db),
        language: str = Form(...),
        theme: str = Form(...),
    ) -> RedirectResponse:
        save_settings(conn, language, theme)
        return RedirectResponse(url="/settings?saved=1", status_code=status.HTTP_303_SEE_OTHER)

    @app.post("/settings/api-keys", response_class=HTMLResponse)
    def create_api_key_page(
        request: Request,
        conn: sqlite3.Connection = Depends(db),
        name: str = Form(...),
        current_api_key: str = Form(""),
    ) -> HTMLResponse:
        if any_api_keys(conn) and not verify_api_key(conn, current_api_key):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Current API key required to create another API key",
            )
        new_api_key = create_api_key_record(conn, name)
        persisted_settings = get_settings(conn)
        current_lang = persisted_settings["language"]
        return templates.TemplateResponse(
            request,
            "settings.html",
            {
                "t": TRANSLATIONS[current_lang],
                "lang": current_lang,
                "theme": persisted_settings["theme"],
                "settings": persisted_settings,
                "api_keys": list_api_keys(conn),
                "stock_items": [dict_from_row(row) for row in conn.execute("SELECT * FROM stock_items ORDER BY name")],
                "has_api_keys": any_api_keys(conn),
                "new_api_key": new_api_key,
                "saved": False,
                "masked_key_label": masked_key_label(),
            },
        )

    @app.get("/api/stock", response_model=list[StockItem])
    def list_stock(
        conn: sqlite3.Connection = Depends(db),
        _api_key: None = Depends(require_api_key),
    ) -> list[dict[str, Any]]:
        return [dict_from_row(row) for row in conn.execute("SELECT * FROM stock_items ORDER BY name")]

    @app.post("/api/stock", response_model=StockItem, status_code=status.HTTP_201_CREATED)
    def add_stock(
        payload: StockCreate,
        conn: sqlite3.Connection = Depends(db),
        _api_key: None = Depends(require_api_key),
    ) -> dict[str, Any]:
        cursor = conn.execute(
            "INSERT INTO stock_items (name, description, amount) VALUES (?, ?, ?)",
            (payload.name.strip(), payload.description.strip(), payload.amount.strip()),
        )
        conn.commit()
        return get_stock_or_404(conn, cursor.lastrowid)

    @app.put("/api/stock/{item_id}", response_model=StockItem)
    def update_stock(
        item_id: int,
        payload: StockUpdate,
        conn: sqlite3.Connection = Depends(db),
        _api_key: None = Depends(require_api_key),
    ) -> dict[str, Any]:
        ensure_stock_exists(conn, item_id)
        conn.execute(
            "UPDATE stock_items SET name = ?, description = ?, amount = ? WHERE id = ?",
            (payload.name.strip(), payload.description.strip(), payload.amount.strip(), item_id),
        )
        conn.commit()
        return get_stock_or_404(conn, item_id)

    @app.delete("/api/stock/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
    def delete_stock(
        item_id: int,
        conn: sqlite3.Connection = Depends(db),
        _api_key: None = Depends(require_api_key),
    ) -> None:
        ensure_stock_exists(conn, item_id)
        conn.execute("DELETE FROM stock_items WHERE id = ?", (item_id,))
        conn.commit()
        return None

    @app.post(
        "/api/stock/{item_id}/add-to-shopping-list",
        response_model=ShoppingItem,
        status_code=status.HTTP_201_CREATED,
    )
    def add_stock_to_shopping_list(
        item_id: int,
        conn: sqlite3.Connection = Depends(db),
        _api_key: None = Depends(require_api_key),
    ) -> dict[str, Any]:
        stock = get_stock_or_404(conn, item_id)
        cursor = conn.execute(
            "INSERT INTO shopping_list_items (item, amount, completed, stock_item_id) VALUES (?, ?, 0, ?)",
            (stock["name"], stock["amount"], item_id),
        )
        conn.commit()
        return get_shopping_or_404(conn, cursor.lastrowid)

    @app.get("/api/shopping-list", response_model=list[ShoppingItem])
    def list_shopping(
        conn: sqlite3.Connection = Depends(db),
        _api_key: None = Depends(require_api_key),
    ) -> list[dict[str, Any]]:
        return [
            dict_from_row(row)
            for row in conn.execute("SELECT * FROM shopping_list_items ORDER BY completed, item")
        ]

    @app.post(
        "/api/shopping-list", response_model=ShoppingItem, status_code=status.HTTP_201_CREATED
    )
    def add_shopping(
        payload: ShoppingCreate,
        conn: sqlite3.Connection = Depends(db),
        _api_key: None = Depends(require_api_key),
    ) -> dict[str, Any]:
        if payload.stock_item_id is not None:
            ensure_stock_exists(conn, payload.stock_item_id)
        cursor = conn.execute(
            """
            INSERT INTO shopping_list_items (item, amount, completed, stock_item_id)
            VALUES (?, ?, 0, ?)
            """,
            (payload.item.strip(), payload.amount.strip(), payload.stock_item_id),
        )
        conn.commit()
        return get_shopping_or_404(conn, cursor.lastrowid)

    @app.put("/api/shopping-list/{item_id}", response_model=ShoppingItem)
    def update_shopping(
        item_id: int,
        payload: ShoppingUpdate,
        conn: sqlite3.Connection = Depends(db),
        _api_key: None = Depends(require_api_key),
    ) -> dict[str, Any]:
        ensure_shopping_exists(conn, item_id)
        if payload.stock_item_id is not None:
            ensure_stock_exists(conn, payload.stock_item_id)
        conn.execute(
            """
            UPDATE shopping_list_items
            SET item = ?, amount = ?, completed = ?, stock_item_id = ?
            WHERE id = ?
            """,
            (
                payload.item.strip(),
                payload.amount.strip(),
                int(payload.completed),
                payload.stock_item_id,
                item_id,
            ),
        )
        conn.commit()
        return get_shopping_or_404(conn, item_id)

    @app.delete("/api/shopping-list/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
    def delete_shopping(
        item_id: int,
        conn: sqlite3.Connection = Depends(db),
        _api_key: None = Depends(require_api_key),
    ) -> None:
        ensure_shopping_exists(conn, item_id)
        conn.execute("DELETE FROM shopping_list_items WHERE id = ?", (item_id,))
        conn.commit()
        return None

    @app.post("/api/shopping-list/{item_id}/complete", response_model=ShoppingItem)
    def complete_shopping(
        item_id: int,
        conn: sqlite3.Connection = Depends(db),
        _api_key: None = Depends(require_api_key),
    ) -> dict[str, Any]:
        ensure_shopping_exists(conn, item_id)
        conn.execute("UPDATE shopping_list_items SET completed = 1 WHERE id = ?", (item_id,))
        conn.commit()
        return get_shopping_or_404(conn, item_id)

    @app.post("/ui/stock")
    def ui_add_stock(
        conn: sqlite3.Connection = Depends(db),
        name: str = Form(...),
        description: str = Form(""),
        amount: str = Form(...),
    ) -> RedirectResponse:
        add_stock(StockCreate(name=name, description=description, amount=amount), conn)
        return RedirectResponse(url="/settings?saved=1", status_code=status.HTTP_303_SEE_OTHER)

    @app.post("/ui/stock/refill")
    def ui_refill_stock(
        conn: sqlite3.Connection = Depends(db),
        stock_item_id: int = Form(...),
        amount: str = Form(...),
        lang: str = Form("en"),
        theme: str = Form("light"),
    ) -> RedirectResponse:
        current = get_stock_or_404(conn, stock_item_id)
        update_stock(
            stock_item_id,
            StockUpdate(name=current["name"], description=current["description"], amount=amount),
            conn,
        )
        return redirect_home(lang, theme, "stock-panel")

    @app.post("/ui/stock/{item_id}/adjust")
    def ui_adjust_stock(
        item_id: int,
        conn: sqlite3.Connection = Depends(db),
        delta: int = Form(...),
        lang: str = Form("en"),
        theme: str = Form("light"),
    ) -> RedirectResponse:
        current = get_stock_or_404(conn, item_id)
        if delta not in {-1, 1}:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="delta must be -1 or 1")
        current_count = parse_stock_count(current["amount"])
        if current_count is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="stock amount is not numeric")
        next_count = max(Decimal("0"), current_count + Decimal(delta))
        update_stock(
            item_id,
            StockUpdate(
                name=current["name"],
                description=current["description"],
                amount=format_stock_count(next_count),
            ),
            conn,
        )
        return redirect_home(lang, theme, "stock-panel")

    @app.post("/ui/stock/{item_id}")
    def ui_update_stock(
        item_id: int,
        conn: sqlite3.Connection = Depends(db),
        name: str = Form(...),
        description: str = Form(""),
        amount: str = Form(...),
        lang: str = Form("en"),
        theme: str = Form("light"),
        return_to: str = Form("home"),
    ):
        update_stock(item_id, StockUpdate(name=name, description=description, amount=amount), conn)
        if return_to == "settings":
            return RedirectResponse(url="/settings?saved=1", status_code=status.HTTP_303_SEE_OTHER)
        return redirect_home(lang, theme, "stock-panel")

    @app.post("/ui/stock/{item_id}/delete")
    def ui_delete_stock(
        item_id: int,
        conn: sqlite3.Connection = Depends(db),
        lang: str = Form("en"),
        theme: str = Form("light"),
        return_to: str = Form("home"),
    ):
        delete_stock(item_id, conn)
        if return_to == "settings":
            return RedirectResponse(url="/settings?saved=1", status_code=status.HTTP_303_SEE_OTHER)
        return redirect_home(lang, theme, "stock-panel")

    @app.post("/ui/stock/{item_id}/shopping-list")
    def ui_stock_to_shopping(item_id: int, conn: sqlite3.Connection = Depends(db), lang: str = Form("en"), theme: str = Form("light")):
        add_stock_to_shopping_list(item_id, conn)
        return redirect_home(lang, theme, "shopping-panel")

    @app.post("/ui/shopping-list")
    def ui_add_shopping(
        conn: sqlite3.Connection = Depends(db),
        item: str = Form(...),
        amount: str = Form(...),
        lang: str = Form("en"),
        theme: str = Form("light"),
    ) -> RedirectResponse:
        add_shopping(ShoppingCreate(item=item, amount=amount), conn)
        return redirect_home(lang, theme, "shopping-panel")

    @app.post("/ui/shopping-list/{item_id}")
    def ui_update_shopping(
        item_id: int,
        conn: sqlite3.Connection = Depends(db),
        item: str = Form(...),
        amount: str = Form(...),
        completed: bool = Form(False),
        lang: str = Form("en"),
        theme: str = Form("light"),
    ):
        current = get_shopping_or_404(conn, item_id)
        update_shopping(
            item_id,
            ShoppingUpdate(
                item=item,
                amount=amount,
                completed=completed,
                stock_item_id=current.get("stock_item_id"),
            ),
            conn,
        )
        return redirect_home(lang, theme, "shopping-panel")

    @app.post("/ui/shopping-list/{item_id}/complete")
    def ui_complete_shopping(item_id: int, conn: sqlite3.Connection = Depends(db), lang: str = Form("en"), theme: str = Form("light")):
        complete_shopping(item_id, conn)
        return redirect_home(lang, theme, "shopping-panel")

    @app.post("/ui/shopping-list/{item_id}/delete")
    def ui_delete_shopping(item_id: int, conn: sqlite3.Connection = Depends(db), lang: str = Form("en"), theme: str = Form("light")):
        delete_shopping(item_id, conn)
        return redirect_home(lang, theme, "shopping-panel")

    return app


def redirect_home(lang: str, theme: str, fragment: str) -> RedirectResponse:
    return RedirectResponse(
        url=f"/?lang={normalize_language(lang)}&theme={normalize_theme(theme)}#{fragment}",
        status_code=status.HTTP_303_SEE_OTHER,
    )


def ensure_stock_exists(conn: sqlite3.Connection, item_id: int) -> None:
    get_stock_or_404(conn, item_id)


def get_stock_or_404(conn: sqlite3.Connection, item_id: int | None) -> dict[str, Any]:
    row = conn.execute("SELECT * FROM stock_items WHERE id = ?", (item_id,)).fetchone()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Stock item not found")
    return dict_from_row(row)


def ensure_shopping_exists(conn: sqlite3.Connection, item_id: int) -> None:
    get_shopping_or_404(conn, item_id)


def get_shopping_or_404(conn: sqlite3.Connection, item_id: int | None) -> dict[str, Any]:
    row = conn.execute("SELECT * FROM shopping_list_items WHERE id = ?", (item_id,)).fetchone()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Shopping list item not found")
    return dict_from_row(row)


app = create_app()
