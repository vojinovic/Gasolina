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
  - Romania:    fuel-prices.eu (EU Oil Bulletin, EUR -> RON preko kursa)
  - Kosovo:     globalpetrolprices.com (EUR)
"""

import csv
import json
import re
import sys
from datetime import datetime
from pathlib import Path

import requests
from bs4 import BeautifulSoup

HIST_PATH = Path("cene_istorija.csv")

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

MUST_LIST_URL = "https://must.gov.rs/tekst/sr/94/saopstenja.php"


def _must_latest_price_url(soup):
    """Nadji link najnovije vesti o ceni goriva na listi saopstenja Ministarstva.
    Naslov je dosledan iz nedelje u nedelju ('OBAVESTENJE O NAJVISOJ
    MALOPRODAJNOJ CENI...'), ali URL/ID vesti se menja svake nedelje pa mora
    da se trazi svaki put iznova."""
    for a in soup.find_all("a", href=True):
        text = a.get_text(" ", strip=True).lower()
        if "maloprodajnoj ceni" in text and ("derivata" in text or "goriva" in text):
            href = a["href"]
            if href.startswith("/"):
                href = "https://must.gov.rs" + href
            return href
    return None


def _must_parse_prices(text):
    """Iz teksta zvanicnog obavestenja izvuci (dizel, benzin) u dinarima.
    Format je godinama identican: 'EVRO DIZEL, u iznosu 222,00 dinara ...
    EVRO PREMIJUM BMB 95 u iznosu 198,00 dinara'."""
    d = re.search(r"EVRO\s+DIZEL[^0-9]{0,30}(\d{2,3})[,.]\d{2}\s*dinara", text, re.I)
    b = re.search(r"BMB\s*95[^0-9]{0,30}(\d{2,3})[,.]\d{2}\s*dinara", text, re.I)
    if not (d and b):
        return None
    return float(d.group(1)), float(b.group(1))


def scrape_serbia():
    # TNG uvek sa nafta.hr (Ministarstvo ne kontrolise/ne objavljuje cenu TNG-a).
    soup = fetch_soup("https://nafta.hr/sr/cene-goriva-srbija/")
    petrol_agg = get_company_row(find_table_for_heading(soup, ["BMB 95 Benzin"]), "nis")
    diesel_agg = get_company_row(find_table_for_heading(soup, ["Eurodizel"]), "nis")
    lpg        = get_company_row(find_table_for_heading(soup, ["Autoplin", "TNG", "auto plin"]), "nis")
    if not all([petrol_agg, diesel_agg, lpg]):
        raise RuntimeError(f"Serbia: petrol={petrol_agg}, diesel={diesel_agg}, lpg={lpg}")
    p_eur, p_loc = petrol_agg; d_eur, d_loc = diesel_agg; l_eur, l_loc = lpg
    fx = round(p_loc / p_eur, 4) if p_eur else None

    # Dizel i benzin: PRVO zvanicno Ministarstvo (must.gov.rs, objava petkom 15h,
    # izvor od kog svi agregatori prepisuju - nafta.hr je znao da kasni ceo dan+,
    # pa je sajt subotom pokazivao staru cenu). Ako Ministarstvo ne uspe iz bilo
    # kog razloga, ostaju agregatorske cifre - gore po svezini, ali ne pada nista.
    src_note = "nafta.hr"
    try:
        must_list = fetch_soup(MUST_LIST_URL)
        url = _must_latest_price_url(must_list)
        if url:
            must_page = fetch_soup(url)
            parsed = _must_parse_prices(must_page.get_text(" ", strip=True))
            if parsed and fx:
                d_loc, p_loc = parsed
                d_eur = round(d_loc / fx, 3)
                p_eur = round(p_loc / fx, 3)
                src_note = "must.gov.rs (zvanicno)"
                print(f"[ok] Serbia dizel/benzin sa must.gov.rs: {d_loc}/{p_loc} din")
    except Exception as ex:
        print(f"[warn] must.gov.rs nedostupan ({ex}), Serbia ostaje na nafta.hr ciframa")

    return {
        "name": "Serbia", "flag": "🇷🇸", "currency": "RSD",
        "fx_rate_eur": fx,
        "petrol95": {"local": p_loc, "eur": p_eur},
        "diesel":   {"local": d_loc, "eur": d_eur},
        "lpg":      {"local": l_loc, "eur": l_eur},
        "price_source": src_note,
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

def scrape_greece():
    """fuel-prices.eu/Greece/llms.txt - same EU Oil Bulletin format as Bulgaria."""
    url = "https://www.fuel-prices.eu/Greece/llms.txt"
    r = requests.get(url, headers=HEADERS, timeout=20)
    r.raise_for_status()
    text = r.text

    def grab(label):
        m = re.search(rf"^{label}\s+€\s*(\d+[.,]\d+)", text, re.IGNORECASE | re.MULTILINE)
        if not m:
            raise ValueError(f"Greece: missing {label}")
        return float(m.group(1).replace(",", "."))

    petrol = grab(r"Euro\s*95")
    diesel = grab(r"Diesel")

    return {
        "name": "Greece", "flag": "🇬🇷", "currency": "EUR", "fx_rate_eur": 1.0,
        "petrol95": {"local": petrol, "eur": petrol},
        "diesel":   {"local": diesel, "eur": diesel},
        "lpg":      None,
        "updated":  now_utc(),
    }

# ------------------------------ main -------------------------------

def scrape_romania():
    """fuel-prices.eu/Romania/llms.txt - EU Oil Bulletin, isti format kao Bugarska.
    Cene su u evrima; lokalna valuta je RON, pa preracunavamo preko kursa."""
    url = "https://www.fuel-prices.eu/Romania/llms.txt"
    r = requests.get(url, headers=HEADERS, timeout=20)
    r.raise_for_status()
    text = r.text

    def grab(label):
        m = re.search(rf"^{label}\s+€\s*(\d+[.,]\d+)", text, re.IGNORECASE | re.MULTILINE)
        if not m:
            raise ValueError(f"Romania: missing {label}")
        return float(m.group(1).replace(",", "."))

    petrol = grab(r"Euro\s*95")
    diesel = grab(r"Diesel")

    # kurs RON/EUR (ako ne uspe, koristimo priblizan fiksni)
    rate = 4.98
    try:
        fx = requests.get("https://api.frankfurter.app/latest?from=EUR&to=RON",
                          headers=HEADERS, timeout=10)
        if fx.ok:
            rate = float(fx.json()["rates"]["RON"])
    except Exception:
        pass

    return {
        "name": "Romania", "flag": "🇷🇴", "currency": "RON", "fx_rate_eur": round(rate, 4),
        "petrol95": {"local": round(petrol * rate, 2), "eur": petrol},
        "diesel":   {"local": round(diesel * rate, 2), "eur": diesel},
        "lpg":      None,
        "updated":  now_utc(),
    }


def scrape_kosovo():
    """globalpetrolprices.com - Kosovo koristi EUR, cene se azuriraju nedeljno."""
    petrol = diesel = None
    for fuel, key in (("gasoline_prices", "petrol"), ("diesel_prices", "diesel")):
        url = f"https://www.globalpetrolprices.com/Kosovo/{fuel}/"
        try:
            soup = fetch_soup(url)
            txt = soup.get_text(" ", strip=True)
            m = re.search(r"(\d+\.\d+)\s*(?:Euro|EUR|€)", txt)
            if not m:
                m = re.search(r"is\s+(\d+\.\d+)\s", txt)
            if m:
                val = float(m.group(1))
                if key == "petrol":
                    petrol = val
                else:
                    diesel = val
        except Exception:
            pass

    if petrol is None or diesel is None:
        raise ValueError("Kosovo: cene nisu pronadjene")

    return {
        "name": "Kosovo", "flag": "🇽🇰", "currency": "EUR", "fx_rate_eur": 1.0,
        "petrol95": {"local": petrol, "eur": petrol},
        "diesel":   {"local": diesel, "eur": diesel},
        "lpg":      None,
        "updated":  now_utc(),
    }


def append_history(countries):
    """Dopisuje cene_istorija.csv - jedan red po (zemlja, gorivo) kod svakog
    pokretanja scrapera. Bez ovoga nema nikakve istorije cena (fuel_prices.json
    se svaki put prepise, stari broj se gubi) - ovo je preduslov za bilo kakav
    min/max ili trend prikaz na frontend-u.

    NAPOMENA O UCESTALOSTI: cron za ovaj scraper trenutno ide jednom nedeljno
    (petak 18h UTC), sto znaci da ce "30-dnevni" raspon realno imati samo
    ~4 tacke podataka mesecno, ne 30. Frontend treba da to iskreno predstavi
    (npr. "raspon poslednjih N sedmica" umesto lazno preciznog "30 dana") dok
    se ne odluci da li cron treba da bude ucestaliji.
    """
    ts = now_utc()
    rows = []
    for c in countries:
        name = c.get("name")
        if not name:
            continue
        for fuel_key in ("petrol95", "diesel", "lpg"):
            f = c.get(fuel_key)
            if f and f.get("eur") is not None:
                rows.append([ts, name, fuel_key, f["eur"]])

    if not rows:
        print("Istorija cena: nema sta da se upise.")
        return

    new_file = not HIST_PATH.exists()
    with open(HIST_PATH, "a", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        if new_file:
            w.writerow(["ts", "zemlja", "gorivo", "cena_eur"])
        w.writerows(rows)
    print(f"Istorija cena: dopisano {len(rows)} redova u {HIST_PATH}")


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
    ("Greece", scrape_greece),
    ("Romania", scrape_romania),
    ("Kosovo", scrape_kosovo),
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

    append_history(countries)


def selftest():
    """Testira parsiranje zvanicnog obavestenja Ministarstva (must.gov.rs)
    protiv TACNOG teksta iz dve stvarne objave (razlicite nedelje, jedna sa
    rednim brojevima '1.'/'2.', druga bez) - bez mreze."""
    t1 = ("utvrdjuje se najvisa maloprodajna cena derivata nafte za period od "
          "15 casova 12. januara 2024. godine do 19. januara 2024. godine, i to za: "
          "EVRO DIZEL, u iznosu 194,00 dinara za jedan litar i "
          "EVRO PREMIJUM BMB 95 u iznosu 174,00 dinara za jedan litar.")
    t2 = ("i to za: 1.EVRO DIZEL, u iznosu 217,00 dinara za jedan litar i "
          "2. EVRO PREMIJUM BMB 95 u iznosu 199,00 dinara")
    ok = True
    if _must_parse_prices(t1) != (194.0, 174.0):
        ok = False
    if _must_parse_prices(t2) != (217.0, 199.0):
        ok = False
    if _must_parse_prices("nema cena u ovom tekstu") is not None:
        ok = False
    print("SELFTEST:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        raise SystemExit(selftest())
    main()
