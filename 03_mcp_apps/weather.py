"""Deterministic forecast data, so every run and every test gives the same numbers."""

CITIES = {
    "Seattle": [("Fri", 12, 7, "rain"), ("Sat", 14, 8, "showers"), ("Sun", 16, 9, "cloudy"),
                ("Mon", 18, 10, "sun"), ("Tue", 17, 9, "sun")],
    "San Jose": [("Fri", 22, 11, "sun"), ("Sat", 24, 12, "sun"), ("Sun", 21, 11, "cloudy"),
                 ("Mon", 20, 10, "sun"), ("Tue", 23, 12, "sun")],
}
ICON = {"rain": "🌧", "showers": "🌦", "cloudy": "☁", "sun": "☀"}


def forecast(city: str, days: int = 3, units: str = "C") -> list[dict]:
    if city not in CITIES:
        raise ValueError(f"no forecast for {city!r}; try {', '.join(CITIES)}")
    conv = (lambda c: round(c * 9 / 5 + 32)) if units == "F" else (lambda c: c)
    return [{"day": d, "high": conv(h), "low": conv(lo), "sky": s, "icon": ICON[s]}
            for d, h, lo, s in CITIES[city][:days]]


def as_text(city: str, rows: list[dict], units: str) -> str:
    return f"{city}: " + "; ".join(f"{r['day']} {r['high']}°{units}/{r['low']}°{units} {r['sky']}" for r in rows)
