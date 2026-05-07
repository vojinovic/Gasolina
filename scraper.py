"""
Gasolina fuel price scraper.
Source: nafta.hr (clean tables per fuel type with EUR + local currency).
Strategy: read NIS Petrol row from each fuel-type table (largest market share).
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


def to_float(s: str) -> float:
    """Parse '191,00' or '1,63' or '1.63' into float."""
    s = s.replace("\xa0", " ").strip()
    m = re.search(r"(\d+[.,]?\d*)", s)
    if not m:
        raise ValueError(f"Cannot parse number from: {s!r}")
    return float(m.group(1).replace(",", "."))


def find_table_for_heading(soup: BeautifulSoup, heading_keywords: list[str]):
    """Find the first <table> that follows an h2/h3 matching any of the keywords."""
    for header in soup.find_all(["h2", "h3"]):
        title = header.get_text(strip=True).lower()
        if any(k.lower() in title for k in heading_keywords):
            # Skip 'Premium' tables when looking for base fuels.
            if "premium" in title and not any("premium" in k.lower() for k in heading_keywords):
                continue
            tbl = header.find_next("table")
            if tbl:
                return tbl
    return None


def get_company_row(table, company_name: str = "nis"):
    """From a price table, return (eur, local) tuple for the given company."""
    if table is None:
        return None
    for row in table.find_all("tr"):
        cells = row.find_all(["td", "th"])
        if len(cells) < 3:
            continue
        company = cells[0].get_text(strip=True).lower()
        if company_name.lower() in company:
            return to_float(cells[1].get_text()), to_float(cells[2].get_text())
    return None


def scrape_serbia() -> dict:
    url = "https://nafta.hr/sr/cene-goriva-srbija/"
    r = requests.get(url, headers=HEADERS, timeout=20)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")

    petrol_table = find_table_for_heading(soup, ["BMB 95 Benzin"])
    diesel_table = find_table_for_heading(soup, ["Eurodizel"])
    lpg_table    = find_table_for_heading(soup, ["Autoplin", "TNG", "auto plin"])

    petrol = get_company_row(petrol_table, "nis")
    diesel = get_company_row(diesel_table, "nis")
    lpg    = get_company_row(lpg_table, "nis")

    if not all([petrol, diesel, lpg]):
        raise RuntimeError(
            f"Failed to parse Serbia. petrol={petrol}, diesel={diesel}, lpg={lpg}"
        )

    p_eur, p_loc = petrol
    d_eur, d_loc = diesel
    l_eur, l_loc = lpg

    # Implied FX rate from any one fuel (sanity check / display).
    fx = round(p_loc / p_eur, 4) if p_eur else None

    return {
        "name": "Serbia",
        "flag": "🇷🇸",
        "currency": "RSD",
        "fx_rate_eur": fx,
        "petrol95": {"local": p_loc, "eur": p_eur},
        "diesel":   {"local": d_loc, "eur": d_eur},
        "lpg":      {"local": l_loc, "eur": l_eur},
        "updated":  datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"),
    }


def main():
    countries = []

    try:
        countries.append(scrape_serbia())
        print("[ok] Serbia scraped")
    except Exception as exc:
        print(f"[err] Serbia: {exc}")
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
