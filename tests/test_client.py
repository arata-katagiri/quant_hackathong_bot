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

    def test_balance_accepts_wallet_wrapped_in_data(self) -> None:
        client = RoostooClient("key", "secret")
        client._request = lambda *_args, **_kwargs: {"Success": True, "Data": {"Wallet": {"USD": {"Free": 100}}}}
        self.assertEqual(client.balance()["Wallet"]["USD"]["Free"], 100)

    def test_balance_rejects_unknown_shape(self) -> None:
        client = RoostooClient("key", "secret")
        client._request = lambda *_args, **_kwargs: {"Success": True, "Message": "unexpected"}
        with self.assertRaisesRegex(Exception, "no Wallet field"):
            client.balance()
