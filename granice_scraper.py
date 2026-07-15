#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Gasolina - scraper vremena cekanja na granicnim prelazima.

Izvor podataka: AMSS mapa stanja na putu, koja preuzima zvanicne podatke
Uprave granicne policije RS. Brojke o cekanju su cinjenice (nisu autorski
sadrzaj), pa se smeju koristiti uz navodjenje izvora.

Bez eksternih zavisnosti (samo standardna biblioteka), pa radi na GitHub
Actions bez `pip install`. Pristojan interval: na svakih 30-60 min je sasvim
dovoljno, jer AMSS i sam azurira retko.

Izlaz: granice.json u rootu repoa.
"""

import re
import sys
import json
import html
import datetime
import urllib.request

URL = "https://www.amss.org.rs/stanje-na-putu/strana/mapa"
HU_URL = ("https://www.police.hu/hu/hirek-es-informaciok/hatarinfo"
          "?field_hat_rszakasz_value=szerb+hat%C3%A1rszakasz")
MK_URL = "https://amsm.mk/sostojba-na-patishta/dnevni-informacii/"

# --- BorderAlarm (prijave vozaca, crowdsource) -----------------------------
# PRIVREMENO za Gradinu dok ne postoji zvanicni izvor sa minutima.
# Iskljucuje se jednim flagom. Podatak se prikazuje uz atribuciju i link.
BA_ENABLED = True
BA_URL = "https://borderalarm.com/countries/serbia/"
BA_TARGETS = {
    "gradina":  r"dragina\s*/\s*kalotina",   # njihov (pogresan) naziv za Gradinu
    "presevo":  r"presevo\s*/\s*tabanovce",
    "horgos":   r"horgos\s*/\s*roszke",
    "kelebija": r"kelebija\s*/\s*tompa",
    "batrovci": r"batrovci\s*/\s*bajakovo",
}
OUT = "granice.json"

# id prelaza (mora da se poklapa sa CAMERAS u granice.html) -> kljucna rec
# u AMSS naslovu (folovano, bez kvacica, velikim slovima)
TARGETS = {
    "gradina":      "GRADINA",
    "horgos":       "HORGOS",
    "kelebija":     "KELEBIJA",
    "batrovci":     "BATROVCI",
    "presevo":      "PRESEVO",
    "sremska-raca": "SREMSKA RACA",
    "spiljani":     "SPILJANI",
    "gostun":       "GOSTUN",
}

# id prelaza -> folovani naziv madjarske strane na police.hu (Szerb szakasz).
# "ki" (Magyarorszag felol) = ulaz u Srbiju; "be" (Magyarorszag fele) = izlaz iz Srbije.
HU_TARGETS = {
    "horgos": "horgos autopalya",
    "kelebija": "tompa - kelebia",
}

# id prelaza -> naziv GP na makedonskoj strani (AMSM dnevne informacije, kirilica).
# AMSM navodi broj samo kad ima guzve; inace "nema podolgi zadrzuvanja" -> 0.
# Smerovi: "vlez" = ulaz u MK, "izlez" = izlaz iz MK.
MK_TARGETS = {
    "presevo":    "табановце",
    "bogorodica": "богородица",
}


def fold(s):
    """Skida srpske i madjarske akcente radi poredjenja naziva."""
    s = (s.replace("Š", "S").replace("š", "s")
          .replace("Đ", "Dj").replace("đ", "dj")
          .replace("Č", "C").replace("č", "c")
          .replace("Ć", "C").replace("ć", "c")
          .replace("Ž", "Z").replace("ž", "z"))
    # madjarski samoglasnici
    for a, b in (("á","a"),("é","e"),("í","i"),("ó","o"),("ö","o"),("ő","o"),
                 ("ú","u"),("ü","u"),("ű","u"),
                 ("Á","A"),("É","E"),("Í","I"),("Ó","O"),("Ö","O"),("Ő","O"),
                 ("Ú","U"),("Ü","U"),("Ű","U")):
        s = s.replace(a, b)
    return s


def html_to_text(raw):
    """Grubo cisti HTML u tekst po linijama, bez bs4."""
    raw = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", raw)
    raw = re.sub(r"(?i)<br\s*/?>", "\n", raw)
    raw = re.sub(r"(?i)</(p|div|h[1-6]|li|tr)>", "\n", raw)
    raw = re.sub(r"<[^>]+>", " ", raw)
    raw = html.unescape(raw)
    raw = raw.replace("\xa0", " ")
    lines = [re.sub(r"[ \t]+", " ", ln).strip() for ln in raw.splitlines()]
    return "\n".join(ln for ln in lines if ln)


def heading_name(line):
    """Ako je linija naslov granicnog prelaza, vraca naziv, inace None."""
    l = line.strip().lstrip("#").strip().lstrip("*").strip()
    m = re.match(r"^\d*\s*GP\s+([A-ZČĆŽŠĐ]\S*)(.*)$", l)
    if not m:
        return None
    return (m.group(1) + m.group(2)).strip()


def split_blocks(text):
    """Deli tekst na blokove po graničnom prelazu (do prvog 'Izvor')."""
    blocks = {}
    cur = None
    collecting = False
    for raw in text.splitlines():
        name = heading_name(raw)
        if name:
            cur = name
            blocks[cur] = []
            collecting = True
            continue
        if cur and collecting:
            blocks[cur].append(raw)
            if re.search(r"izvor", raw, re.I):
                collecting = False
    return {name: "\n".join(lines) for name, lines in blocks.items()}


def grab(segment, key):
    """Iz segmenta izvlaci minute za 'Izlaz iz Srbije' ili 'Ulaz u Srbiju'.
    Razume 'oko/od/do/preko N min', 'N sata/casa', 'jedan sat', 'pola sata'."""
    m = re.search(key, segment, re.I)
    if m is None:
        return None
    rest = segment[m.end():]
    stop = len(rest)
    for pat in (r"(?i)ulaz u srbiju", r"(?i)izlaz iz srbije", r"\n"):
        mm = re.search(pat, rest)
        if mm:
            stop = min(stop, mm.start())
    win = fold(rest[:stop]).lower()[:90]
    mmin = re.search(r"(\d+)\s*min", win)
    if mmin:
        return int(mmin.group(1))
    mh = re.search(r"(\d+)\s*(?:sata|sati|sat|casa|casova|cas|h\b)", win)
    if mh:
        return int(mh.group(1)) * 60
    for w, v in (("pola sata", 30), ("jedan sat", 60), ("sat vremena", 60),
                 ("dva sata", 120), ("tri sata", 180), ("cetiri sata", 240),
                 ("pet sati", 300)):
        if w in win:
            return v
    return None


def parse_block(text):
    """Vraca {'putnicka': {...}, 'teretna': {...} | None}."""
    upper = fold(text).upper()
    ti = upper.find("TERETN")
    if ti != -1:
        putn, ter = text[:ti], text[ti:]
        return {
            "putnicka": {"izlaz": grab(putn, r"Izlaz iz Srbije"),
                         "ulaz":  grab(putn, r"Ulaz u Srbiju")},
            "teretna":  {"izlaz": grab(ter, r"Izlaz iz Srbije"),
                         "ulaz":  grab(ter, r"Ulaz u Srbiju")},
        }
    return {
        "putnicka": {"izlaz": grab(text, r"Izlaz iz Srbije"),
                     "ulaz":  grab(text, r"Ulaz u Srbiju")},
        "teretna": None,
    }


def match_target(blocks, keyword):
    """Nadji blok ciji folovani naziv sadrzi kljucnu rec."""
    for name, body in blocks.items():
        fname = fold(name).upper()
        if keyword == "HORGOS" and "HORGOS II" in fname:
            continue
        if keyword in fname:
            return name, body
    return None, None


def hu_value(segment):
    """Tekst posle oznake smera -> minuti (0 = nema cekanja > 15 min).
    Ocekuje folovan (bez akcenata) tekst."""
    seg = segment.lower()
    if "nincs 15 percet" in seg:
        return 0
    h = re.search(r"(\d+)\s*ora", seg)    # ora = sat
    p = re.search(r"(\d+)\s*perc", seg)   # perc = minut
    mins = (int(h.group(1)) * 60 if h else 0) + (int(p.group(1)) if p else 0)
    return mins if mins else None


def parse_hu(text):
    """Vraca {id: {'ulaz':min, 'izlaz':min}} sa police.hu."""
    folded = fold(text).lower()
    res = {}
    for cid, name in HU_TARGETS.items():
        i = folded.find(name.lower())
        if i == -1:
            continue
        ki = folded.find("felol (ki)", i)
        be = folded.find("fele (be)", i)
        if ki == -1 or be == -1:
            continue
        forg = folded.find("forgalom", be)
        ki_seg = folded[ki:be]
        be_seg = folded[be:(forg if forg != -1 else be + 200)]
        res[cid] = {"ulaz": hu_value(ki_seg), "izlaz": hu_value(be_seg)}
    return res


def mk_minutes(segment):
    """Makedonski tekst -> minuti. 'polovina cas'=30, 'eden cas'=60, 'N casa'=N*60."""
    seg = segment.lower()
    m = re.search(r"(\d+)\s*минут", seg)
    if m:
        return int(m.group(1))
    if "половина час" in seg:
        return 30
    if "еден час" in seg:
        return 60
    h = re.search(r"(\d+)\s*час", seg)
    if h:
        return int(h.group(1)) * 60
    return None


def parse_mk(text):
    """Vraca {id: {'vlez':m,'izlez':m,'opsto':m}} sa AMSM dnevnih informacija.
    Trazi naziv prelaza po celom tekstu; minuti se citaju u ISTOJ recenici,
    i to POSLE imena (da 'Blace 20 min, a Tabanovce 30 min' ne pomesa brojke).
    Ako prelaz nije pomenut a stoji 'nema podolgi zadrzuvanja' -> sve 0.
    Ako nema ni pomena ni te fraze -> prelaz se preskace (posteno 'ne znamo')."""
    low = text.lower()
    if "фреквенција" not in low and "гранични премини" not in low:
        print("MK: stranica ne lici na AMSM dnevne informacije")
        return {}
    no_delay = ("нема подолги задржувања" in low)
    res = {}
    for cid, name in MK_TARGETS.items():
        i = low.find(name)
        if i == -1:
            if no_delay:
                res[cid] = {"vlez": 0, "izlez": 0, "opsto": 0}
                print(f"MK: {cid} ({name}) nije pomenut -> bez zadrzavanja")
            else:
                print(f"MK: {cid} ({name}) nije nadjen, preskacem")
            continue
        s_start = low.rfind(".", 0, i) + 1
        s_end = low.find(".", i)
        if s_end == -1:
            s_end = min(i + 300, len(low))
        after_name = low[i:s_end]          # od imena do kraja recenice
        sentence = low[s_start:s_end]      # cela recenica (za smer ispred imena)
        mins = mk_minutes(after_name)
        entry = {"vlez": None, "izlez": None, "opsto": None}
        if mins is not None:
            if "за влез" in sentence:
                entry["vlez"] = mins
            elif "за излез" in sentence:
                entry["izlez"] = mins
            else:
                entry["opsto"] = mins
            print(f"MK: {cid} -> {entry}")
        else:
            print(f"MK: {cid} pomenut ali bez minuta u recenici: '{sentence[:120]}'")
        res[cid] = entry
    return res


def fetch_mk():
    req = urllib.request.Request(MK_URL, headers={
        "User-Agent": "Gasolina/1.0 (+https://vojinovic.github.io/Gasolina)"
    })
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode("utf-8", "replace")


def parse_ba(text):
    """Vraca {id: {'izlaz':m,'ulaz':m}} sa BorderAlarm liste za Srbiju.
    Format po prelazu: ime, pa prvi 'N min.' = Srbija->X (izlaz),
    drugi 'N min.' = X->Srbija (ulaz)."""
    low = fold(text).lower()
    res = {}
    for cid, name in BA_TARGETS.items():
        mm = re.search(name, low)
        if mm is None:
            print(f"BA: {cid} ({name}) nije nadjen")
            continue
        i = mm.end()
        nxt = low.find(" open", i + 10)
        window = low[i:(nxt if nxt != -1 else i + 400)]
        mins = re.findall(r"(\d+)\s*min", window)
        if len(mins) >= 2:
            res[cid] = {"izlaz": int(mins[0]), "ulaz": int(mins[1])}
            print(f"BA: {cid} -> {res[cid]}")
        else:
            print(f"BA: {cid} nadjen ali bez dva vremena u prozoru")
    return res


def fetch_ba():
    req = urllib.request.Request(BA_URL, headers={
        "User-Agent": "Gasolina/1.0 (+https://vojinovic.github.io/Gasolina)"
    })
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode("utf-8", "replace")


def fetch_hu():
    req = urllib.request.Request(HU_URL, headers={
        "User-Agent": "Gasolina/1.0 (+https://vojinovic.github.io/Gasolina)"
    })
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode("utf-8", "replace")


def build(text, hu_text=None, mk_text=None, ba_text=None):
    blocks = split_blocks(text)
    hu = parse_hu(hu_text) if hu_text else {}
    mk = parse_mk(mk_text) if mk_text else {}
    ba = parse_ba(ba_text) if ba_text else {}
    crossings = {}
    for cid, kw in TARGETS.items():
        name, body = match_target(blocks, kw)
        if body is None:
            entry = {"found": False}
        else:
            entry = parse_block(body)
            entry["found"] = True
            entry["amss_name"] = name
        if cid in hu:
            entry["hu"] = hu[cid]
        if cid in mk:
            entry["mk"] = mk[cid]
        if cid in ba:
            entry["ba"] = ba[cid]
        crossings[cid] = entry
    # bogorodica nije na AMSS mapi (MK-GR granica), ali MK podatak treba da udje
    if "bogorodica" in mk and "bogorodica" not in crossings:
        crossings["bogorodica"] = {"found": False, "mk": mk["bogorodica"]}
    return {
        "scraped_at": datetime.datetime.now(datetime.timezone.utc)
                          .isoformat(timespec="seconds"),
        "source": "AMSS / Uprava granicne policije RS",
        "source_hu": "Magyar Rendorseg (police.hu) - madjarska strana",
        "source_mk": "AMSM (amsm.mk) - makedonska strana",
        "source_ba": "BorderAlarm (borderalarm.com) - prijave vozaca",
        "crossings": crossings,
    }


def fetch():
    req = urllib.request.Request(URL, headers={
        "User-Agent": "Gasolina/1.0 (+https://vojinovic.github.io/Gasolina)"
    })
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode("utf-8", "replace")


# --------------------------------------------------------------------------
SELFTEST_FIXTURE = """
#### 1GP BATROVCI sa Hrvatske strane GP BAJAKOVO Lipovac, na AP E70
Prema poslednjim informacijama zadrzavanja na nasim granicnim prelazima su:
Na PUTNICKIM terminalima:
1. Izlaz iz Srbije - oko 30 minuta.
2. Ulaz u Srbiju - oko 30 minuta.
Na TERETNIM terminalima:
1. Izlaz iz Srbije - oko 300 min.
2. Ulaz u Srbiju - oko 30 min.
Izvor: Uprava granicne policije RS

