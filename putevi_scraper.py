#!/usr/bin/env python3
"""Gasolina - stanje na putevima (TomTom Traffic Incidents).

Povlaci saobracajne incidente (zastoji, radovi, zatvaranja) duz glavnih
koridora u Srbiji i pise ih u putevi.json. API kljuc se cita iz env
promenljive TOMTOM_KEY (GitHub Secret), nikad iz koda.

Koristi TomTom Traffic API v5 (besplatno do 2.500 zahteva dnevno).
8 koridora x 48 pokretanja dnevno = ~384 zahteva, daleko ispod limita.
"""
import datetime
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

API = "https://api.tomtom.com/traffic/services/5/incidentDetails"

# koridori: (id, minLon, minLat, maxLon, maxLat) - uske kutije duz autoputeva,
# svaka ispod TomTom limita povrsine
BOXES = [
    ("bg-horgos",       19.70, 44.95, 20.25, 46.18),  # A1 sever, BG-Horgos
    ("bg-sid",          19.05, 44.70, 20.45, 45.15),  # A3, BG-Sid (Batrovci)
    ("bg-jagodina",     20.35, 44.10, 21.35, 44.95),  # A1, BG-Jagodina
    ("jagodina-nis",    21.00, 43.25, 21.95, 44.15),  # A1, Jagodina-Nis
    ("nis-presevo",     21.50, 42.25, 22.20, 43.35),  # A1 jug, Nis-Presevo
    ("nis-gradina",     21.85, 42.95, 22.70, 43.40),  # A4, Nis-Gradina
    ("bg-preljina",     20.00, 43.80, 20.60, 44.70),  # Milos Veliki
    ("zlatibor-gostun", 19.40, 43.15, 20.35, 43.90),  # Zlatibor-Gostun
]

# TomTom iconCategory -> srpski opis (zadrzavamo samo bitne)
CATS = {
    1: "nezgoda",
    6: "zastoj",
    7: "zatvorena traka",
    8: "zatvoren put",
    9: "radovi na putu",
    14: "vozilo u kvaru",
}

FIELDS = ("{incidents{properties{id,iconCategory,magnitudeOfDelay,"
          "from,to,length,delay,roadNumbers,events{description}}}}")


def fetch_box(key, box):
    cid, lo1, la1, lo2, la2 = box
    params = urllib.parse.urlencode({
        "key": key,
        "bbox": f"{lo1},{la1},{lo2},{la2}",
        "fields": FIELDS,
        "language": "en-GB",
        "categoryFilter": ",".join(str(c) for c in CATS),
        "timeValidityFilter": "present",
    })
    req = urllib.request.Request(API + "?" + params, headers={
        "User-Agent": "Gasolina/1.0 (+https://vojinovic.github.io/Gasolina)"
    })
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = ""
        try:
            body = e.read().decode("utf-8", "replace")[:400]
        except Exception:
            pass
        raise RuntimeError(f"HTTP {e.code} | odgovor: {body}") from None


def parse_incidents(data, corridor):
    """TomTom odgovor -> lista nasih incidenata za dat koridor."""
    out = []
    for inc in data.get("incidents", []):
        p = inc.get("properties", {})
        cat = p.get("iconCategory")
        if cat not in CATS:
            continue
        delay_min = round((p.get("delay") or 0) / 60)
        length_km = round((p.get("length") or 0) / 1000, 1)
        # zadrzimo samo znacajno: kasnjenje 5+ min, ili zatvaranja/radove
        if delay_min < 5 and cat not in (8, 9):
            continue
        out.append({
            "id": p.get("id"),
            "corridor": corridor,
            "category": CATS[cat],
            "road": ", ".join(p.get("roadNumbers") or []) or None,
            "from": p.get("from"),
            "to": p.get("to"),
            "delay_min": delay_min if delay_min > 0 else None,
            "length_km": length_km if length_km > 0 else None,
        })
    return out


def main():
    key = os.environ.get("TOMTOM_KEY", "").strip()
    if not key:
        print("GRESKA: TOMTOM_KEY nije postavljen (GitHub Secret).")
        return 1
    print(f"TOMTOM_KEY: duzina {len(key)}, pocinje '{key[:4]}', zavrsava '{key[-4:]}'")
    seen, incidents = set(), []
    for box in BOXES:
        try:
            data = fetch_box(key, box)
        except Exception as e:
            print(f"Upozorenje: {box[0]} nedostupan: {e}")
            continue
        got = parse_incidents(data, box[0])
        print(f"{box[0]}: {len(got)} incidenata")
        for inc in got:
            if inc["id"] in seen:
                continue
            seen.add(inc["id"])
            incidents.append(inc)
    incidents.sort(key=lambda x: -(x["delay_min"] or 0))
    result = {
        "scraped_at": datetime.datetime.now(datetime.timezone.utc)
                          .isoformat(timespec="seconds"),
        "source": "TomTom Traffic",
        "incidents": incidents[:40],
    }
    with open("putevi.json", "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f"Ukupno upisano: {len(result['incidents'])}")
    return 0


SELFTEST_RESPONSE = {
    "incidents": [
        {"properties": {"id": "a1", "iconCategory": 6, "magnitudeOfDelay": 3,
                        "from": "Vranje", "to": "Bujanovac", "length": 3200,
                        "delay": 1500, "roadNumbers": ["A1"],
                        "events": [{"description": "Stationary traffic"}]}},
        {"properties": {"id": "a2", "iconCategory": 9, "magnitudeOfDelay": 0,
                        "from": "Petlja Nis", "to": "Petlja Merosina",
                        "length": 800, "delay": 0, "roadNumbers": ["A1"],
                        "events": [{"description": "Roadworks"}]}},
        {"properties": {"id": "a3", "iconCategory": 6, "magnitudeOfDelay": 1,
                        "from": "X", "to": "Y", "length": 200,
                        "delay": 120, "roadNumbers": [],
                        "events": [{"description": "Queuing traffic"}]}},
    ]
}


def selftest():
    got = parse_incidents(SELFTEST_RESPONSE, "nis-presevo")
    ok = True
    # a1: zastoj 25 min -> ostaje; a2: radovi bez kasnjenja -> ostaje (cat 9);
    # a3: zastoj 2 min -> ispada (ispod praga)
    if len(got) != 2:
        ok = False
    if not (got and got[0]["delay_min"] == 25 and got[0]["category"] == "zastoj"):
        ok = False
    if not (len(got) > 1 and got[1]["category"] == "radovi na putu"
            and got[1]["delay_min"] is None):
        ok = False
    print(json.dumps(got, ensure_ascii=False, indent=2))
    print("SELFTEST:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(selftest())
    sys.exit(main())
