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

OVERPASS_MIRRORS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://overpass.osm.ch/api/interpreter",
]

# koridori: (id, opis, W, S, E, N, zemlja) - pojas oko autoputa/magistrale
CORRIDORS = [
    ("bg-horgos",   "A1 Beograd - Novi Sad",      19.75, 45.05, 20.55, 45.65, "RS"),
    ("bg-horgos",   "A1 Novi Sad - Horgos",       19.55, 45.55, 20.20, 46.20, "RS"),
    ("bg-sid",      "A3 Beograd - Ruma",          19.85, 44.75, 20.55, 45.15, "RS"),
    ("bg-sid",      "A3 Ruma - Batrovci",         19.00, 44.75, 19.95, 45.15, "RS"),
    ("bg-nis",      "A1 Beograd - Velika Plana",  20.35, 44.30, 21.05, 44.90, "RS"),
    ("bg-nis",      "A1 Velika Plana - Jagodina", 20.90, 43.85, 21.40, 44.45, "RS"),
    ("bg-nis",      "A1 Jagodina - Nis",          21.05, 43.20, 21.95, 44.05, "RS"),
    ("nis-presevo", "A1 Nis - Presevo",           21.45, 42.25, 22.20, 43.35, "RS"),
    ("nis-gradina", "A4 Nis - Gradina",           21.80, 42.90, 22.75, 43.45, "RS"),
    ("bg-cacak",    "A2 Milos Veliki (ka CG)",    19.95, 43.75, 20.65, 44.75, "RS"),
    ("cacak-gostun", "Zlatibor - Gostun",         19.35, 43.10, 20.40, 43.95, "RS"),
    ("bg-loznica",  "Ka Sremskoj Raci / BiH",     19.10, 44.55, 19.90, 45.00, "RS"),
    # Prva zemlja van Srbije - trazio Ivan konkretno za Nis-Sarti/Solun rute.
    # Pokriva ceo A1 kroz Makedoniju: Tabanovce (granica) - Kumanovo - Skopje -
    # Veles - Negotino - Gevgelija - Bogorodica (granica ka Grckoj).
    ("mk-transit",  "A1 Tabanovce - Skopje (MK)", 21.30, 41.85, 21.90, 42.45, "MK"),
    ("mk-transit",  "A1 Skopje - Bogorodica (MK)", 21.90, 41.00, 22.70, 42.05, "MK"),
]

# cirilica -> latinica (OSM ima i "НИС Петрол" i "NIS Petrol")
CYR = {
    "а":"a","б":"b","в":"v","г":"g","д":"d","ђ":"dj","е":"e","ж":"z","з":"z",
    "и":"i","ј":"j","к":"k","л":"l","љ":"lj","м":"m","н":"n","њ":"nj","о":"o",
    "п":"p","р":"r","с":"s","т":"t","ћ":"c","у":"u","ф":"f","х":"h","ц":"c",
    "ч":"c","џ":"dz","ш":"s",
}


def translit(s):
    return "".join(CYR.get(ch, ch) for ch in s.lower())


# Prepoznajemo brend po CELIM RECIMA, ne po delu reci.
# Inace "Ranis Petrol" -> NIS, a "Jugopetrol/MB Petrol" -> slovenacki Petrol.
# Kljuc je torka reci koje moraju sve da postoje u imenu.
BRAND_RULES = [
    (("nis", "petrol"), "NIS Petrol"),
    (("knez", "petrol"), "Knez Petrol"),
    (("euro", "petrol"), "Euro Petrol"),
    (("eurodiesel",), "Euro Diesel"),
    (("gazprom",), "Gazprom"),
    (("gaspromnjeft",), "Gazprom"),
    (("lukoil",), "Lukoil"),
    (("omv",), "OMV"),
    (("mol",), "MOL"),
    (("shell",), "Shell"),
    (("coral",), "Shell"),          # Coral radi Shell pumpe po licenci na delu Balkana
    (("eko",), "EKO"),
    (("ina",), "INA"),
    (("avia",), "Avia"),
    (("mrk",), "MRK"),
    (("jugopetrol",), "Jugopetrol"),
    (("beopetrol",), "Beopetrol"),
    (("nis",), "NIS Petrol"),       # samostalna rec "nis"
    # Makedonija - Makpetrol i Lukoil su ubedljivo najpreporucivaniji medju
    # srpskim vozacima (potvrdjeno iz vise izvora), OKTA/Gulf/Jetoil/Avin manje
    # cesti ali realni. Pucko Petrol treba par reci da se ne pobrka sa genericnim
    # "petrol" pravilom ispod.
    (("makpetrol",), "Makpetrol"),
    (("okta",), "OKTA"),
    (("gulf",), "Gulf"),
    (("jetoil",), "Jetoil"),
    (("avin",), "Avin"),
    (("pucko", "petrol"), "Pucko Petrol"),
]

# Ovi brendovi se priznaju SAMO ako je ime tacno ta rec (mozda uz d.o.o/d.d.),
# da "MB Petrol" ili "Sunny Petrol" ne postanu slovenacki Petrol.
EXACT_ONLY = {
    "petrol": "Petrol",
}
FILLER = {"doo", "dd", "ad", "d", "o", "srbija", "serbia",
          "benzinska", "stanica", "pumpa", "gas"}

