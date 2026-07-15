#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Gasolina - hvata staticne thumbnail slike sa graniсnih kamera (ffmpeg).

Cita feeds[0].src direktno iz borders-data.js (jedinstveni izvor istine,
isto kao sto ga koristi frontend) - nema duplirane liste URL-ova na dva
mesta. Za svaki prelaz koji ima pravu kameru (nije linkOnly/noCamera),
ffmpeg izvuce JEDAN kadar iz m3u8 strima i sacuva ga kao thumbs/<id>.jpg.

Zasto ffmpeg a ne browser (kao stari previewFeed u granice.html):
  - MUP kamere (port 4443) su CORS-blokirane u browseru na svemu sem
    Safarija -> u browseru ostaju bez pregleda. ffmpeg nije browser,
    CORS ga se ne tice, pa ovo napokon daje sliku i za njih.
  - Radi identicno za sve uredjaje (mobilni, desktop), jer je izlaz
    obicna .jpg slika, ne live HLS koji se pusta pa zamrzava.

Fallback: ako hvatanje za neki prelaz padne (mreza, kamera privremeno
mrtva), STARA slika u thumbs/ ostaje netaknuta - kartica nikad ne ostane
bez ičega zbog jednog promasenog ciklusa.

Bez eksternih Python zavisnosti (samo stdlib + sistemski ffmpeg binarni
fajl, koji workflow instalira preko apt).
"""

import os
import re
import sys
import shutil
import subprocess

JS_FILE = "borders-data.js"
THUMBS_DIR = "thumbs"
FFMPEG_TIMEOUT = 25  # sekundi po kameri; spor/mrtav strim ne sme da zaglavi ceo posao

# Prelazi za koje se OCEKUJE prava kamera (feeds[0]) - koristi ga selftest
# da uhvati tihi kvar parsera ako neko izmeni strukturu borders-data.js.
# Ako dodas novi prelaz sa kamerom, dodaj ga i ovde.
EXPECTED_IDS = {
    "gradina", "horgos", "kelebija", "batrovci",
    "presevo", "bogorodica", "sremska-raca", "spiljani",
}


def parse_crossings(js_text):
    """Vrati [(id, feeds[0].src), ...] za sve prelaze koji imaju kameru.
    Ne parsira JS kao JS (nema zavisnosti) - deli tekst na komade po
    'id: "..."' granicama, pa u svakom komadu trazi prvi src i noCamera/
    linkOnly flagove. Dovoljno pouzdano za nas fiksni, citljiv format."""
    ids = [(m.group(1), m.start()) for m in re.finditer(r'id:\s*"([a-z0-9-]+)"', js_text)]
    out = []
    for i, (cid, start) in enumerate(ids):
        end = ids[i + 1][1] if i + 1 < len(ids) else len(js_text)
        chunk = js_text[start:end]
        if re.search(r'noCamera:\s*true', chunk) or re.search(r'linkOnly:\s*true', chunk):
            continue
        m = re.search(r'src:\s*"([^"]+\.m3u8)"', chunk)
        if not m:
            continue
        out.append((cid, m.group(1)))
    return out


def capture_thumb(url, out_path):
    tmp_path = out_path + ".tmp"
    cmd = [
        "ffmpeg", "-y",
        "-user_agent", "Mozilla/5.0 (Gasolina thumbs bot)",
        "-i", url,
        "-frames:v", "1",
        "-q:v", "4",
        "-vf", "scale=480:-2",
        tmp_path,
    ]
    try:
        r = subprocess.run(cmd, capture_output=True, timeout=FFMPEG_TIMEOUT)
    except subprocess.TimeoutExpired:
        print(f"  [FAIL] timeout posle {FFMPEG_TIMEOUT}s")
        return False
    if r.returncode != 0 or not os.path.exists(tmp_path) or os.path.getsize(tmp_path) < 500:
        err = r.stderr.decode(errors="replace").strip().splitlines()
        print(f"  [FAIL] ffmpeg exit {r.returncode}: {err[-1] if err else '(nema stderr)'}")
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
        return False
    os.replace(tmp_path, out_path)  # atomicno - stara slika se menja tek kad je nova sigurno gotova
    return True


def selftest():
    problems = []
    if shutil.which("ffmpeg") is None:
        problems.append("ffmpeg nije na PATH-u (u workflow-u: apt-get install ffmpeg)")
    if not os.path.exists(JS_FILE):
        problems.append(f"{JS_FILE} ne postoji u ovom direktorijumu")
    else:
        with open(JS_FILE, encoding="utf-8") as f:
            crossings = parse_crossings(f.read())
        found = {c for c, _ in crossings}
        print(f"Parser nasao {len(crossings)} prelaza sa kamerom: {sorted(found)}")
        missing = EXPECTED_IDS - found
        extra = found - EXPECTED_IDS
        if missing:
            problems.append(f"Ocekivani prelazi NISU nadjeni (parser ili JS pokvaren?): {sorted(missing)}")
        if extra:
            print(f"(info) Novi prelazi otkriveni van EXPECTED_IDS - ako je namerno, dodaj ih u listu: {sorted(extra)}")
    if problems:
        print("SELFTEST PALO:")
        for p in problems:
            print(" -", p)
        return 1
    print("Selftest OK.")
    return 0


def main():
    if "--selftest" in sys.argv:
        return selftest()

    if shutil.which("ffmpeg") is None:
        print("ffmpeg nije instaliran. U Actions workflow-u: apt-get install -y ffmpeg")
        return 1
    if not os.path.exists(JS_FILE):
        print(f"{JS_FILE} nije nadjen - pokreni skriptu iz root-a repoa.")
        return 1

    with open(JS_FILE, encoding="utf-8") as f:
        crossings = parse_crossings(f.read())
    if not crossings:
        print("Nijedan prelaz sa kamerom nije parsiran iz borders-data.js - proveri format fajla.")
        return 1

    os.makedirs(THUMBS_DIR, exist_ok=True)
    ok = fail = 0
    for cid, url in crossings:
        out_path = os.path.join(THUMBS_DIR, f"{cid}.jpg")
        print(f"{cid}: {url}")
        if capture_thumb(url, out_path):
            print("  [OK]")
            ok += 1
        else:
            fail += 1
            if os.path.exists(out_path):
                print("  zadrzana prethodna slika (fallback)")
            else:
                print("  NEMA ni stare ni nove slike - kartica ostaje bez thumb-a dok se ne uhvati jedna")

    print(f"Gotovo: {ok}/{len(crossings)} novih slika, {fail} palo (fallback gde postoji stara).")
    return 0 if fail < len(crossings) else 1  # crveno u Actions samo ako je SVE palo


if __name__ == "__main__":
    sys.exit(main())
