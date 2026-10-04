from __future__ import annotations

import hashlib
import hmac
import json
import math
import time
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


class RoostooAPIError(RuntimeError):
    pass


class OrderRejected(RoostooAPIError):
    """An explicit backend rejection; no retry is performed."""


class OrderOutcomeUnknown(RoostooAPIError):
    """A submit may have reached the exchange. Never automatically resubmit."""


class RoostooClient:
    """Small client for the official REST API, with deterministic signed payloads."""

    base_url = "https://mock-api.roostoo.com"

    def __init__(self, api_key: str, secret_key: str, timeout: float = 15.0, *, allow_orders: bool = False, request_interval: float = 2.5) -> None:
        if not api_key or not secret_key:
            raise ValueError("ROOSTOO_API_KEY and ROOSTOO_SECRET_KEY must be set")
        self.api_key = api_key
        self.secret_key = secret_key.encode()
        self.timeout = timeout
        self.allow_orders = allow_orders
        if not math.isfinite(request_interval) or request_interval < 2.5:
            raise ValueError("request spacing must be at least 2.5 seconds")
        self.request_interval = request_interval
        self._last_request = float("-inf")
        self._clock = time.monotonic
        self._sleep = time.sleep

    @staticmethod
    def timestamp() -> str:
        return str(int(time.time() * 1000))

    @staticmethod
    def encode(params: dict[str, Any]) -> str:
        return urlencode(sorted((key, str(value)) for key, value in params.items()))

    @staticmethod
    def canonical_params(params: dict[str, Any]) -> str:
        # The official Python demo signs decoded values (BTC/USD), while the
        # HTTP form separately transports percent-encoded values (BTC%2FUSD).
        return "&".join(f"{key}={params[key]}" for key in sorted(params))

    def signature(self, canonical_params: str) -> str:
        return hmac.new(self.secret_key, canonical_params.encode(), hashlib.sha256).hexdigest()

    def _request(self, method: str, path: str, params: dict[str, Any], signed: bool) -> dict[str, Any]:
        submitting = path == "/v3/place_order"
        mutating = submitting or path == "/v3/cancel_order"
        if mutating and not self.allow_orders:
            raise RoostooAPIError("order submission is disabled on this client")
        for attempt in range(1 if mutating else 3):
            # <=24 calls/minute per process, including retries and read-only POSTs.
            delay = self.request_interval - (self._clock() - self._last_request)
            if delay > 0:
                self._sleep(delay)
            self._last_request = self._clock()
            current = dict(params)
            if "timestamp" in current:
                current["timestamp"] = self.timestamp()
            encoded = self.encode(current)
            headers = {"Content-Type": "application/x-www-form-urlencoded"}
            if signed:
                headers.update({"RST-API-KEY": self.api_key, "MSG-SIGNATURE": self.signature(self.canonical_params(current))})
            try:
                if method == "GET":
                    request = Request(f"{self.base_url}{path}{'?' if encoded else ''}{encoded}", headers=headers, method="GET")
                else:
                    request = Request(f"{self.base_url}{path}", data=encoded.encode(), headers=headers, method="POST")
                with urlopen(request, timeout=self.timeout) as response:
                    payload = json.loads(response.read().decode())
                if not isinstance(payload, dict):
                    raise ValueError("non-object response")
            except (HTTPError, URLError, OSError, ValueError) as exc:
                code = exc.code if isinstance(exc, HTTPError) else None
                if isinstance(exc, HTTPError):
                    exc.close()
                message = f"{method} {path} failed ({'HTTP ' + str(code) if code else type(exc).__name__})"
                if mutating:
                    raise OrderOutcomeUnknown(message) from None
                retryable = code is None or code in {408, 429} or code >= 500
                if attempt < 2 and retryable:
                    self._sleep(5 * 2 ** attempt if code == 429 else 2 ** attempt)
                    continue
                raise RoostooAPIError(message) from None
            if payload.get("Success") is False:
                if submitting and payload.get("OrderDetail"):
                    # Contradictory response: preserve the durable unknown
                    # intent rather than claiming that no order was accepted.
                    raise OrderOutcomeUnknown(f"{method} {path} has conflicting acceptance evidence")
                if path == "/v3/pending_count" and payload.get("TotalPending") == 0 and payload.get("OrderPairs") == {}:
                    return payload
                if path == "/v3/query_order" and payload.get("ErrMsg") == "no order matched":
                    payload["OrderMatched"] = []
                    return payload
                # Do not put remote error bodies (which could echo credentials) in logs.
                error = OrderRejected if mutating else RoostooAPIError
                raise error(f"{method} {path} explicitly rejected")
            if signed and payload.get("Success") is not True:
                error = OrderOutcomeUnknown if mutating else RoostooAPIError
                raise error(f"{method} {path} missing Success confirmation")
            return payload
        raise RoostooAPIError("request attempts exhausted")

    def server_time(self) -> dict[str, Any]:
        return self._request("GET", "/v3/serverTime", {}, signed=False)

    def exchange_info(self) -> dict[str, Any]:
        return self._request("GET", "/v3/exchangeInfo", {}, signed=False)

    def ticker(self, pair: str | None = None) -> dict[str, Any]:
        params = {"timestamp": self.timestamp()}
        if pair is not None:
            params["pair"] = pair
        return self._request("GET", "/v3/ticker", params, signed=False)

    def balance(self) -> dict[str, Any]:
        payload = self._request("GET", "/v3/balance", {"timestamp": self.timestamp()}, signed=True)
        # Older documentation shows Wallet at the top level. The hackathon
        # backend currently returns SpotWallet (and a separate MarginWallet).
        # This bot trades spot only, so SpotWallet is deliberately selected.
        def select(container: dict) -> Any:
            for key in ("SpotWallet", "spotWallet", "Wallet", "wallet"):
                if key in container:
                    return container[key]
            return None

        wallet: Any = select(payload)
        if not isinstance(wallet, dict):
            for key in ("Data", "data", "Result", "result"):
                container = payload.get(key)
                if isinstance(container, dict):
                    wallet = select(container)
                    if isinstance(wallet, dict):
                        break
        if not isinstance(wallet, dict):
            keys = ", ".join(sorted(str(key) for key in payload.keys()))
            raise RoostooAPIError(f"balance response has no spot wallet field (top-level keys: {keys or 'none'})")
        payload["Wallet"] = wallet
        return payload

    def place_market_order(self, pair: str, side: str, quantity: str) -> dict[str, Any]:
        if side not in {"BUY", "SELL"}:
            raise ValueError("side must be BUY or SELL")
        return self._request(
            "POST", "/v3/place_order",
            {"pair": pair, "side": side, "type": "MARKET", "quantity": quantity, "timestamp": self.timestamp()},
            signed=True,
        )

    def query_order(self, order_id: str) -> dict[str, Any]:
        return self._request("POST", "/v3/query_order", {"order_id": order_id, "timestamp": self.timestamp()}, signed=True)

    def query_orders(self, pair: str, limit: int = 10) -> dict[str, Any]:
        if type(limit) is not int or not 1 <= limit <= 100:
            raise ValueError("history limit must be 1 to 100")
        return self._request("POST", "/v3/query_order", {"pair":pair,"limit":limit,"timestamp":self.timestamp()}, signed=True)

    def place_limit_order(self, pair: str, side: str, quantity: str, price: str) -> dict[str, Any]:
        if side not in {"BUY", "SELL"}:
            raise ValueError("side must be BUY or SELL")
        return self._request("POST", "/v3/place_order", {"pair":pair,"side":side,"type":"LIMIT",
                             "quantity":quantity,"price":price,"timestamp":self.timestamp()}, signed=True)

    def cancel_order(self, order_id: str) -> dict[str, Any]:
        if not order_id:
            raise ValueError("exact order ID required; bulk cancellation is unsupported")
        return self._request("POST", "/v3/cancel_order", {"order_id":str(order_id),"timestamp":self.timestamp()}, signed=True)

    def pending_count(self) -> dict[str, Any]:
        return self._request("GET", "/v3/pending_count", {"timestamp": self.timestamp()}, signed=True)
