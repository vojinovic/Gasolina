"""
Gasolina fuel price scraper.
Sources:
  - Serbia: cenagoriva.com (weekly max prices set by Ministry of Trade)
  - FX:     Narodna banka Srbije (RSD/EUR middle rate)
"""

import json
import re
from datetime import datetime
from pathlib import Path

import requests
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0 Safari/537.36"
    )
}

JSON_PATH = Path("fuel_prices.json")


def get_rsd_to_eur_rate() -> float:
    """Fetch middle RSD->EUR rate from NBS. Falls back to a sane default."""
    try:
        url = "https://www.nbs.rs/kursnaListaModul/zaDevize.faces"
        r = requests.get(url, headers=HEADERS, timeout=15)
        r.raise_for_status()
        # Try to find EUR row and parse the middle rate.
        soup = BeautifulSoup(r.text, "html.parser")
        text = soup.get_text(" ", strip=True)
        match = re.search(r"EUR.*?(\d{2,3}[.,]\d{2,4})", text)
        if match:
            return float(match.group(1).replace(",", "."))
    except Exception as exc:
        print(f"[fx] NBS fetch failed: {exc}")
    # Fallback. Updated periodically; keeps script working even if NBS changes.
    return 117.0


def parse_price(text: str) -> float | None:
    """Extract a number like '191,00' or '191.00' or '191' from text."""
    if not text:
        return None
    match = re.search(r"(\d{2,4}[.,]\d{1,2})", text)
    if match:
        return float(match.group(1).replace(",", "."))
    match = re.search(r"\b(\d{2,4})\b", text)
    if match:
        return float(match.group(1))
    return None


def scrape_serbia() -> dict:
    """Scrape current weekly max prices for Serbia from cenagoriva.com."""
    url = "https://www.cenagoriva.com/"
    r = requests.get(url, headers=HEADERS, timeout=20)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")
    page_text = soup.get_text(" ", strip=True)

    # Find prices near each fuel keyword. Tolerant to small layout changes.
    def find_near(label_patterns: list[str]) -> float | None:
        for pat in label_patterns:
            m = re.search(pat + r".{0,80}?(\d{2,4}[.,]?\d{0,2})\s*din", page_text, re.IGNORECASE)
            if m:
                return float(m.group(1).replace(",", "."))
        return None

    petrol_rsd = find_near([r"BMB\s*95", r"benzin\s*95"])
    diesel_rsd = find_near([r"evro\s*dizel", r"evrodizel", r"\bdizel\b"])
    lpg_rsd    = find_near([r"\bTNG\b", r"auto[-\s]?gas"])

    if not all([petrol_rsd, diesel_rsd, lpg_rsd]):
        raise RuntimeError(
            f"Failed to parse Serbia prices. Got petrol={petrol_rsd}, "
            f"diesel={diesel_rsd}, lpg={lpg_rsd}"
        )

    rate = get_rsd_to_eur_rate()
    return {
        "name": "Serbia",
        "flag": "🇷🇸",
        "currency": "RSD",
        "fx_rate_eur": round(rate, 4),
        "petrol95": {"local": petrol_rsd, "eur": round(petrol_rsd / rate, 2)},
        "diesel":   {"local": diesel_rsd, "eur": round(diesel_rsd / rate, 2)},
        "lpg":      {"local": lpg_rsd,    "eur": round(lpg_rsd    / rate, 2)},
        "updated":  datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"),
    }


def main():
    countries = []

    try:
        countries.append(scrape_serbia())
        print("[ok] Serbia scraped")
    except Exception as exc:
        print(f"[err] Serbia: {exc}")
        # Keep previous Serbia data if scrape fails, so site does not break.
        if JSON_PATH.exists():
            old = json.loads(JSON_PATH.read_text())
            for c in old.get("countries", []):
                if c.get("name") == "Serbia":
                    countries.append(c)
                    print("[fallback] kept previous Serbia data")
                    break

    payload = {"countries": countries}
    JSON_PATH.write_text(json.dumps(payload, indent=2, ensure_ascii=False))
    print(f"[done] wrote {JSON_PATH} with {len(countries)} country/countries")


if __name__ == "__main__":
    main()
