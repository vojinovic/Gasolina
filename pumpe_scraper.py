#!/usr/bin/env python3
"""Gasolina - pumpe na ruti (OpenStreetMap / Overpass API).

Povlaci benzinske pumpe (amenity=fuel) duz glavnih koridora i pise pumpe.json.
Bez API kljuca. Pumpe se retko menjaju, pa je dovoljno jednom nedeljno.

Za svaku pumpu cuvamo: brend, zemlju, koridor, koordinate i koja goriva ima.
Cene NE dolaze odavde (OSM ih nema pouzdano) - sajt ih spaja sa cenom brenda
iz fuel_prices.json.
"""
import datetime
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

OVERPASS = "https://overpass-api.de/api/interpreter"

# koridori: (id, opis, W, S, E, N) - pojas oko autoputa/magistrale
CORRIDORS = [
    ("bg-horgos",   "A1 Beograd - Horgos",        19.60, 44.75, 20.60, 46.20),
    ("bg-sid",      "A3 Beograd - Batrovci",      19.00, 44.70, 20.60, 45.20),
    ("bg-nis",      "A1 Beograd - Nis",           20.30, 43.20, 21.95, 44.95),
    ("nis-presevo", "A1 Nis - Presevo",           21.45, 42.25, 22.20, 43.35),
    ("nis-gradina", "A4 Nis - Gradina",           21.80, 42.90, 22.75, 43.45),
    ("bg-cacak",    "A2 Milos Veliki (ka CG)",    19.95, 43.75, 20.65, 44.75),
    ("cacak-gostun", "Zlatibor - Gostun",         19.35, 43.10, 20.40, 43.95),
    ("bg-loznica",  "Ka Sremskoj Raci / BiH",     19.10, 44.55, 19.90, 45.00),
]

# brend -> normalizovano ime (da se poklopi sa cenama i da lepo izgleda)
BRAND_MAP = {
    "nis petrol": "NIS Petrol", "nis": "NIS Petrol", "gazprom": "Gazprom",
    "gazprom neft": "Gazprom", "lukoil": "Lukoil", "omv": "OMV",
    "mol": "MOL", "eko": "EKO", "shell": "Shell", "knez petrol": "Knez Petrol",
    "eurodiesel": "Euro Diesel", "euro petrol": "Euro Petrol",
    "ina": "INA", "petrol": "Petrol", "avia": "Avia", "mrk": "MRK",
}


def norm_brand(tags):
    raw = (tags.get("brand") or tags.get("operator") or tags.get("name") or "").strip()
    low = raw.lower()
    for key, val in BRAND_MAP.items():
        if key in low:
            return val
    return raw or "Nepoznata pumpa"


def fetch_corridor(cid, w, s, e, n, tries=3):
    q = f"""
    [out:json][timeout:60];
    node["amenity"="fuel"]({s},{w},{n},{e});
    out body;
    """
    data = urllib.parse.urlencode({"data": q}).encode()
    req = urllib.request.Request(OVERPASS, data=data, headers={
        "User-Agent": "Gasolina/1.0 (+https://gasolina.rs)"
    })
    for i in range(tries):
        try:
            with urllib.request.urlopen(req, timeout=90) as r:
                return json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as ex:
            if ex.code == 429 and i < tries - 1:
                print(f"   {cid}: rate limit, cekam 30s...")
                time.sleep(30)
                continue
            raise RuntimeError(f"HTTP {ex.code}") from None
    raise RuntimeError("nije uspelo posle vise pokusaja")


def parse(data, cid):
    out = []
    for el in data.get("elements", []):
        t = el.get("tags", {}) or {}
        fuels = []
        if t.get("fuel:diesel") == "yes":
            fuels.append("dizel")
        if t.get("fuel:octane_95") == "yes" or t.get("fuel:octane_98") == "yes":
            fuels.append("benzin")
        if t.get("fuel:lpg") == "yes":
            fuels.append("tng")
        if t.get("fuel:electricity") == "yes":
            fuels.append("struja")
        out.append({
            "id": el.get("id"),
            "corridor": cid,
            "brand": norm_brand(t),
            "lat": round(el.get("lat", 0), 5),
            "lon": round(el.get("lon", 0), 5),
            "fuels": fuels or None,
            "open24": t.get("opening_hours") == "24/7" or None,
        })
    return out


def main():
    all_st, seen = [], set()
    for cid, desc, w, s, e, n in CORRIDORS:
        try:
            data = fetch_corridor(cid, w, s, e, n)
        except Exception as ex:
            print(f"Upozorenje: {cid} nedostupan: {ex}")
            continue
        got = parse(data, cid)
        new = 0
        for st in got:
            if st["id"] in seen:
                continue
            seen.add(st["id"])
            all_st.append(st)
            new += 1
        print(f"{cid} ({desc}): {len(got)} pumpi, {new} novih")
        time.sleep(2)   # ljubazno prema Overpass serveru

    # statistika po brendu
    brands = {}
    for st in all_st:
        brands[st["brand"]] = brands.get(st["brand"], 0) + 1
    top = sorted(brands.items(), key=lambda x: -x[1])[:10]
    print("\nNajcesci brendovi:", ", ".join(f"{b} ({c})" for b, c in top))

    result = {
        "scraped_at": datetime.datetime.now(datetime.timezone.utc)
                          .isoformat(timespec="seconds"),
        "source": "OpenStreetMap (Overpass API)",
        "count": len(all_st),
        "stations": all_st,
    }
    with open("pumpe.json", "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f"\nUkupno upisano: {len(all_st)} pumpi")
    return 0


SELFTEST = {
    "elements": [
        {"id": 1, "lat": 44.7866, "lon": 20.4489,
         "tags": {"amenity": "fuel", "brand": "NIS Petrol",
                  "fuel:diesel": "yes", "fuel:octane_95": "yes",
                  "fuel:lpg": "yes", "opening_hours": "24/7"}},
        {"id": 2, "lat": 44.0128, "lon": 20.9114,
         "tags": {"amenity": "fuel", "operator": "Lukoil Srbija",
                  "fuel:diesel": "yes"}},
        {"id": 3, "lat": 43.3209, "lon": 21.8958,
         "tags": {"amenity": "fuel", "name": "Pumpa kod Mite"}},
    ]
}


def selftest():
    got = parse(SELFTEST, "bg-nis")
    ok = True
    if len(got) != 3:
        ok = False
    if got[0]["brand"] != "NIS Petrol" or "tng" not in (got[0]["fuels"] or []):
        ok = False
    if got[1]["brand"] != "Lukoil":
        ok = False
    if got[2]["brand"] != "Pumpa kod Mite" or got[2]["fuels"] is not None:
        ok = False
    print(json.dumps(got, ensure_ascii=False, indent=2))
    print("SELFTEST:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(selftest())
    sys.exit(main())
