from decimal import Decimal


def calculate_net_worth_summary(items: list[dict], currency: str) -> dict:
    assets = Decimal("0")
    liabilities = Decimal("0")
    categories: dict[str, Decimal] = {}
    active_items = [item for item in items if item["active"] and item["currency"] == currency]

    for item in active_items:
        owned_value = Decimal(str(item["effective_value"])) * Decimal(str(item["ownership_percent"])) / Decimal("100")
        if item["kind"] == "ASSET":
            assets += owned_value
        else:
            liabilities += owned_value
        categories[item["category"]] = categories.get(item["category"], Decimal("0")) + owned_value

    return {
        "currency": currency,
        "assets": assets.quantize(Decimal("0.01")),
        "liabilities": liabilities.quantize(Decimal("0.01")),
        "net_worth": (assets - liabilities).quantize(Decimal("0.01")),
        "item_count": len(active_items),
        "categories": [
            {"category": category, "value": value.quantize(Decimal("0.01"))}
            for category, value in sorted(categories.items(), key=lambda pair: pair[1], reverse=True)
        ],
    }
