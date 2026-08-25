import calendar
from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP
from typing import Mapping


CENT = Decimal("0.01")


def _money(value: Decimal) -> Decimal:
    return value.quantize(CENT, rounding=ROUND_HALF_UP)


def _occurrence_date(start: date, frequency: str, index: int) -> date:
    if frequency == "DAILY":
        return start + timedelta(days=index)
    if frequency == "WEEKLY":
        return start + timedelta(days=index * 7)
    if frequency == "MONTHLY":
        absolute_month = start.year * 12 + start.month - 1 + index
        year, zero_based_month = divmod(absolute_month, 12)
        month = zero_based_month + 1
        day = min(start.day, calendar.monthrange(year, month)[1])
        return date(year, month, day)
    if frequency == "YEARLY":
        year = start.year + index
        day = min(start.day, calendar.monthrange(year, start.month)[1])
        return date(year, start.month, day)
    raise ValueError(f"Unsupported recurring frequency: {frequency}")


def _first_candidate_index(start: date, frequency: str, range_start: date) -> int:
    if range_start <= start:
        return 0
    if frequency == "DAILY":
        return (range_start - start).days
    if frequency == "WEEKLY":
        return max(0, (range_start - start).days // 7)
    if frequency == "MONTHLY":
        month_difference = (range_start.year - start.year) * 12 + range_start.month - start.month
        return max(0, month_difference - 1)
    if frequency == "YEARLY":
        return max(0, range_start.year - start.year - 1)
    raise ValueError(f"Unsupported recurring frequency: {frequency}")


def count_occurrences(
    recurring_expense: Mapping,
    range_start: date,
    range_end: date,
) -> int:
    schedule_start = recurring_expense["start_date"]
    schedule_end = recurring_expense.get("end_date")

    if range_end < range_start:
        raise ValueError("Forecast end date cannot be before its start date")
    if range_end < schedule_start or (schedule_end and range_start > schedule_end):
        return 0

    effective_end = min(range_end, schedule_end) if schedule_end else range_end
    index = _first_candidate_index(
        schedule_start,
        recurring_expense["frequency"],
        range_start,
    )
    count = 0

    while True:
        occurrence = _occurrence_date(
            schedule_start,
            recurring_expense["frequency"],
            index,
        )
        if occurrence > effective_end:
            return count
        if occurrence >= range_start:
            count += 1
        index += 1


def _cost(recurring_expense: Mapping, occurrence_count: int) -> Decimal:
    return _money(Decimal(recurring_expense["amount"]) * occurrence_count)


def build_recurring_coverage(
    recurring_expenses: list[Mapping],
    as_of: date,
    horizon_days: int = 365,
) -> dict:
    if horizon_days < 1:
        raise ValueError("Forecast horizon must contain at least one day")

    through = as_of + timedelta(days=horizon_days - 1)
    commitments = []
    covered_total = Decimal("0.00")

    for recurring_expense in recurring_expenses:
        horizon_count = count_occurrences(recurring_expense, as_of, through)
        horizon_total = _cost(recurring_expense, horizon_count)
        end_date = recurring_expense.get("end_date")

        contract_count = None
        contract_total = None
        remaining_count = None
        remaining_total = None
        if end_date is not None:
            contract_count = count_occurrences(
                recurring_expense,
                recurring_expense["start_date"],
                end_date,
            )
            contract_total = _cost(recurring_expense, contract_count)
            remaining_count = count_occurrences(recurring_expense, as_of, end_date)
            remaining_total = _cost(recurring_expense, remaining_count)

        included = bool(recurring_expense["active"] and horizon_count > 0)
        if included:
            covered_total += horizon_total

        commitments.append(
            {
                "recurring_expense_id": recurring_expense["id"],
                "included_in_coverage": included,
                "horizon_total": horizon_total,
                "horizon_payment_count": horizon_count,
                "daily_reserve": _money(horizon_total / Decimal(horizon_days)),
                "weekly_reserve": _money(horizon_total / Decimal(52)),
                "monthly_reserve": _money(horizon_total / Decimal(12)),
                "remaining_total": remaining_total,
                "remaining_payment_count": remaining_count,
                "contract_total": contract_total,
                "contract_payment_count": contract_count,
            }
        )

    covered_total = _money(covered_total)
    return {
        "as_of": as_of,
        "through": through,
        "horizon_days": horizon_days,
        "totals": {
            "daily_reserve": _money(covered_total / Decimal(horizon_days)),
            "weekly_reserve": _money(covered_total / Decimal(52)),
            "monthly_reserve": _money(covered_total / Decimal(12)),
            "horizon_total": covered_total,
        },
        "commitments": commitments,
    }
