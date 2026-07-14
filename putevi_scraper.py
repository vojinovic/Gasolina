#!/usr/bin/env python3
"""Gasolina - HERE Traffic na granicnim prelazima.

HERE prijavljuje kolone bas na rampama ("Backed-up traffic at Bajakovo"),
sto je peti nezavisan izvor za nase kartice granica. Autoputevi u Srbiji
su im slabo pokriveni, pa gledamo samo uske kutije oko prelaza.

Kljuc iz env HERE_KEY (GitHub Secret). Pise granice_here.json.
"""
import datetime
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

API = "https://data.traffic.hereapi.com/v7/incidents"

# id prelaza (isti kao borders-data.js) -> (lon, lat) rampe
CROSSINGS = {
    "gradina":      (22.7386, 43.0044),   # Gradina / Kalotina
    "horgos":       (19.9910, 46.1650),   # Horgos / Roszke
    "kelebija":     (19.6050, 46.1930),   # Kelebija / Tompa
    "batrovci":     (19.1710, 45.0400),   # Batrovci / Bajakovo
    "presevo":      (21.6400, 42.2450),   # Presevo / Tabanovce
    "sremska-raca": (19.2620, 44.8830),   # Sremska Raca
    "spiljani":     (20.3414, 42.9104),   # Spiljani / Dracenovac
    "gostun":       (19.6740, 43.2870),   # Gostun / Dobrakovo
    "bogorodica":   (22.5490, 41.1343),   # Bogorodica / Evzoni
}

PAD = 0.12   # ~12 km oko rampe

TYPES = {
    "accident": "nezgoda",
    "congestion": "kolona",
    "construction": "radovi",
    "roadClosure": "zatvoren prelaz",
    "laneRestriction": "zatvorena traka",
    "disabledVehicle": "vozilo u kvaru",
    "roadHazard": "opasnost",
}
RANK = {"critical": 0, "major": 1, "minor": 2, "low": 3}

# Incident se prihvata SAMO ako opis pominje granicni prelaz i to bas nas.
BORDER_WORDS = ("granicni prijelaz", "granicni prelaz", "granični prijelaz",
                "granični prelaz", "border crossing", "hatarat", "hataratkelo",
                "granicen premin", "customs", "carina")

# ime prelaza (i ime naspramnog GP) koje mora da se pojavi u opisu
NAMES = {
    "gradina":      ("gradina", "kalotina"),
    "horgos":       ("horgos", "roszke", "roeszke"),
    "kelebija":     ("kelebija", "tompa"),
    "batrovci":     ("batrovci", "bajakovo"),
    "presevo":      ("presevo", "tabanovce"),
    "sremska-raca": ("sremska raca", "raca"),
    "spiljani":     ("spiljani", "dracenovac"),
    "gostun":       ("gostun", "dobrakovo"),
    "bogorodica":   ("bogorodica", "evzoni", "evzonoi"),
}


def fold(s):
    for a, b in (("š","s"),("Š","s"),("đ","dj"),("Đ","dj"),("č","c"),("Č","c"),
                 ("ć","c"),("Ć","c"),("ž","z"),("Ž","z"),("á","a"),("é","e"),
                 ("í","i"),("ó","o"),("ö","o"),("ő","o"),("ú","u"),("ü","u"),("ű","u")):
        s = s.replace(a, b)
    return s.lower()


def is_at_crossing(desc, cid):
    """True samo ako opis pominje granicni prelaz I ime naseg prelaza."""
    d = fold(desc or "")
    if not any(w in d for w in BORDER_WORDS):
        return False
    return any(n in d for n in NAMES.get(cid, ()))


def fetch_box(key, lon, lat):
    w, s, e, n = lon - PAD, lat - PAD, lon + PAD, lat + PAD
    params = urllib.parse.urlencode({
        "apiKey": key,
        "in": f"bbox:{w:.4f},{s:.4f},{e:.4f},{n:.4f}",
        "locationReferencing": "none",
    })
    req = urllib.request.Request(API + "?" + params, headers={
        "User-Agent": "Gasolina/1.0 (+https://vojinovic.github.io/Gasolina)"
    })
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as ex:
        body = ""
        try:
            body = ex.read().decode("utf-8", "replace")[:200]
        except Exception:
            pass
        raise RuntimeError(f"HTTP {ex.code} | {body}") from None