#### 1GP HORGOS SRBIJA MADJARSKA AP A1, E-75
Prema poslednjim informacijama zadrzavanja na nasim granicnim prelazima su:
Na PUTNICKIM terminalima:
1. Izlaz iz Srbije - oko 30 minuta.
2. Ulaz u Srbiju - oko 30 minuta.
Na TERETNIM terminalima:
1. Izlaz iz Srbije - oko 30 min.
2. Ulaz u Srbiju - oko 30 min.
Izvor: Uprava granicne policije RS

#### 1GP PRESEVO Srbija - Severna Makedonija AP E 75 M1
Prema poslednjim informacijama Uprave granicne policije RS, zadrzavanja su:
Na PUTNICKIM terminalima:
1. Izlaz iz Srbije - oko 30 min.
2. Ulaz u Srbiju - oko 30 min.
Na TERETNIM terminalima
1. Izlaz iz Srbije - oko 30 min.
2. Ulaz u Srbiju - oko 30 min.
Izvor: Uprava granicne policije RS

#### 1GP SREMSKA RACA
Prema poslednjim informacijama Uprave granicne policije RS, zadrzavanja su:
Na PUTNICKIM terminalima:
1. Izlaz iz Srbije - oko 30 min.
2. Ulaz u Srbiju - od 30 min.
Na TERETNIM terminalima:
1. Izlaz iz Srbije - oko 240 minuta.
2. Ulaz u Srbiju - oko 30 minuta.
Izvor: Uprava granicne policije RS

