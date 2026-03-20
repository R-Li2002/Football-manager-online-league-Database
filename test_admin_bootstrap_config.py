import os
import unittest
from unittest.mock import patch

from main1 import load_bootstrap_admin_accounts_from_env


class AdminBootstrapConfigTests(unittest.TestCase):
    def test_bootstrap_admin_accounts_are_loaded_from_env(self):
        with patch.dict(
            os.environ,
            {"HEIGO_BOOTSTRAP_ADMINS": "HEIGO01=StrongOne!;HEIGO02=StrongTwo!"},
            clear=False,
        ):
            accounts = load_bootstrap_admin_accounts_from_env()

        self.assertEqual(len(accounts), 2)
        self.assertEqual(accounts[0][0], "HEIGO01")
        self.assertEqual(accounts[1][0], "HEIGO02")
        self.assertNotEqual(accounts[0][1], "StrongOne!")
        self.assertNotEqual(accounts[1][1], "StrongTwo!")

    def test_bootstrap_admin_accounts_reject_invalid_format(self):
        with patch.dict(os.environ, {"HEIGO_BOOTSTRAP_ADMINS": "HEIGO01"}, clear=False):
            with self.assertRaises(RuntimeError):
                load_bootstrap_admin_accounts_from_env()
