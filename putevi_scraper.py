#!/usr/bin/env python3
"""Gasolina - stanje na putevima (HERE Traffic API v7).

Povlaci saobracajne incidente duz glavnih koridora u Srbiji i pise ih
u putevi.json. API kljuc se cita iz env promenljive HERE_KEY (GitHub Secret).

Izlaz je isti oblik kao ranija TomTom verzija, pa index.html ostaje isti.
"""
import datetime
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

API = "https://data.traffic.hereapi.com/v7/incidents"

# koridori: (id, W, S, E, N) - HERE bbox: west,south,east,north
# VAZNO: HERE dozvoljava max 1 stepen sirine i visine po kutiji,
# pa su duzi koridori podeljeni na vise segmenata.
BOXES = [
    ("bg-horgos",       19.70, 45.20, 20.25, 46.15),  # A1 sever (Subotica-Horgos)
    ("bg-horgos",       19.80, 44.75, 20.55, 45.60),  # A1 sever (BG-Novi Sad)
    ("bg-sid",          19.05, 44.75, 19.95, 45.15),  # A3 zapad (Sid-Ruma)
    ("bg-sid",          19.90, 44.70, 20.55, 45.10),  # A3 istok (Ruma-BG)
    ("bg-jagodina",     20.35, 44.10, 21.30, 44.90),  # A1, BG-Jagodina
    ("jagodina-nis",    21.00, 43.30, 21.95, 44.15),  # A1, Jagodina-Nis
    ("nis-presevo",     21.55, 42.30, 22.20, 43.25),  # A1 jug, Nis-Presevo
    ("nis-gradina",     21.85, 42.95, 22.70, 43.40),  # A4, Nis-Gradina
    ("bg-preljina",     20.00, 43.85, 20.60, 44.70),  # Milos Veliki
    ("zlatibor-gostun", 19.40, 43.20, 20.35, 43.90),  # Zlatibor-Gostun
]

TYPES = {
    "accident": "nezgoda",
    "congestion": "zastoj",
    "construction": "radovi na putu",
    "roadClosure": "zatvoren put",
    "laneRestriction": "zatvorena traka",
    "disabledVehicle": "vozilo u kvaru",
    "roadHazard": "opasnost na putu",
}
KEEP = set(TYPES)


def fetch_box(key, box):
    cid, w, s, e, n = box
    params = urllib.parse.urlencode({
        "apiKey": key,
        "in": f"bbox:{w},{s},{e},{n}",
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
            body = ex.read().decode("utf-8", "replace")[:300]
        except Exception:
            pass
        raise RuntimeError(f"HTTP {ex.code} | odgovor: {body}") from None


def parse_incidents(data, corridor, debug=False):
    """HERE odgovor -> lista nasih incidenata."""
    results = data.get("results", [])
    if debug:
        types = {}
        for res in results:
            d = res.get("incidentDetails", {}) or {}
            k = f'{d.get("type")}/{d.get("criticality")}'
            types[k] = types.get(k, 0) + 1
        print(f"   sirovo: {len(results)} stavki, tipovi: {types or '-'}")
    out = []
    for res in results:
        d = res.get("incidentDetails", {}) or {}
        itype = d.get("type")
        if itype not in KEEP:
            continue
        crit = (d.get("criticality") or "").lower()
        desc = ((d.get("description") or {}).get("value")
                or (d.get("summary") or {}).get("value") or "").strip()
        # Filter je namerno blag: HERE u Srbiji cesto oznaci sve kao 'low',
        # pa bi strog filter obrisao sve. Prikaz sortira po ozbiljnosti.
        out.append({
            "id": d.get("id"),
            "corridor": corridor,
            "category": TYPES.get(itype, itype),
            "criticality": crit or None,
            "road": None,
            "from": desc[:90] if desc else None,
            "to": None,
            "delay_min": None,
            "length_km": None,
        })
    return out


def main():
    key = os.environ.get("HERE_KEY", "").strip()
    if not key:
        print("GRESKA: HERE_KEY nije postavljen (GitHub Secret).")
        return 1
    print(f"HERE_KEY: duzina {len(key)}, pocinje '{key[:4]}'")
    seen, incidents = set(), []
    dumped = {"done": False}
    for box in BOXES:
        try:
            data = fetch_box(key, box)
        except Exception as ex:
            print(f"Upozorenje: {box[0]} nedostupan: {ex}")
            continue
        got = parse_incidents(data, box[0], debug=True)
        print(f"{box[0]}: {len(got)} incidenata (posle filtera)")
        if data.get("results") and not dumped["done"]:
            print("   PRIMER sirove stavke:")
            print("   " + json.dumps(data["results"][0], ensure_ascii=False)[:600])
            dumped["done"] = True
        for inc in got:
            kid = inc["id"] or (inc["corridor"], inc["from"])
            if kid in seen:
                continue
            seen.add(kid)
            incidents.append(inc)
    rank = {"critical": 0, "major": 1, "minor": 2, "low": 3}
    incidents.sort(key=lambda x: rank.get(x.get("criticality") or "", 9))
    result = {
        "scraped_at": datetime.datetime.now(datetime.timezone.utc)
                          .isoformat(timespec="seconds"),
        "source": "HERE Traffic",
        "incidents": incidents[:40],
    }
    with open("putevi.json", "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f"Ukupno upisano: {len(result['incidents'])}")
    return 0


SELFTEST_RESPONSE = {
    "results": [
        {"incidentDetails": {"id": "h1", "type": "congestion",
                             "criticality": "major",
                             "description": {"value": "Stationary traffic on A1 near Vranje"}}},
        {"incidentDetails": {"id": "h2", "type": "construction",
                             "criticality": "low",
                             "description": {"value": "Roadworks between Nis and Merosina"}}},
        {"incidentDetails": {"id": "h3", "type": "congestion",
                             "criticality": "low",
                             "description": {"value": "Slow traffic"}}},
        {"incidentDetails": {"id": "h4", "type": "weather",
                             "criticality": "major",
                             "description": {"value": "Rain"}}},
    ]
}


def selftest():
    got = parse_incidents(SELFTEST_RESPONSE, "nis-presevo")
    ok = True
    # blag filter: prolaze zastoj/major, radovi/low, zastoj/low; weather ispada (nije u KEEP)
    if len(got) != 3:
        ok = False
    if not (got and got[0]["category"] == "zastoj" and got[0]["criticality"] == "major"):
        ok = False
    if any(g["category"] == "weather" for g in got):
        ok = False
    print(json.dumps(got, ensure_ascii=False, indent=2))
    print("SELFTEST:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(selftest())
    sys.exit(main())