#### 1GP Horgos II (Srbija-Madjarska)
Prema poslednjim informacijama zadrzavanja putnickih vozila:
1. Izlaz iz Srbije- oko 30 minuta.
2. Ulaz u Srbiju- oko 30 minuta.
Izvor: Uprava granicne policije RS

#### 1GP SPILJANI Srbija Crna Gora E65 E80
Prema poslednjim informacijama Uprave granicne policije RS, zadrzavanja su:
Na PUTNICKIM terminalima:
1. Izlaz iz Srbije: oko 30 minuta
2. Ulaz u Srbiju: oko 30 minuta
Na TERETNIM terminalima:
1. Izlaz iz Srbije- oko 30 min.
2. Ulaz u Srbiju- oko 30 min.
Izvor: Uprava granicne policije RS

#### 1GP GOSTUN Srbija Crna Gora
Prema poslednjim informacijama Uprave granicne policije RS, zadrzavanja su:
Na PUTNICKIM terminalima:
1. Izlaz iz Srbije: oko 30 minuta.
2. Ulaz u Srbiju: oko 30 minuta
Na TERETNIM terminalima:
1. Izlaz iz Srbije- oko 30 min.
2. Ulaz u Srbiju- oko 30 min.
Izvor: Uprava granicne policije RS

#### 1GP GRADINA (Dimitrovgrad Srbija Bugarska AP E80)
Prema poslednjim informacijama Uprave granicne policije RS, zadrzavanja su:
Na PUTNICKIM terminalima:
1. Izlaz iz Srbije - od 60 minuta.
2. Ulaz u Srbiju - oko 30 min.
Na TERETNIM terminalima:
1. Izlaz iz Srbije - jedan sat.
2. Ulaz u Srbiju - oko 30 min.
Izvor: Uprava granicne policije RS

