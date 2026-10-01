import hashlib
import hmac
import unittest

from roostoo_bot.client import RoostooClient


class ClientTests(unittest.TestCase):
    def test_signing_is_deterministic(self) -> None:
        client = RoostooClient("key", "secret")
        payload = client.encode({"type": "MARKET", "pair": "BTC/USD", "timestamp": "1", "side": "BUY", "quantity": "2"})
        self.assertEqual(payload, "pair=BTC%2FUSD&quantity=2&side=BUY&timestamp=1&type=MARKET")
        self.assertEqual(client.signature(payload), hmac.new(b"secret", payload.encode(), hashlib.sha256).hexdigest())
