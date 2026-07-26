# -*- coding: utf-8 -*-
"""Skida komentare iz objavljenih HTML/JS fajlova.

Zasto: komentari u klijentskim fajlovima objasnjavaju ZASTO je nesto tako
uradjeno - koja koordinata je kalibrisana i kako, zasto se AMSS-ovih 30 ne
uzima zdravo za gotovo, kako se bira najgori izvor. To je znanje projekta,
a browser ga svakome prikazuje kroz Ctrl+U. Kod ostaje citljiv u repou i u
CLAUDE.md; objavljena verzija ide bez objasnjenja.

NE dira: <pre>, <code>, JSON-LD, uslovne komentare, ni bilo sta van komentara.
NE menja formatiranje, prelome ni razmake - samo brise komentar-blokove.

Pokretanje:
  python3 strip_comments.py --check    # samo prijavi koliko bi skinuo (CI)
  python3 strip_comments.py            # stvarno skine, na mestu
  python3 strip_comments.py --selftest # bez fajlova, testira parser
"""
import glob
import os
import re
import sys

# HTML komentari koje NE diramo: uslovni (IE) i oni koji pocinju sa "!"
# (konvencija za "ostavi ovo" - npr. licencni zaglavlja)
HTML_KEEP = re.compile(r"<!--\s*(\[if|!)", re.I)


def strip_html_comments(text):
    out, i, n = [], 0, 0
    while True:
        j = text.find("<!--", i)
        if j == -1:
            out.append(text[i:])
            break
        k = text.find("-->", j)
        if k == -1:
            out.append(text[i:])
            break
        blok = text[j:k + 3]
        if HTML_KEEP.match(blok):
            out.append(text[i:k + 3])
        else:
            out.append(text[i:j])
            n += 1
        i = k + 3
    return "".join(out), n


def _mask_regions(text):
    """Vraca listu (start, end) opsega u kojima se komentari NE diraju:
    <pre>, <code>, <textarea>, <script type="application/ld+json">."""
    regije = []
    for pat in (r"<pre\b.*?</pre\s*>", r"<code\b.*?</code\s*>",
                r"<textarea\b.*?</textarea\s*>",
                r'<script[^>]*type\s*=\s*["\']application/ld\+json["\'].*?</script\s*>'):
        for m in re.finditer(pat, text, re.I | re.S):
            regije.append((m.start(), m.end()))
    return regije


def _in_region(pos, regije):
    return any(a <= pos < b for a, b in regije)


def strip_js_comments(code, offset=0, regije=()):
    """Skida // i /* */ iz JS-a, postujuci stringove, sablone i regex literale.
    Naivni pristup (samo regex) bi pojeo URL-ove tipa https://... i sadrzaj
    stringova - zato ide karakter po karakter kroz stanja.
    """
    out = []
    i, n = 0, len(code)
    broj = 0
    while i < n:
        c = code[i]
        # stringovi i sabloni
        if c in "\"'`":
            kraj = c
            out.append(c)
            i += 1
            while i < n:
                if code[i] == "\\":
                    out.append(code[i:i + 2])
                    i += 2
                    continue
                out.append(code[i])
                if code[i] == kraj:
                    i += 1
                    break
                i += 1
            continue
        # linijski komentar
        if c == "/" and i + 1 < n and code[i + 1] == "/":
            if _in_region(offset + i, regije):
                out.append(c)
                i += 1
                continue
            j = code.find("\n", i)
            j = n if j == -1 else j
            # sacuvaj prelom reda da se brojevi linija ne pomere previse
            i = j
            broj += 1
            continue
        # blok komentar
        if c == "/" and i + 1 < n and code[i + 1] == "*":
            if _in_region(offset + i, regije):
                out.append(c)
                i += 1
                continue
            j = code.find("*/", i + 2)
            i = n if j == -1 else j + 2
            broj += 1
            continue
        out.append(c)
        i += 1
    return "".join(out), broj