#### 1GP KELEBIJA Srbija Madjarska
Prema poslednjim informacijama Uprave granicne policije RS, zadrzavanja su:
Na PUTNICKIM terminalima:
1. Izlaz iz Srbije - oko 45 min.
2. Ulaz u Srbiju - oko 30 min.
Na TERETNIM terminalima:
1. Izlaz iz Srbije- oko 30 min.
2. Ulaz u Srbiju- oko 30 min.
Izvor: Uprava granicne policije RS

#### Petlja Vranje, radovi
Zabrana za teretna vozila preko 10 t. Izvor: Putevi Srbije
"""
HU_FIXTURE = """
Hatarszakasz: Szerb hatarszakasz

##### Roszke - Horgos kozut- 00.00-24.00
Varakozasi ido Magyarorszag felol (ki):
Nincs 15 percet meghalado varakozas
---
Varakozasi ido Magyarorszag fele (be):
Nincs 15 percet meghalado varakozas
---
Forgalom tipusa: nemzetkozi szemelyforgalom

##### Roszke - Horgos autopalya- 00:00-24:00
Varakozasi ido Magyarorszag felol (ki):
Nincs 15 percet meghalado varakozas
---
Varakozasi ido Magyarorszag fele (be):
2 ora 30 perc
---
Forgalom tipusa: nemzetkozi szemely- es teherforgalom (tranzit)

