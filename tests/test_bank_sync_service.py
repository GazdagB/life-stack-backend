import unittest
from decimal import Decimal

from app.services.bank_sync_service import (
    decrypt_provider_secret,
    encrypt_provider_secret,
    normalize_account,
    normalize_transaction,
    select_balance,
    suggest_category,
    transaction_fingerprint,
)


class BankSyncServiceTests(unittest.TestCase):
    def test_fingerprint_is_stable_for_provider_reference(self):
        first = transaction_fingerprint("account-1", {"entry_reference": "entry-42", "status": "BOOK"})
        second = transaction_fingerprint("account-1", {"entry_reference": "entry-42", "status": "PDNG"})
        self.assertEqual(first, second)

    def test_normalizes_booked_debit_without_storing_full_payload(self):
        result = normalize_transaction("account-1", {
            "entry_reference": "entry-42",
            "credit_debit_indicator": "DBIT",
            "status": "BOOK",
            "booking_date": "2026-08-31",
            "transaction_amount": {"amount": "-12.40", "currency": "EUR"},
            "creditor": {"name": "Lidl Budapest"},
            "remittance_information": ["Card payment"],
            "merchant_category_code": "5411",
        })
        self.assertEqual(result["direction"], "DEBIT")
        self.assertEqual(result["booking_status"], "BOOKED")
        self.assertEqual(result["amount"], Decimal("12.40"))
        self.assertEqual(result["suggested_category_id"], 3)
        self.assertNotIn("creditor", result)

    def test_masks_iban_when_normalizing_account(self):
        account = normalize_account({
            "uid": "07cc67f4-45d6-494b-adac-09b5cbc7e2b5",
            "identification_hash": "safe-hash",
            "account_id": {"iban": "DE89370400440532013000"},
            "account_servicer": {"name": "Example Bank"},
            "name": "Main account",
            "currency": "EUR",
        })
        self.assertEqual(account["iban_last4"], "3000")
        self.assertNotIn("iban", account)

    def test_selects_available_balance_first(self):
        result = select_balance({"balances": [
            {"balance_type": "CLBD", "balance_amount": {"amount": "100", "currency": "EUR"}},
            {"balance_type": "CLAV", "balance_amount": {"amount": "80", "currency": "EUR"}},
        ]})
        self.assertEqual(result["amount"], Decimal("80"))

    def test_unknown_merchant_uses_other_category(self):
        self.assertEqual(suggest_category("Unfamiliar merchant"), 10)

    def test_provider_session_secret_is_encrypted_at_rest(self):
        key = "MDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDA="
        encrypted = encrypt_provider_secret("provider-session-42", key)
        self.assertNotIn("provider-session-42", encrypted)
        self.assertEqual(decrypt_provider_secret(encrypted, key), "provider-session-42")


if __name__ == "__main__":
    unittest.main()
