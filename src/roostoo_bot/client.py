from __future__ import annotations

import hashlib
import hmac
import json
import time
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


class RoostooAPIError(RuntimeError):
    pass


class RoostooClient:
    """Small client for the official REST API, with deterministic signed payloads."""

    base_url = "https://mock-api.roostoo.com"

    def __init__(self, api_key: str, secret_key: str, timeout: float = 15.0) -> None:
        if not api_key or not secret_key:
            raise ValueError("ROOSTOO_API_KEY and ROOSTOO_SECRET_KEY must be set")
        self.api_key = api_key
        self.secret_key = secret_key.encode()
        self.timeout = timeout

    @staticmethod
    def timestamp() -> str:
        return str(int(time.time() * 1000))

    @staticmethod
    def encode(params: dict[str, Any]) -> str:
        return urlencode(sorted((key, str(value)) for key, value in params.items()))

    def signature(self, encoded_params: str) -> str:
        return hmac.new(self.secret_key, encoded_params.encode(), hashlib.sha256).hexdigest()

    def _request(self, method: str, path: str, params: dict[str, Any], signed: bool) -> dict[str, Any]:
        encoded = self.encode(params)
        headers: dict[str, str] = {}
        if signed:
            headers = {
                "RST-API-KEY": self.api_key,
                "MSG-SIGNATURE": self.signature(encoded),
                "Content-Type": "application/x-www-form-urlencoded",
            }
        try:
            if method == "GET":
                separator = "?" if encoded else ""
                request = Request(f"{self.base_url}{path}{separator}{encoded}", headers=headers, method="GET")
            else:
                request = Request(f"{self.base_url}{path}", data=encoded.encode(), headers=headers, method="POST")
            with urlopen(request, timeout=self.timeout) as response:
                payload = json.loads(response.read().decode())
        except (HTTPError, URLError, TimeoutError, ValueError) as exc:
            raise RoostooAPIError(f"{method} {path} failed: {exc}") from exc
        if payload.get("Success") is False:
            raise RoostooAPIError(f"{method} {path} rejected: {payload.get('ErrMsg', 'unknown error')}")
        return payload

    def server_time(self) -> dict[str, Any]:
        return self._request("GET", "/v3/serverTime", {}, signed=False)

    def exchange_info(self) -> dict[str, Any]:
        return self._request("GET", "/v3/exchangeInfo", {}, signed=False)

    def ticker(self, pair: str) -> dict[str, Any]:
        return self._request("GET", "/v3/ticker", {"pair": pair, "timestamp": self.timestamp()}, signed=False)

    def balance(self) -> dict[str, Any]:
        payload = self._request("GET", "/v3/balance", {"timestamp": self.timestamp()}, signed=True)
        # Older documentation shows Wallet at the top level. The hackathon
        # backend currently returns SpotWallet (and a separate MarginWallet).
        # This bot trades spot only, so SpotWallet is deliberately selected.
        wallet: Any = payload.get("SpotWallet") or payload.get("spotWallet") or payload.get("Wallet") or payload.get("wallet")
        if not isinstance(wallet, dict):
            for key in ("Data", "data", "Result", "result"):
                container = payload.get(key)
                if isinstance(container, dict):
                    wallet = (
                        container.get("SpotWallet")
                        or container.get("spotWallet")
                        or container.get("Wallet")
                        or container.get("wallet")
                    )
                    if isinstance(wallet, dict):
                        break
        if not isinstance(wallet, dict):
            keys = ", ".join(sorted(str(key) for key in payload.keys()))
            raise RoostooAPIError(f"balance response has no spot wallet field (top-level keys: {keys or 'none'})")
        payload["Wallet"] = wallet
        return payload

    def place_market_order(self, pair: str, side: str, quantity: float) -> dict[str, Any]:
        if side not in {"BUY", "SELL"}:
            raise ValueError("side must be BUY or SELL")
        return self._request(
            "POST", "/v3/place_order",
            {"pair": pair, "side": side, "type": "MARKET", "quantity": quantity, "timestamp": self.timestamp()},
            signed=True,
        )

    def query_order(self, order_id: str) -> dict[str, Any]:
        return self._request("POST", "/v3/query_order", {"order_id": order_id, "timestamp": self.timestamp()}, signed=True)
