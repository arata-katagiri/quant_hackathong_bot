import hashlib
import hmac
import unittest
import io
import json
from urllib.error import URLError, HTTPError
from unittest.mock import patch

from roostoo_bot.client import RoostooClient, RoostooAPIError, OrderOutcomeUnknown, OrderRejected


class ClientTests(unittest.TestCase):
    def test_signing_is_deterministic(self) -> None:
        client = RoostooClient("key", "secret")
        params = {"type": "MARKET", "pair": "BTC/USD", "timestamp": "1", "side": "BUY", "quantity": "2"}
        payload = client.encode(params)
        self.assertEqual(payload, "pair=BTC%2FUSD&quantity=2&side=BUY&timestamp=1&type=MARKET")
        canonical = "pair=BTC/USD&quantity=2&side=BUY&timestamp=1&type=MARKET"
        self.assertEqual(client.canonical_params(params),canonical)
        self.assertEqual(client.signature(canonical), hmac.new(b"secret",canonical.encode(),hashlib.sha256).hexdigest())

    def test_signed_post_uses_decoded_canonical_values_but_encoded_transport(self):
        client = RoostooClient("key","secret")
        client.timestamp = lambda:"1"
        response = io.BytesIO(json.dumps({"Success":True,"OrderMatched":[]}).encode())
        with patch("roostoo_bot.client.urlopen",return_value=response) as call:
            client.query_orders("BTC/USD")
        request = call.call_args.args[0]
        self.assertEqual(request.data,b"limit=10&pair=BTC%2FUSD&timestamp=1")
        expected = hmac.new(b"secret",b"limit=10&pair=BTC/USD&timestamp=1",hashlib.sha256).hexdigest()
        self.assertEqual(request.get_header("Msg-signature"),expected)

    def test_documented_empty_order_history_is_not_an_authentication_failure(self):
        response = io.BytesIO(json.dumps({"Success":False,"ErrMsg":"no order matched"}).encode())
        with patch("roostoo_bot.client.urlopen",return_value=response):
            self.assertEqual(RoostooClient("key","secret").query_orders("BTC/USD")["OrderMatched"],[])

    def test_balance_accepts_wallet_wrapped_in_data(self) -> None:
        client = RoostooClient("key", "secret")
        client._request = lambda *_args, **_kwargs: {"Success": True, "Data": {"Wallet": {"USD": {"Free": 100}}}}
        self.assertEqual(client.balance()["Wallet"]["USD"]["Free"], 100)

    def test_balance_prefers_spot_wallet(self) -> None:
        client = RoostooClient("key", "secret")
        client._request = lambda *_args, **_kwargs: {
            "Success": True,
            "SpotWallet": {"USD": {"Free": 100}},
            "MarginWallet": {"USD": {"Free": 999}},
        }
        self.assertEqual(client.balance()["Wallet"]["USD"]["Free"], 100)

    def test_balance_rejects_unknown_shape(self) -> None:
        client = RoostooClient("key", "secret")
        client._request = lambda *_args, **_kwargs: {"Success": True, "Message": "unexpected"}
        with self.assertRaisesRegex(Exception, "no spot wallet field"):
            client.balance()

    def test_empty_spot_wallet_does_not_fall_back_to_another_wallet(self):
        client = RoostooClient("key", "secret")
        client._request = lambda *_args, **_kwargs: {"Success": True, "SpotWallet": {}, "Wallet": {"USD": {"Free": 999}}}
        self.assertEqual(client.balance()["Wallet"], {})

    def test_default_client_blocks_submission_before_network(self):
        client = RoostooClient("key", "secret")
        with patch("roostoo_bot.client.urlopen") as call:
            with self.assertRaises(RoostooAPIError):
                client.place_market_order("BTC/USD", "BUY", "0.00100")
            call.assert_not_called()

    def test_default_client_also_blocks_limit_orders_and_cancellations(self):
        client = RoostooClient("key","secret")
        with patch("roostoo_bot.client.urlopen") as call:
            with self.assertRaises(RoostooAPIError):
                client.place_limit_order("BTC/USD","BUY","0.00008","100000")
            with self.assertRaises(RoostooAPIError):
                client.cancel_order("123")
        call.assert_not_called()

    def test_cancel_requires_exact_id_and_is_not_retried_on_timeout(self):
        client = RoostooClient("key","secret",allow_orders=True)
        with self.assertRaises(ValueError):
            client.cancel_order("")
        with patch("roostoo_bot.client.urlopen",side_effect=URLError("timeout")) as call:
            with self.assertRaises(OrderOutcomeUnknown):
                client.cancel_order("123")
        self.assertEqual(call.call_count,1)

    def test_lost_submit_response_is_not_retried(self):
        client = RoostooClient("key", "secret", allow_orders=True)
        with patch("roostoo_bot.client.urlopen", side_effect=URLError("secret")) as call:
            with self.assertRaises(OrderOutcomeUnknown) as caught:
                client.place_market_order("BTC/USD", "BUY", "0.00100")
            self.assertEqual(call.call_count, 1)
            self.assertNotIn("secret", str(caught.exception))

    def test_false_success_with_order_detail_is_ambiguous_not_safe_rejection(self):
        client = RoostooClient("key", "secret", allow_orders=True)
        body = {"Success": False, "ErrMsg": "secret", "OrderDetail": {"OrderID": 123, "Status": "FILLED"}}
        with patch("roostoo_bot.client.urlopen", return_value=io.BytesIO(json.dumps(body).encode())) as call:
            with self.assertRaises(OrderOutcomeUnknown) as caught:
                client.place_market_order("BTC/USD", "BUY", "0.00100")
            self.assertEqual(call.call_count, 1)
            self.assertNotIn("secret", str(caught.exception))

    def test_explicit_failure_without_order_details_remains_a_rejection(self):
        client = RoostooClient("key", "secret", allow_orders=True)
        with patch("roostoo_bot.client.urlopen", return_value=io.BytesIO(b'{"Success":false,"ErrMsg":"private"}')) as call:
            with self.assertRaises(OrderRejected) as caught:
                client.place_market_order("BTC/USD", "BUY", "0.00100")
            self.assertEqual(call.call_count, 1)
            self.assertNotIn("private", str(caught.exception))

    def test_read_retries_are_paced(self):
        client = RoostooClient("key", "secret")
        sleeps = []
        client._sleep = sleeps.append
        client._clock = lambda: 0
        response = io.BytesIO(json.dumps({"ServerTime": 1}).encode())
        with patch("roostoo_bot.client.urlopen", side_effect=[URLError("temporary"), response]) as call:
            self.assertEqual(client.server_time()["ServerTime"], 1)
            self.assertEqual(call.call_count, 2)
            self.assertIn(2.5, sleeps)

    def test_no_pending_orders_documented_false_success_is_accepted(self):
        client = RoostooClient("key", "secret")
        response = io.BytesIO(json.dumps({"Success": False, "TotalPending": 0, "OrderPairs": {}}).encode())
        with patch("roostoo_bot.client.urlopen", return_value=response):
            self.assertEqual(client.pending_count()["TotalPending"], 0)
