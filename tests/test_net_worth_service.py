import unittest
from decimal import Decimal

from app.services.net_worth_service import calculate_net_worth_summary


class NetWorthServiceTests(unittest.TestCase):
    def test_calculates_owned_assets_liabilities_and_net_worth(self):
        result = calculate_net_worth_summary([
            {"active": True, "currency": "EUR", "kind": "ASSET", "category": "PROPERTY", "effective_value": Decimal("300000"), "ownership_percent": Decimal("50")},
            {"active": True, "currency": "EUR", "kind": "ASSET", "category": "BANK", "effective_value": Decimal("10000"), "ownership_percent": Decimal("100")},
            {"active": True, "currency": "EUR", "kind": "LIABILITY", "category": "LOAN", "effective_value": Decimal("120000"), "ownership_percent": Decimal("50")},
        ], "EUR")

        self.assertEqual(result["assets"], Decimal("160000.00"))
        self.assertEqual(result["liabilities"], Decimal("60000.00"))
        self.assertEqual(result["net_worth"], Decimal("100000.00"))
        self.assertEqual(result["item_count"], 3)

    def test_excludes_inactive_and_other_currency_items(self):
        result = calculate_net_worth_summary([
            {"active": False, "currency": "EUR", "kind": "ASSET", "category": "CASH", "effective_value": 500, "ownership_percent": 100},
            {"active": True, "currency": "HUF", "kind": "ASSET", "category": "CASH", "effective_value": 1000, "ownership_percent": 100},
        ], "EUR")
        self.assertEqual(result["net_worth"], Decimal("0.00"))
        self.assertEqual(result["item_count"], 0)


if __name__ == "__main__":
    unittest.main()