def process_html(text):
    regije = _mask_regions(text)
    text, n_html = strip_html_comments(text)
    regije = _mask_regions(text)   # pozicije su se pomerile
    out, i, n_js = [], 0, 0
    for m in re.finditer(r"(<script\b[^>]*>)(.*?)(</script\s*>)", text, re.I | re.S):
        atrs, telo, kraj = m.group(1), m.group(2), m.group(3)
        out.append(text[i:m.start()])
        if re.search(r'type\s*=\s*["\'](?!text/javascript|application/javascript|module)', atrs, re.I):
            out.append(m.group(0))   # JSON-LD i slicno - ne diramo
        else:
            ocisceno, k = strip_js_comments(telo, m.start(2), regije)
            n_js += k
            out.append(atrs + ocisceno + kraj)
        i = m.end()
    out.append(text[i:])
    return "".join(out), n_html, n_js


def main(check_only):
    ukupno_h = ukupno_j = 0
    izmenjeni = []
    for path in sorted(glob.glob("*.html") + glob.glob("en/*.html") + glob.glob("*.js")):
        with open(path, encoding="utf-8") as f:
            orig = f.read()
        if path.endswith(".js"):
            novo, k = strip_js_comments(orig)
            h = 0
            j = k
        else:
            novo, h, j = process_html(orig)
        if novo != orig:
            ukupno_h += h
            ukupno_j += j
            izmenjeni.append((path, h, j, len(orig) - len(novo)))
            if not check_only:
                with open(path, "w", encoding="utf-8") as f:
                    f.write(novo)
    for path, h, j, ust in izmenjeni:
        print(f"  {path:34} HTML:{h:3}  JS:{j:3}  -{ust} B")
    print(f"{'Naslo' if check_only else 'Skinuto'}: {ukupno_h} HTML + {ukupno_j} JS komentara "
          f"u {len(izmenjeni)} fajlova")
    return 0


def selftest():
    ok = True

    def proveri(naziv, dobio, ocekivano):
        nonlocal ok
        dobro = dobio == ocekivano
        if not dobro:
            ok = False
        print(f"[{'OK ' if dobro else 'FAIL'}] {naziv}: {dobio!r}")

    # URL u stringu ne sme da se pojede
    kod = 'const u = "https://kamere.amss.org.rs/x.m3u8"; // objasnjenje\nlet a=1;'
    proveri("URL u stringu", strip_js_comments(kod)[0].strip(),
            'const u = "https://kamere.amss.org.rs/x.m3u8"; \nlet a=1;')

    # sablon sa // unutra
    kod2 = 'const t = `pre//posle`; /* blok */ let b=2;'
    proveri("template literal", strip_js_comments(kod2)[0], 'const t = `pre//posle`;  let b=2;')

    # apostrof u stringu
    kod3 = "const s = 'it\\'s // ne komentar'; // jeste komentar\n"
    proveri("escaped navodnik", strip_js_comments(kod3)[0].strip(),
            "const s = 'it\\'s // ne komentar';")

    # JSON-LD ostaje netaknut
    html = ('<script type="application/ld+json">{"@type":"X","u":"http://a//b"}</script>'
            '<script>var x=1; // skini me\n</script><!-- skini -->'
            '<!--[if IE]>ostani<![endif]-->')
    novo, h, j = process_html(html)
    proveri("JSON-LD netaknut", '"u":"http://a//b"' in novo, True)
    proveri("uslovni komentar ostaje", "[if IE]" in novo, True)
    proveri("HTML komentar skinut", "<!-- skini -->" not in novo, True)
    proveri("JS komentar skinut", "skini me" not in novo, True)

    # <pre> blok se ne dira
    html2 = "<pre><script>var y=1; // primer u dokumentaciji\n</script></pre>"
    proveri("pre blok netaknut", "primer u dokumentaciji" in process_html(html2)[0], True)

    print("SELFTEST:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(selftest())
    sys.exit(main("--check" in sys.argv))
