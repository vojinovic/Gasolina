# -*- coding: utf-8 -*-
"""CI provere za gasolina.rs — isti ritual kao rucna validacija pre isporuke:
  1. node --check za svaki inline <script> u svakom .html (i za samostalne .js fajlove)
  2. json.loads za svaki <script type="application/ld+json"> blok (JSON-LD)
  3. json.loads za sve .json fajlove u korenu repoa

Bez mreze, bez zavisnosti van stdlib-a + node na PATH-u.
Pokretanje:  python3 ci_checks.py          (ili --selftest za test samog parsera)
Izlaz: 0 ako je sve OK, 1 ako bilo sta padne (sa listom problema).
"""
import json
import os
import re
import subprocess
import sys
import tempfile

# <script ...>...</script> — hvata i atribute, non-greedy telo, case-insensitive
SCRIPT_RE = re.compile(
    r"<script\b([^>]*)>(.*?)</script\s*>",
    re.IGNORECASE | re.DOTALL,
)
SRC_RE = re.compile(r"\bsrc\s*=", re.IGNORECASE)
TYPE_RE = re.compile(r"""\btype\s*=\s*["']?([^"'\s>]+)""", re.IGNORECASE)

JS_TYPES = {"", "text/javascript", "application/javascript", "module"}


def _line_of(text, pos):
    return text.count("\n", 0, pos) + 1


def check_node(code, label, problems):
    """node --check nad JS kodom (pise se u temp fajl)."""
    with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False, encoding="utf-8") as f:
        f.write(code)
        tmp = f.name
    try:
        r = subprocess.run(["node", "--check", tmp], capture_output=True, text=True)
        if r.returncode != 0:
            msg = (r.stderr or r.stdout).strip().replace(tmp, label)
            problems.append(f"{label}: node --check PAO:\n{msg}")
            return False
        return True
    finally:
        os.remove(tmp)


def check_html(path, problems):
    with open(path, encoding="utf-8") as f:
        text = f.read()
    n_js = n_ld = 0
    for m in SCRIPT_RE.finditer(text):
        attrs, body = m.group(1), m.group(2)
        if SRC_RE.search(attrs):
            continue  # spoljni skript (cdnjs itd.) — ne proverava se
        tm = TYPE_RE.search(attrs)
        stype = (tm.group(1).lower() if tm else "")
        line = _line_of(text, m.start())
        label = f"{path} (script na liniji {line})"
        if stype == "application/ld+json":
            n_ld += 1
            try:
                json.loads(body)
            except Exception as e:
                problems.append(f"{label}: JSON-LD nevazeci: {e}")
        elif stype in JS_TYPES:
            if body.strip():
                n_js += 1
                check_node(body, label, problems)
        # ostali tipovi (npr. text/template) se preskacu
    return n_js, n_ld


def iter_files(root="."):
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if not d.startswith(".") and d != "node_modules"]
        for fn in sorted(filenames):
            yield os.path.join(dirpath, fn)


def main():
    problems = []
    tot_html = tot_js = tot_ld = tot_json = tot_jsfile = 0
    for path in iter_files():
        low = path.lower()
        if low.endswith(".html"):
            tot_html += 1
            js, ld = check_html(path, problems)
            tot_js += js
            tot_ld += ld
        elif low.endswith(".js"):
            tot_jsfile += 1
            with open(path, encoding="utf-8") as f:
                check_node(f.read(), path, problems)
        elif low.endswith(".json"):
            tot_json += 1
            try:
                with open(path, encoding="utf-8") as f:
                    json.load(f)
            except Exception as e:
                problems.append(f"{path}: nevazeci JSON: {e}")
    print(f"Provereno: {tot_html} HTML ({tot_js} inline JS blokova, {tot_ld} JSON-LD), "
          f"{tot_jsfile} .js, {tot_json} .json")
    if problems:
        print(f"\nCI CHECKS PALO ({len(problems)}):")
        for p in problems:
            print("-" * 60)
            print(p)
        return 1
    print("CI checks OK.")
    return 0


def selftest():
    """Test samog parsera na sintetickom HTML-u — bez repoa."""
    html = (
        '<script src="https://cdnjs.example/hls.js"></script>'
        '<script type="application/ld+json">{"@type":"Place"}</script>'
        "<script>\nvar x = 1;\n</script>"
        '<SCRIPT type="text/javascript">function f(){return 2}</SCRIPT>'
    )
    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, "t.html")
        with open(p, "w", encoding="utf-8") as f:
            f.write(html)
        problems = []
        js, ld = check_html(p, problems)
        ok = (js == 2 and ld == 1 and not problems)
        # i negativan slucaj — pokvaren JS i pokvaren JSON-LD moraju da PADNU
        with open(p, "w", encoding="utf-8") as f:
            f.write('<script>var x = ;</script>'
                    '<script type="application/ld+json">{pokvaren}</script>')
        problems2 = []
        check_html(p, problems2)
        ok = ok and len(problems2) == 2
    print("SELFTEST:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(selftest() if "--selftest" in sys.argv else main())
