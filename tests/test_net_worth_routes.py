import unittest
from decimal import Decimal
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.main import app
from app.services.auth_service import get_current_user_id


class NetWorthRouteTests(unittest.TestCase):
    def setUp(self):
        app.dependency_overrides[get_current_user_id] = lambda: 42
        self.client = TestClient(app)

    def tearDown(self):
        app.dependency_overrides.clear()

    @patch("app.api.net_worth.list_net_worth_items")
    def test_summary_is_scoped_to_authenticated_user(self, list_items):
        list_items.return_value = [{
            "active": True,
            "currency": "EUR",
            "kind": "ASSET",
            "category": "BANK",
            "effective_value": Decimal("2500"),
            "ownership_percent": Decimal("100"),
        }]

        response = self.client.get("/net-worth/summary?currency=eur")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["net_worth"], 2500.0)
        list_items.assert_called_once_with(42)

    @patch("app.api.net_worth.create_net_worth_item")
    def test_create_normalizes_currency_and_passes_user_scope(self, create_item):
        create_item.return_value = {"id": 1}

        response = self.client.post("/net-worth/items", json={
            "name": "  Savings  ",
            "kind": "ASSET",
            "category": "CASH",
            "current_value": "1000.00",
            "currency": "eur",
            "ownership_percent": 100,
            "linked_bank_account_id": None,
            "notes": None,
            "active": True,
        })

        self.assertEqual(response.status_code, 200)
        item = create_item.call_args.args[1]
        self.assertEqual(create_item.call_args.args[0], 42)
        self.assertEqual(item.name, "Savings")
        self.assertEqual(item.currency, "EUR")


if __name__ == "__main__":
    unittest.main()