WORD_RE = re.compile(r"[a-z0-9]+")


def norm_brand(tags):
    raw = (tags.get("brand") or tags.get("operator") or tags.get("name") or "").strip()
    if not raw:
        return "Nepoznata pumpa"
    words = set(WORD_RE.findall(translit(raw)))
    for keys, val in BRAND_RULES:
        if all(k in words for k in keys):
            return val
    core = words - FILLER
    if len(core) == 1:
        only = next(iter(core))
        if only in EXACT_ONLY:
            return EXACT_ONLY[only]
    return raw


def fetch_corridor(cid, w, s, e, n):
    """Proba svako ogledalo redom, sa ponovnim pokusajima na 429/504."""
    q = f"""
    [out:json][timeout:180];
    node["amenity"="fuel"]({s},{w},{n},{e});
    out body;
    """
    data = urllib.parse.urlencode({"data": q}).encode()
    last = None
    for mirror in OVERPASS_MIRRORS:
        for attempt in range(2):
            req = urllib.request.Request(mirror, data=data, headers={
                "User-Agent": "Gasolina/1.0 (+https://gasolina.rs)"
            })
            try:
                with urllib.request.urlopen(req, timeout=180) as r:
                    return json.loads(r.read().decode("utf-8"))
            except urllib.error.HTTPError as ex:
                last = f"HTTP {ex.code}"
                if ex.code in (429, 504):
                    wait = 25 if ex.code == 429 else 15
                    print(f"   {cid}: {last} na {mirror.split('/')[2]}, cekam {wait}s...")
                    time.sleep(wait)
                    continue
                break   # druga greska -> odmah na sledece ogledalo
            except Exception as ex:
                last = str(ex)
                time.sleep(10)
                continue
        print(f"   {cid}: prelazim na sledece ogledalo...")
    raise RuntimeError(last or "sva ogledala su pala")


def parse(data, cid, country="RS"):
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
            "country": country,
            "brand": norm_brand(t),
            "lat": round(el.get("lat", 0), 5),
            "lon": round(el.get("lon", 0), 5),
            "fuels": fuels or None,
            "open24": t.get("opening_hours") == "24/7" or None,
        })
    return out


def load_previous():
    try:
        with open("pumpe.json", encoding="utf-8") as f:
            return json.load(f).get("stations", [])
    except Exception:
        return []


def main():
    prev = load_previous()
    all_st, seen = [], set()
    failed = set()
    for cid, desc, w, s, e, n, country in CORRIDORS:
        try:
            data = fetch_corridor(cid, w, s, e, n)
        except Exception as ex:
            print(f"Upozorenje: {cid} nedostupan: {ex}")
            failed.add(cid)
            continue
        got = parse(data, cid, country)
        new = 0
        for st in got:
            if st["id"] in seen:
                continue
            seen.add(st["id"])
            all_st.append(st)
            new += 1
        print(f"{cid} ({desc}): {len(got)} pumpi, {new} novih")
        time.sleep(6)   # ljubazno prema Overpass serveru (izbegava 429/504)

    # koridor koji je pao -> zadrzi prosle pumpe (bolje stare nego nikakve)
    if failed and prev:
        kept = 0
        for st in prev:
            if st.get("corridor") in failed and st.get("id") not in seen:
                seen.add(st["id"])
                all_st.append(st)
                kept += 1
        if kept:
            print(f"\n[fallback] zadrzano {kept} pumpi iz prethodnog upisa "
                  f"za koridore: {', '.join(sorted(failed))}")

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
        {"id": 4, "lat": 44.5, "lon": 20.5,
         "tags": {"amenity": "fuel", "brand": "НИС Петрол", "fuel:diesel": "yes"}},
        {"id": 5, "lat": 44.6, "lon": 20.6,
         "tags": {"amenity": "fuel", "brand": "Кнез Петрол"}},
        {"id": 6, "lat": 42.0, "lon": 21.43,
         "tags": {"amenity": "fuel", "brand": "Makpetrol", "fuel:diesel": "yes"}},
        {"id": 7, "lat": 41.14, "lon": 22.50,
         "tags": {"amenity": "fuel", "brand": "Pucko Petrol"}},
    ]
}


def selftest():
    got = parse(SELFTEST, "bg-nis")   # default country="RS"
    ok = True
    if len(got) != 7:
        ok = False
    if got[3]["brand"] != "NIS Petrol":   # cirilica -> latinica
        ok = False
    if got[4]["brand"] != "Knez Petrol":
        ok = False
    if got[0]["brand"] != "NIS Petrol" or "tng" not in (got[0]["fuels"] or []):
        ok = False
    if got[1]["brand"] != "Lukoil":
        ok = False
    if got[2]["brand"] != "Pumpa kod Mite" or got[2]["fuels"] is not None:
        ok = False
    if got[0]["country"] != "RS":
        ok = False
    got_mk = parse(SELFTEST, "mk-transit", "MK")
    if got_mk[5]["brand"] != "Makpetrol" or got_mk[5]["country"] != "MK":
        ok = False
    if got_mk[6]["brand"] != "Pucko Petrol":   # ne sme da padne na genericni "Petrol"
        ok = False
    print(json.dumps(got, ensure_ascii=False, indent=2))
    print("SELFTEST:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(selftest())
    sys.exit(main())
