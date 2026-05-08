"""
Gasolina fuel price scraper.
Sources:
  - Serbia:     nafta.hr (per-fuel tables, NIS row)
  - Croatia:    cijenegoriva.hr (median of INA prices)
  - BiH:        goriva.ba (national average from 300+ stations)
  - Montenegro: nafta.hr (single combined table)
  - Slovenia:   nafta.hr (single combined table, EUR-only)
  - Macedonia:  nafta.hr (4-column table: fuel/MKD/EUR/RSD)
  - Hungary:    nafta.hr (Min/Avg/Max EUR table)
  - Bulgaria:   fuel-prices.eu (EU Oil Bulletin, machine-readable)
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


def scrape_croatia():
    soup = fetch_soup("https://cijenegoriva.hr/")

    def median_under_section(section_keyword: str, company: str = "INA"):
        for h2 in soup.find_all("h2"):
            if section_keyword.lower() not in h2.get_text(strip=True).lower():
                continue
            for sib in h2.find_all_next():
                if sib.name == "h2" and sib is not h2:
                    break
                if sib.name == "h3" and company.lower() in sib.get_text(strip=True).lower():
                    block_text = ""
                    for after in sib.find_all_next():
                        if after.name in ("h2", "h3"):
                            break
                        block_text += " " + after.get_text(" ", strip=True)
                    m = re.search(r"medijan[^0-9]*([0-9]+[.,][0-9]+)", block_text, re.IGNORECASE)
                    if m:
                        try:
                            return float(m.group(1).replace(",", "."))
                        except ValueError:
                            pass
            break
        return None

    petrol_eur = median_under_section("Eurosuper 95")
    diesel_eur = median_under_section("Eurodizel")
    lpg_eur    = median_under_section("Autoplin")

    if not all([petrol_eur, diesel_eur, lpg_eur]):
        raise RuntimeError(f"Croatia: petrol={petrol_eur}, diesel={diesel_eur}, lpg={lpg_eur}")

    return {
        "name": "Croatia", "flag": "🇭🇷", "currency": "EUR", "fx_rate_eur": 1.0,
        "petrol95": {"local": petrol_eur, "eur": petrol_eur},
        "diesel":   {"local": diesel_eur, "eur": diesel_eur},
        "lpg":      {"local": lpg_eur,    "eur": lpg_eur},
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


def scrape_slovenia():
    soup = fetch_soup("https://nafta.hr/sr/cene-goriva-slovenija/")
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


def scrape_hungary():
    """Hungary table format: Gorivo | Min EUR | Avg EUR | Max EUR. We use Avg column."""
    soup = fetch_soup("https://nafta.hr/sr/cene-goriva-madarska/")
    petrol = find_row_in_single_table(soup, ["Eurosuper 95 E10", "Eurosuper 95"], eur_col=2, local_col=2)
    diesel = find_row_in_single_table(soup, ["Dizel"], eur_col=2, local_col=2)
    lpg    = find_row_in_single_table(soup, ["Autoplin", "LPG"], eur_col=2, local_col=2)
    if not all([petrol, diesel, lpg]):
        raise RuntimeError(f"Hungary: petrol={petrol}, diesel={diesel}, lpg={lpg}")
    p_eur, _ = petrol; d_eur, _ = diesel; l_eur, _ = lpg
    return {
        "name": "Hungary", "flag": "🇭🇺", "currency": "EUR", "fx_rate_eur": 1.0,
        "petrol95": {"local": p_eur, "eur": p_eur},
        "diesel":   {"local": d_eur, "eur": d_eur},
        "lpg":      {"local": l_eur, "eur": l_eur},
        "updated":  now_utc(),
    }


def scrape_bulgaria():
    """fuel-prices.eu/Bulgaria/llms.txt - clean machine-readable format from EU Oil Bulletin."""
    url = "https://www.fuel-prices.eu/Bulgaria/llms.txt"
    r = requests.get(url, headers=HEADERS, timeout=20)
    r.raise_for_status()
    text = r.text

    def grab(label):
        m = re.search(rf"^{label}\s+€\s*(\d+[.,]\d+)", text, re.IGNORECASE | re.MULTILINE)
        if not m:
            raise ValueError(f"Bulgaria: missing {label}")
        return float(m.group(1).replace(",", "."))

    petrol = grab(r"Euro\s*95")
    diesel = grab(r"Diesel")

    return {
        "name": "Bulgaria", "flag": "🇧🇬", "currency": "EUR", "fx_rate_eur": 1.0,
        "petrol95": {"local": petrol, "eur": petrol},
        "diesel":   {"local": diesel, "eur": diesel},
        "lpg":      None,
        "updated":  now_utc(),
    }
  
def scrape_albania():
    """globalpetrolprices.com - prices in ALL (Albanian Lek), updated monthly.
    If scraping fails, falls back to last-known regulated prices.
    """
    # Albania uses fixed regulated prices set by Bordi i Transparencës (Transparency Board).
    # Latest known prices (May 2026):
    FALLBACK = {"petrol_all": 179.0, "diesel_all": 193.0, "lpg_all": 57.0}
    ALL_TO_EUR = 100.0  # approx 1 EUR = 100 ALL (varies 98-102; close enough for display)

    # Try to fetch fresh data from globalpetrolprices.com.
    petrol = diesel = lpg = None
    try:
        r = requests.get(
            "https://www.globalpetrolprices.com/Albania/gasoline_prices/",
            headers=HEADERS, timeout=15,
        )
        if r.ok:
            m = re.search(r"price of octane-95 gasoline is\s*([\d.]+)\s*Albanian Lek", r.text, re.IGNORECASE)
            if m: petrol = float(m.group(1))
    except Exception as exc:
        print(f"[warn] Albania petrol fetch: {exc}")

    try:
        r = requests.get(
            "https://www.globalpetrolprices.com/Albania/diesel_prices/",
            headers=HEADERS, timeout=15,
        )
        if r.ok:
            m = re.search(r"price of diesel is\s*([\d.]+)\s*Albanian Lek", r.text, re.IGNORECASE)
            if m: diesel = float(m.group(1))
    except Exception as exc:
        print(f"[warn] Albania diesel fetch: {exc}")

    try:
        r = requests.get(
            "https://www.globalpetrolprices.com/Albania/lpg_prices/",
            headers=HEADERS, timeout=15,
        )
        if r.ok:
            m = re.search(r"price of autogas is\s*([\d.]+)\s*Albanian Lek", r.text, re.IGNORECASE)
            if m: lpg = float(m.group(1))
    except Exception as exc:
        print(f"[warn] Albania lpg fetch: {exc}")

    # Use fallbacks if scraping failed
    if petrol is None:
        print("[fallback] Albania petrol using static value")
        petrol = FALLBACK["petrol_all"]
    if diesel is None:
        print("[fallback] Albania diesel using static value")
        diesel = FALLBACK["diesel_all"]
    if lpg is None:
        print("[fallback] Albania lpg using static value")
        lpg = FALLBACK["lpg_all"]

    return {
        "name": "Albania", "flag": "🇦🇱", "currency": "ALL",
        "fx_rate_eur": ALL_TO_EUR,
        "petrol95": {"local": petrol, "eur": round(petrol / ALL_TO_EUR, 2)},
        "diesel":   {"local": diesel, "eur": round(diesel / ALL_TO_EUR, 2)},
        "lpg":      {"local": lpg,    "eur": round(lpg    / ALL_TO_EUR, 2)},
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
    ("Hungary", scrape_hungary),
    ("Bulgaria", scrape_bulgaria),
    ("Albania", scrape_albania),
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
