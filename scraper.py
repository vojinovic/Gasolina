"""
Gasolina fuel price scraper.
Sources:
  - Serbia:     nafta.hr (per-fuel tables, NIS row)
  - Montenegro: nafta.hr (single combined table)
  - BiH:        goriva.ba (national average from 300+ stations)
  - Slovenia:   nafta.hr (single combined table, EUR-only)
  - Macedonia:  nafta.hr (4-column table: fuel/MKD/EUR/RSD)
  - Croatia:    cijenegoriva.hr (median of INA prices)
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
BAM_TO_EUR = 1.95583  # fixed peg


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


def find_table_for_heading(soup, heading_keywords):
    for header in soup.find_all(["h2", "h3"]):
        title = header.get_text(strip=True).lower()
        if any(k.lower() in title for k in heading_keywords):
            if "premium" in title and not any("premium" in k.lower() for k in heading_keywords):
                continue
            tbl = header.find_next("table")
            if tbl:
                return tbl
    return None


def get_company_row(table, company_name):
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


def find_row_in_single_table(soup, fuel_keywords, eur_col=1, local_col=2):
    """Generic: find row by fuel name, return (col1, col2) parsed as floats."""
    for table in soup.find_all("table"):
        for row in table.find_all("tr"):
            cells = row.find_all(["td", "th"])
            if len(cells) <= max(eur_col, local_col):
                continue
            label = cells[0].get_text(strip=True).lower()
            if any(k.lower() in label for k in fuel_keywords):
                try:
                    return to_float(cells[eur_col].get_text()), to_float(cells[local_col].get_text())
                except ValueError:
                    continue
    return None


def now_utc():
    return datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")


# --------------------------- scrapers ------------------------------

def scrape_serbia():
    soup = fetch_soup("https://nafta.hr/sr/cene-goriva-srbija/")
    petrol = get_company_row(find_table_for_heading(soup, ["BMB 95 Benzin"]), "nis")
    diesel = get_company_row(find_table_for_heading(soup, ["Eurodizel"]), "nis")
    lpg    = get_company_row(find_table_for_heading(soup, ["Autoplin", "TNG", "auto plin"]), "nis")
    if not all([petrol, diesel, lpg]):
        raise RuntimeError(f"Serbia: petrol={petrol}, diesel={diesel}, lpg={lpg}")
    p_eur, p_loc = petrol; d_eur, d_loc = diesel; l_eur, l_loc = lpg
    return {
        "name": "Serbia", "flag": "🇷🇸", "currency": "RSD",
        "fx_rate_eur": round(p_loc / p_eur, 4) if p_eur else None,
        "petrol95": {"local": p_loc, "eur": p_eur},
        "diesel":   {"local": d_loc, "eur": d_eur},
        "lpg":      {"local": l_loc, "eur": l_eur},
        "updated":  now_utc(),
    }


def scrape_montenegro():
    soup = fetch_soup("https://nafta.hr/sr/cene-goriva-crna-gora/")
    petrol = find_row_in_single_table(soup, ["BMB 95"])
    diesel = find_row_in_single_table(soup, ["Eurodizel"])
    if not petrol or not diesel:
        raise RuntimeError(f"Montenegro: petrol={petrol}, diesel={diesel}")
    p_eur, _ = petrol; d_eur, _ = diesel
    return {
        "name": "Montenegro", "flag": "🇲🇪", "currency": "EUR", "fx_rate_eur": 1.0,
        "petrol95": {"local": p_eur, "eur": p_eur},
        "diesel":   {"local": d_eur, "eur": d_eur},
        "lpg":      None,
        "updated":  now_utc(),
    }


def scrape_bosnia():
    r = requests.get("https://goriva.ba/", headers=HEADERS, timeout=20)
    r.raise_for_status()
    text = BeautifulSoup(r.text, "html.parser").get_text(" ", strip=True)
    def grab(label):
        m = re.search(label + r"\s*(\d+[.,]\d+)\s*KM", text, re.IGNORECASE)
        if not m: raise ValueError(f"BiH: {label}")
        return float(m.group(1).replace(",", "."))
    petrol_loc = grab(r"Benzin\s*95")
    diesel_loc = grab(r"\bDizel\b")
    lpg_loc    = grab(r"\bLPG\b")
    return {
        "name": "Bosnia and Herzegovina", "flag": "🇧🇦", "currency": "BAM",
        "fx_rate_eur": BAM_TO_EUR,
        "petrol95": {"local": petrol_loc, "eur": round(petrol_loc / BAM_TO_EUR, 2)},
        "diesel":   {"local": diesel_loc, "eur": round(diesel_loc / BAM_TO_EUR, 2)},
        "lpg":      {"local": lpg_loc,    "eur": round(lpg_loc    / BAM_TO_EUR, 2)},
        "updated":  now_utc(),
    }


def scrape_slovenia():
    soup = fetch_soup("https://nafta.hr/sr/cene-goriva-slovenija/")
    # Slovenia table: GORIVO | CENA | PROMENA. EUR is in 'CENA' column (index 1).
    petrol = find_row_in_single_table(soup, ["BMB 95", "Benzin BMB 95"], eur_col=1, local_col=1)
    diesel = find_row_in_single_table(soup, ["Dizel"], eur_col=1, local_col=1)
    lpg    = find_row_in_single_table(soup, ["Auto gas", "TNG", "auto plin"], eur_col=1, local_col=1)
    if not all([petrol, diesel, lpg]):
        raise RuntimeError(f"Slovenia: petrol={petrol}, diesel={diesel}, lpg={lpg}")
    p_eur, _ = petrol; d_eur, _ = diesel; l_eur, _ = lpg
    return {
        "name": "Slovenia", "flag": "🇸🇮", "currency": "EUR", "fx_rate_eur": 1.0,
        "petrol95": {"local": p_eur, "eur": p_eur},
        "diesel":   {"local": d_eur, "eur": d_eur},
        "lpg":      {"local": l_eur, "eur": l_eur},
        "updated":  now_utc(),
    }


def scrape_macedonia():
    soup = fetch_soup("https://nafta.hr/sr/cene-goriva-makedonija/")
    # Table: Gorivo | MKD | EUR | DIN. local=MKD (col 1), eur=EUR (col 2).
    petrol = find_row_in_single_table(soup, ["Eurosuper 95", "BMB 95"], eur_col=2, local_col=1)
    diesel = find_row_in_single_table(soup, ["Dizel"], eur_col=2, local_col=1)
    lpg    = find_row_in_single_table(soup, ["Autoplin", "TNG"], eur_col=2, local_col=1)
    if not all([petrol, diesel, lpg]):
        raise RuntimeError(f"Macedonia: petrol={petrol}, diesel={diesel}, lpg={lpg}")
    p_eur, p_loc = petrol; d_eur, d_loc = diesel; l_eur, l_loc = lpg
    return {
        "name": "North Macedonia", "flag": "🇲🇰", "currency": "MKD",
        "fx_rate_eur": round(p_loc / p_eur, 4) if p_eur else None,
        "petrol95": {"local": p_loc, "eur": p_eur},
        "diesel":   {"local": d_loc, "eur": d_eur},
        "lpg":      {"local": l_loc, "eur": l_eur},
        "updated":  now_utc(),
    }


def scrape_croatia():
    """cijenegoriva.hr lists prices by company. We take INA medians for each fuel."""
    soup = fetch_soup("https://cijenegoriva.hr/")
    text = soup.get_text("\n", strip=True)

    def median_for(section_keyword, company_keyword="INA"):
        # Find section heading, then within it find INA block, then 'Medijan' followed by a price.
        # Strategy: scan lines, track current section, find first INA Medijan after section header.
        lines = text.split("\n")
        in_section = False
        in_company = False
        for i, line in enumerate(lines):
            low = line.lower().strip()
            # Section change
            if low.startswith("eurosuper 95") or low.startswith("eurosuper 100") \
               or low.startswith("eurodizel") or low.startswith("plavi dizel") \
               or low.startswith("lož ulje") or low.startswith("autoplin"):
                in_section = (section_keyword.lower() in low)
                in_company = False
                continue
            if not in_section:
                continue
            if company_keyword.lower() in low:
                in_company = True
                continue
            if in_company and low == "medijan":
                # next line is the price
                if i + 1 < len(lines):
                    try:
                        return to_float(lines[i + 1])
                    except Exception:
                        pass
                in_company = False
        return None

    petrol_eur = median_for("Eurosuper 95")
    diesel_eur = median_for("Eurodizel")
    lpg_eur    = median_for("Autoplin")

    if not all([petrol_eur, diesel_eur, lpg_eur]):
        raise RuntimeError(f"Croatia: petrol={petrol_eur}, diesel={diesel_eur}, lpg={lpg_eur}")

    return {
        "name": "Croatia", "flag": "🇭🇷", "currency": "EUR", "fx_rate_eur": 1.0,
        "petrol95": {"local": petrol_eur, "eur": petrol_eur},
        "diesel":   {"local": diesel_eur, "eur": diesel_eur},
        "lpg":      {"local": lpg_eur,    "eur": lpg_eur},
        "updated":  now_utc(),
    }


# ------------------------------ main -------------------------------

SCRAPERS = [
    ("Serbia", scrape_serbia),
    ("Croatia", scrape_croatia),
    ("Bosnia and Herzegovina", scrape_bosnia),
    ("Montenegro", scrape_montenegro),
    ("Slovenia", scrape_slovenia),
    ("North Macedonia", scrape_macedonia),
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
