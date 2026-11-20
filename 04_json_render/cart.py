"""The coffee cart's numbers. Application data: the model never invents them."""

DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri"]
CUPS = [62, 71, 58, 90, 104]
ITEMS = [["Latte", 142, "$4.50"], ["Cold brew", 118, "$4.00"], ["Chai", 64, "$4.25"], ["Mocha", 61, "$4.75"]]
REVENUE = sum(c * float(p.strip("$")) for _, c, p in ITEMS)
STOCK = {"beans_pct": 22, "milk_pct": 64, "cups_pct": 85}


def sales_state(title: str, highlight: str) -> dict:
    return {"title": title, "highlight": highlight, "revenue": f"${REVENUE:,.0f}", "cups": sum(CUPS),
            "top": ITEMS[0][0], "days": DAYS, "cups_by_day": CUPS, "items": ITEMS}


def inventory_state(alert: str = "Beans run out in about 2 days") -> dict:
    return {"title": "Inventory", **STOCK, "alert": alert}