def pick_worst(data, cid):
    """Najozbiljnija stavka koja se stvarno odnosi na NAS granicni prelaz."""
    best = None
    for res in data.get("results", []):
        d = res.get("incidentDetails", {}) or {}
        itype = d.get("type")
        if itype not in TYPES:
            continue
        crit = (d.get("criticality") or "").lower()
        desc = ((d.get("description") or {}).get("value") or "").strip()
        if not is_at_crossing(desc, cid):
            continue
        length_m = (res.get("location") or {}).get("length")
        item = {
            "category": TYPES[itype],
            "criticality": crit or None,
            "closed": bool(d.get("roadClosed")),
            "desc": desc[:120] or None,
            "length_km": round(length_m / 1000, 1) if length_m else None,
        }
        if best is None or RANK.get(crit, 9) < RANK.get(best["criticality"] or "", 9):
            best = item
    return best


def main():
    key = os.environ.get("HERE_KEY", "").strip()
    if not key:
        print("GRESKA: HERE_KEY nije postavljen (GitHub Secret).")
        return 1
    out = {}
    for cid, (lon, lat) in CROSSINGS.items():
        try:
            data = fetch_box(key, lon, lat)
        except Exception as ex:
            print(f"Upozorenje: {cid} nedostupan: {ex}")
            continue
        worst = pick_worst(data, cid)
        res = data.get("results", [])
        n = len(res)
        if res:
            tp = {}
            for r in res:
                dd = r.get("incidentDetails", {}) or {}
                k = f'{dd.get("type")}/{dd.get("criticality")}'
                tp[k] = tp.get(k, 0) + 1
            print(f"   [{cid}] sirovi tipovi: {tp}")
        if worst:
            out[cid] = worst
            print(f"{cid}: {n} stavki -> {worst['category']}/{worst['criticality']}"
                  f" | {worst['desc']}")
        else:
            print(f"{cid}: {n} stavki -> nista relevantno")
    result = {
        "scraped_at": datetime.datetime.now(datetime.timezone.utc)
                          .isoformat(timespec="seconds"),
        "source": "HERE Traffic",
        "crossings": out,
    }
    with open("granice_here.json", "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f"Prelaza sa prijavom: {len(out)}")
    return 0


SELFTEST = {
    "results": [
        {"location": {"length": 309.0},
         "incidentDetails": {"type": "congestion", "criticality": "minor",
                             "roadClosed": False,
                             "description": {"value": "At Granični prijelaz Bajakovo - Backed-up traffic. Approach with care"}}},
        {"location": {"length": 1200.0},
         "incidentDetails": {"type": "congestion", "criticality": "major",
                             "roadClosed": False,
                             "description": {"value": "Queuing traffic"}}},
        {"incidentDetails": {"type": "weather", "criticality": "critical",
                             "description": {"value": "Rain"}}},
    ]
}

NOISE = {
    "results": [
        {"incidentDetails": {"type": "construction", "criticality": "minor",
                             "description": {"value": "At 8001 (Novo Bardo) - Road construction"}}},
        {"incidentDetails": {"type": "roadClosure", "criticality": "critical",
                             "description": {"value": "Lezárva"}}},
    ]
}


def selftest():
    ok = True
    # Bajakovo se prihvata za batrovci
    b = pick_worst(SELFTEST, "batrovci")
    if not (b and b["category"] == "kolona" and b["length_km"] == 0.3):
        ok = False
    print("batrovci ->", json.dumps(b, ensure_ascii=False))
    # isti podatak se NE sme pripisati Sremskoj Raci
    r = pick_worst(SELFTEST, "sremska-raca")
    if r is not None:
        ok = False
    print("sremska-raca ->", r)
    # radovi kod Novog Brda se ne smeju pripisati Gradini
    g = pick_worst(NOISE, "gradina")
    if g is not None:
        ok = False
    print("gradina (sum) ->", g)
    print("SELFTEST:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(selftest())
    sys.exit(main())
