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
    "batrovci":     (19.1710, 45.0400),   # Batrovci / Bajakovo
    "presevo":      (21.6400, 42.2450),   # Presevo / Tabanovce
    "sremska-raca": (19.2620, 44.8830),   # Sremska Raca
    "spiljani":     (20.3414, 42.9104),   # Spiljani / Dracenovac
    "gostun":       (19.6740, 43.2870),   # Gostun / Dobrakovo
    "bogorodica":   (22.5490, 41.1343),   # Bogorodica / Evzoni
}

PAD = 0.06   # ~6 km oko rampe (kutija ~12x12 km, daleko ispod HERE limita)

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


def pick_worst(data):
    """Iz HERE odgovora izvuci najozbiljniju stavku za prelaz."""
    best = None
    for res in data.get("results", []):
        d = res.get("incidentDetails", {}) or {}
        itype = d.get("type")
        if itype not in TYPES:
            continue
        crit = (d.get("criticality") or "").lower()
        desc = ((d.get("description") or {}).get("value") or "").strip()
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
        worst = pick_worst(data)
        n = len(data.get("results", []))
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
                             "description": {"value": "At Granicni prijelaz Bajakovo - Backed-up traffic. Approach with care"}}},
        {"location": {"length": 1200.0},
         "incidentDetails": {"type": "congestion", "criticality": "major",
                             "roadClosed": False,
                             "description": {"value": "Queuing traffic"}}},
        {"incidentDetails": {"type": "weather", "criticality": "critical",
                             "description": {"value": "Rain"}}},
    ]
}


def selftest():
    got = pick_worst(SELFTEST)
    ok = (got and got["category"] == "kolona" and got["criticality"] == "major"
          and got["length_km"] == 1.2)
    print(json.dumps(got, ensure_ascii=False, indent=2))
    print("SELFTEST:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(selftest())
    sys.exit(main())
