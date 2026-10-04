import os
import unittest
from unittest.mock import patch

from roostoo_bot.config import Settings


class ConfigTests(unittest.TestCase):
    def test_misspelled_dry_run_fails_instead_of_enabling_orders(self):
        with patch.dict(os.environ, {"DRY_RUN": "treu"}, clear=True):
            with self.assertRaises(ValueError):
                Settings.from_env()

    def test_live_trading_requires_second_explicit_gate(self):
        with patch.dict(os.environ, {"DRY_RUN": "false"}, clear=True):
            with self.assertRaises(ValueError):
                Settings.from_env()

    def test_testing_credentials_use_user_env_names(self) -> None:
        environment = {
            "CREDENTIAL_SET": "testing",
            "ROOSTOO_API_KEY": "test-key",
            "ROOSTOO_API_SECRET": "test-secret",
        }
        with patch.dict(os.environ, environment, clear=True):
            settings = Settings.from_env()
        self.assertEqual(settings.api_key, "test-key")
        self.assertEqual(settings.secret_key, "test-secret")

    def test_competition_credentials_are_selected_explicitly(self) -> None:
        environment = {
            "CREDENTIAL_SET": "competition",
            "ROOSTOO_COMPET_API_KEY": "competition-key",
            "ROOSTOO_COMPET_API_SECRET": "competition-secret",
        }
        with patch.dict(os.environ, environment, clear=True):
            settings = Settings.from_env()
        self.assertEqual(settings.api_key, "competition-key")
        self.assertEqual(settings.secret_key, "competition-secret")
