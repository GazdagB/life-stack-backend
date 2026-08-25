import unittest
from datetime import date
from decimal import Decimal

from app.services.recurring_forecast_service import (
    build_recurring_coverage,
    count_occurrences,
)


def recurring_expense(**overrides):
    value = {
        "id": 1,
        "amount": Decimal("94.79"),
        "frequency": "MONTHLY",
        "start_date": date(2026, 8, 21),
        "end_date": date(2027, 1, 22),
        "active": True,
    }
    value.update(overrides)
    return value


class RecurringForecastServiceTests(unittest.TestCase):
    def test_finite_monthly_contract_respects_end_date(self):
        forecast = build_recurring_coverage(
            [recurring_expense()],
            as_of=date(2026, 8, 25),
        )

        commitment = forecast["commitments"][0]
        self.assertEqual(commitment["contract_payment_count"], 6)
        self.assertEqual(commitment["contract_total"], Decimal("568.74"))
        self.assertEqual(commitment["remaining_payment_count"], 5)
        self.assertEqual(commitment["remaining_total"], Decimal("473.95"))
        self.assertEqual(commitment["horizon_total"], Decimal("473.95"))
        self.assertEqual(commitment["daily_reserve"], Decimal("1.30"))
        self.assertEqual(commitment["monthly_reserve"], Decimal("39.50"))

    def test_paused_commitment_is_not_in_aggregate_but_keeps_its_metrics(self):
        forecast = build_recurring_coverage(
            [recurring_expense(active=False)],
            as_of=date(2026, 8, 25),
        )

        self.assertEqual(forecast["totals"]["horizon_total"], Decimal("0.00"))
        self.assertEqual(
            forecast["commitments"][0]["horizon_total"],
            Decimal("473.95"),
        )

    def test_month_end_cadence_uses_original_payment_day(self):
        expense = recurring_expense(
            start_date=date(2024, 1, 31),
            end_date=date(2024, 4, 30),
        )

        self.assertEqual(
            count_occurrences(expense, date(2024, 1, 1), date(2024, 4, 30)),
            4,
        )
        self.assertEqual(
            count_occurrences(expense, date(2024, 3, 1), date(2024, 3, 31)),
            1,
        )

    def test_leap_day_yearly_cadence(self):
        expense = recurring_expense(
            frequency="YEARLY",
            start_date=date(2024, 2, 29),
            end_date=date(2028, 2, 29),
        )

        self.assertEqual(
            count_occurrences(expense, date(2024, 1, 1), date(2028, 12, 31)),
            5,
        )


if __name__ == "__main__":
    unittest.main()
