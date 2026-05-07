"""
Gasolina fuel price scraper.
Sources:
  - Serbia:     nafta.hr (per-fuel tables, NIS row)
  - Montenegro: nafta.hr (single combined table)
  - BiH:        goriva.ba (national average from 300+ stations)
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

# Fixed currency pegs (no daily fetching needed).
BAM_TO_EUR = 1.95583  # BAM is pegged to EUR


# ----------------------------- helpers -----------------------------

def to_float(s: str) -> float:
    s = (s or "").replace("\xa0", " ").strip()
    m = re.search(r"(\d+[.,]?\d*)", s)
    if not m:
        raise ValueError(f"Cannot parse number from: {s!r}")
    return float(m.group(1).replace(",", "."))


def fetch_soup(url: str) -> BeautifulSoup:
    r = requests.get(url, headers=HEADERS, timeout=20)
    r.raise_for_status()
    return BeautifulSoup(r.text, "html.parser")


def find_table_for_heading(soup: BeautifulSoup, heading_keywords: list[str]):
    for header in soup.find_all(["h2", "h3"]):
        title = header.get_text(strip=True).lower()
        if any(k.lower() in title for k in heading_keywords):
            if "premium" in title and not any("premium" in k.lower() for k in heading_keywords):
                continue
            tbl = header.find_next("table")
            if tbl:
                return tbl
    return None


def get_company_row(table, company_name: str):
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


def find_row_in_single_table(soup: BeautifulSoup, fuel_keywords: list[str]):
    for table in soup.find_all("table"):
        for row in table.find_all("tr"):
            cells = row.find_all(["td", "th"])
            if len(cells) < 3:
                continue
            label = cells[0].get_text(strip=True).lower()
            if any(k.lower() in label for k in fuel_keywords):
                try:
                    return to_float(cells[1].get_text()), to_float(cells[2].get_text())
                except ValueError:
                    continue
    return None


# --------------------------- scrapers ------------------------------

def scrape_serbia() -> dict:
    soup = fetch_soup("https://nafta.hr/sr/cene-goriva-srbija/")

    petrol = get_company_row(find_table_for_heading(soup, ["BMB 95 Benzin"]), "nis")
    diesel = get_company_row(find_table_for_heading(soup, ["Eurodizel"]), "nis")
    lpg    = get_company_row(find_table_for_heading(soup, ["Autoplin", "TNG", "auto plin"]), "nis")

    if not all([petrol, diesel, lpg]):
        raise RuntimeError(f"Serbia parse failed: petrol={petrol}, diesel={diesel}, lpg={lpg}")

    p_eur, p_loc = petrol
    d_eur, d_loc = diesel
    l_eur, l_loc = lpg

    return {
        "name": "Serbia",
        "flag": "🇷🇸",
        "currency": "RSD",
        "fx_rate_eur": round(p_loc / p_eur, 4) if p_eur else None,
        "petrol95": {"local": p_loc, "eur": p_eur},
        "diesel":   {"local": d_loc, "eur": d_eur},
        "lpg":      {"local": l_loc, "eur": l_eur},
        "updated":  datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"),
    }


def scrape_montenegro() -> dict:
    soup = fetch_soup("https://nafta.hr/sr/cene-goriva-crna-gora/")

    petrol = find_row_in_single_table(soup, ["BMB 95"])
    diesel = find_row_in_single_table(soup, ["Eurodizel"])

    if not petrol or not diesel:
        raise RuntimeError(f"Montenegro parse failed: petrol={petrol}, diesel={diesel}")

    p_eur, _ = petrol
    d_eur, _ = diesel

    return {
        "name": "Montenegro",
        "flag": "🇲🇪",
        "currency": "EUR",
        "fx_rate_eur": 1.0,
        "petrol95": {"local": p_eur, "eur": p_eur},
        "diesel":   {"local": d_eur, "eur": d_eur},
        "lpg":      None,
        "updated":  datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"),
    }


def scrape_bosnia() -> dict:
    """goriva.ba shows national averages as: '<fuel>\n<price>KM'."""
    r = requests.get("https://goriva.ba/", headers=HEADERS, timeout=20)
    r.raise_for_status()
    text = BeautifulSoup(r.text, "html.parser").get_text(" ", strip=True)

    def grab(label_pattern: str) -> float:
        m = re.search(label_pattern + r"\s*(\d+[.,]\d+)\s*KM", text, re.IGNORECASE)
        if not m:
            raise ValueError(f"Could not find price for: {label_pattern}")
        return float(m.group(1).replace(",", "."))

    petrol_loc = grab(r"Benzin\s*95")
    diesel_loc = grab(r"\bDizel\b")
    lpg_loc    = grab(r"\bLPG\b")

    return {
        "name": "Bosnia and Herzegovina",
        "flag": "🇧🇦",
        "currency": "BAM",
        "fx_rate_eur": BAM_TO_EUR,
        "petrol95": {"local": petrol_loc, "eur": round(petrol_loc / BAM_TO_EUR, 2)},
        "diesel":   {"local": diesel_loc, "eur": round(diesel_loc / BAM_TO_EUR, 2)},
        "lpg":      {"local": lpg_loc,    "eur": round(lpg_loc    / BAM_TO_EUR, 2)},
        "updated":  datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"),
    }


# ------------------------------ main -------------------------------

SCRAPERS = [
    ("Serbia", scrape_serbia),
    ("Montenegro", scrape_montenegro),
    ("Bosnia and Herzegovina", scrape_bosnia),
]


def main():
    countries = []
    old = {}
    if JSON_PATH.exists():
        try:
            old = json.loads(JSON_PATH.read_text())
        except Exception:
            old = {}

    for name, fn in SCRAPERS:
        try:
            countries.append(fn())
            print(f"[ok] {name} scraped")
        except Exception as exc:
            print(f"[err] {name}: {exc}")
            for c in old.get("countries", []):
                if c.get("name") == name:
                    countries.append(c)
                    print(f"[fallback] kept previous {name} data")
                    break

    payload = {"countries": countries}
    JSON_PATH.write_text(json.dumps(payload, indent=2, ensure_ascii=False))
    print(f"[done] wrote {JSON_PATH} with {len(countries)} country/countries")


if __name__ == "__main__":
    main()