##### Tompa - Kelebia- 00:00-24:00
Varakozasi ido Magyarorszag felol (ki):
Nincs 15 percet meghalado varakozas
---
Varakozasi ido Magyarorszag fele (be):
180 perc
---
Forgalom tipusa: nemzetkozi szemely- es teherforgalom
"""


MK_FIXTURE = """
Состојба на патишта
Дневни информации
СОСТОЈБА: Сообраќајот на државните патишта се одвива непречено, по суви коловози.
ФРЕКВЕНЦИЈА: Интензитетот на сообраќај на патните правци надвор од градските средини е зголемен.
Се бележи зголемена фреквенција на возила на ГП Блаце, времето на чекање е 20 минути,
а на ГП Табановце времето на чекање е 30 минути.
Поради зголемена фреквенција на возила, на ГП Богородица времето на чекање за излез
од државата е околу половина час.
На останатите гранични премини од македонска страна, нема подолги задржувања за влез и излез од државата.
ВНИМАТЕЛНО: АМСМ препорачува прилагодена брзина на движење.
"""


BA_FIXTURE = """
BG
Dragina / Kalotina Open
55 min.
Serbia \u2794
Bulgaria
5 min.
Bulgaria \u2794
Serbia
MK
Presevo / Tabanovce Open
15 min.
Serbia \u2794
North Macedonia
10 min.
North Macedonia \u2794
Serbia
"""


def selftest():
    result = build(SELFTEST_FIXTURE, HU_FIXTURE, MK_FIXTURE, BA_FIXTURE)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    c = result["crossings"]
    ok = True
    def check(cid, p_out, p_in, t_out, t_in):
        nonlocal ok
        x = c[cid]
        got = (x["putnicka"]["izlaz"], x["putnicka"]["ulaz"],
               (x["teretna"] or {}).get("izlaz"), (x["teretna"] or {}).get("ulaz"))
        exp = (p_out, p_in, t_out, t_in)
        flag = "OK " if got == exp else "FAIL"
        if got != exp:
            ok = False
        print(f"[{flag}] {cid}: got={got} exp={exp}")
    check("batrovci", 30, 30, 300, 30)
    check("gradina", 60, 30, 60, 30)
    check("kelebija", 45, 30, 30, 30)
    check("horgos", 30, 30, 30, 30)
    check("presevo", 30, 30, 30, 30)
    check("sremska-raca", 30, 30, 240, 30)
    check("spiljani", 30, 30, 30, 30)
    check("gostun", 30, 30, 30, 30)
    # HU strana: ki=ulaz, be=izlaz
    hu = c["horgos"].get("hu")
    hu_exp = {"ulaz": 0, "izlaz": 150}
    hu_ok = hu == hu_exp
    if not hu_ok:
        ok = False
    print(f"[{'OK ' if hu_ok else 'FAIL'}] horgos.hu: got={hu} exp={hu_exp}")
    hu_k = c["kelebija"].get("hu")
    hu_k_exp = {"ulaz": 0, "izlaz": 180}
    hu_k_ok = hu_k == hu_k_exp
    if not hu_k_ok:
        ok = False
    print(f"[{'OK ' if hu_k_ok else 'FAIL'}] kelebija.hu: got={hu_k} exp={hu_k_exp}")
    # MK strana: Tabanovce bez smera -> opsto 30; Bogorodica "za izlez ... polovina cas" -> izlez 30
    mk_p = c["presevo"].get("mk")
    mk_p_exp = {"vlez": None, "izlez": None, "opsto": 30}
    mk_b = c["bogorodica"].get("mk")
    mk_b_exp = {"vlez": None, "izlez": 30, "opsto": None}
    for label, got, exp in (("presevo.mk", mk_p, mk_p_exp), ("bogorodica.mk", mk_b, mk_b_exp)):
        good = got == exp
        if not good:
            ok = False
        print(f"[{'OK ' if good else 'FAIL'}] {label}: got={got} exp={exp}")
    ba_g = c["gradina"].get("ba")
    ba_exp = {"izlaz": 55, "ulaz": 5}
    ba_ok = ba_g == ba_exp
    if not ba_ok:
        ok = False
    print(f"[{'OK ' if ba_ok else 'FAIL'}] gradina.ba: got={ba_g} exp={ba_exp}")
    ba_p = c["presevo"].get("ba")
    ba_p_exp = {"izlaz": 15, "ulaz": 10}
    ba_p_ok = ba_p == ba_p_exp
    if not ba_p_ok:
        ok = False
    print(f"[{'OK ' if ba_p_ok else 'FAIL'}] presevo.ba: got={ba_p} exp={ba_p_exp}")
    print("\nSELFTEST:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


HIST = "istorija.csv"


def append_history(result):
    """Dopise jedan red po prelazu/smeru u istorija.csv (kombinovani najgori podatak).
    Format: ts,prelaz,smer,minuti,izvor
    Jedan red je par bajtova; 48 upisa dnevno x 9 prelaza x 2 smera = mali fajl."""
    import csv
    import os

    ts = result["scraped_at"]
    rows = []
    for cid, c in result["crossings"].items():
        for smer in ("ulaz", "izlaz"):
            best, src_name = None, None
            # AMSS (putnicka)
            p = (c.get("putnicka") or {}).get(smer)
            if p is not None:
                best, src_name = p, "amss"
            # madjarska strana
            hu = c.get("hu")
            if hu and hu.get(smer) is not None and hu[smer] > 0:
                if best is None or hu[smer] > best:
                    best, src_name = hu[smer], "hu"
            # makedonska strana (vlez = izlaz iz Srbije)
            mk = c.get("mk")
            if mk:
                v = mk.get("vlez") if smer == "izlaz" else mk.get("izlez")
                for cand in (v, mk.get("opsto")):
                    if cand is not None and cand > 0 and (best is None or cand > best):
                        best, src_name = cand, "mk"
            # prijave vozaca
            ba = c.get("ba")
            if ba and ba.get(smer) is not None and ba[smer] > 0:
                if best is None or ba[smer] > best:
                    best, src_name = ba[smer], "ba"
            if best is not None:
                rows.append([ts, cid, smer, best, src_name])

    if not rows:
        print("Istorija: nema sta da se upise.")
        return

    new_file = not os.path.exists(HIST)
    with open(HIST, "a", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        if new_file:
            w.writerow(["ts", "prelaz", "smer", "minuti", "izvor"])
        w.writerows(rows)
    print(f"Istorija: dopisano {len(rows)} redova u {HIST}")


def main():
    if "--selftest" in sys.argv:
        return selftest()
    text = html_to_text(fetch())
    try:
        hu_text = html_to_text(fetch_hu())
    except Exception as e:
        print("Upozorenje: police.hu nije dostupan:", e)
        hu_text = None
    try:
        mk_text = html_to_text(fetch_mk())
    except Exception as e:
        print("Upozorenje: amsm.mk nije dostupan:", e)
        mk_text = None
    ba_text = None
    if BA_ENABLED:
        try:
            ba_text = html_to_text(fetch_ba())
        except Exception as e:
            print("Upozorenje: borderalarm.com nije dostupan:", e)
    result = build(text, hu_text, mk_text, ba_text)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    append_history(result)
    found = sum(1 for v in result["crossings"].values() if v.get("found"))
    print(f"Upisano {OUT}: {found}/{len(TARGETS)} prelaza, {result['scraped_at']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
