from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import aiohttp


class KitchenIOApiError(Exception):
    """Raised when KitchenIO cannot be reached or returns bad data."""


@dataclass(slots=True)
class KitchenIOClient:
    """Small async client for the KitchenIO REST API."""

    session: aiohttp.ClientSession
    url: str
    api_key: str | None = None

    def __post_init__(self) -> None:
        self.url = self.url.rstrip("/")

    @property
    def headers(self) -> dict[str, str]:
        if not self.api_key:
            return {}
        return {"X-API-Key": self.api_key}

    async def async_health(self) -> None:
        await self._request("GET", "/health")

    async def async_stock(self) -> list[dict[str, Any]]:
        data = await self._request("GET", "/api/stock")
        if not isinstance(data, list):
            raise KitchenIOApiError("KitchenIO stock response was not a list")
        return data

    async def async_products(self) -> list[dict[str, Any]]:
        """Return the KitchenIO product list."""
        return await self.async_stock()

    async def async_shopping_list(self) -> list[dict[str, Any]]:
        data = await self._request("GET", "/api/shopping-list")
        if not isinstance(data, list):
            raise KitchenIOApiError("KitchenIO shopping-list response was not a list")
        return data

    async def async_add_shopping_item(self, item: str, amount: str) -> dict[str, Any]:
        data = await self._request(
            "POST",
            "/api/shopping-list",
            json={"item": item, "amount": amount},
        )
        if not isinstance(data, dict):
            raise KitchenIOApiError("KitchenIO add-shopping response was not an object")
        return data

    async def async_delete_shopping_item(self, item_id: int) -> None:
        await self._request("DELETE", f"/api/shopping-list/{item_id}")

    async def _request(self, method: str, path: str, **kwargs: Any) -> Any:
        try:
            async with self.session.request(
                method,
                f"{self.url}{path}",
                headers=self.headers,
                timeout=aiohttp.ClientTimeout(total=15),
                **kwargs,
            ) as response:
                if response.status >= 400:
                    body = await response.text()
                    raise KitchenIOApiError(
                        f"KitchenIO returned HTTP {response.status} for {path}: {body[:200]}"
                    )
                if response.content_type == "application/json":
                    return await response.json()
                return await response.text()
        except TimeoutError as exc:
            raise KitchenIOApiError("Timed out talking to KitchenIO") from exc
        except aiohttp.ClientError as exc:
            raise KitchenIOApiError(f"Could not talk to KitchenIO: {exc}") from exc
