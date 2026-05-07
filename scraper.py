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
            return to_float(cells[1]
