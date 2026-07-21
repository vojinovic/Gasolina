#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Gasolina - generise po jednu SEO landing stranicu za svaki granicni prelaz
(granica-<id>.html) iz borders-data.js.

Zasto ovako a ne 9 rucno pisanih fajlova: borders-data.js je jedinstveni
izvor istine za prelaze (isto pravilo kao za granice.html/index.html).
Ako se prelaz doda/izmeni tamo, ovaj skript se samo ponovo pokrene
(preko update-crossing-pages.yml, workflow_dispatch - ne treba terminal)
i sve stranice se osvezavaju iz istog izvora, bez rucnog kopiranja.

Landing stranice NAMERNO ne dupliraju ceo video/HLS plejer iz granice.html
(rizik za odrzavanje ako se plejer promeni na 9 mesta). Umesto toga:
staticna sliCica (thumbs/<id>.jpg, vec postoji) + broj trenutnog cekanja
(mali fetch granice.json) + jedinstven tekst za SEO vrednost + jasan CTA
ka granice.html#<id> gde vec postoji puni interaktivni prikaz.

Bez eksternih zavisnosti (samo stdlib), radi iz istog principa kao ostali
scraperi u repou.
"""

import re
import sys

SRC = "borders-data.js"
SITEMAP = "sitemap.xml"

FLAG = {
    "RS": "\U0001F1F7\U0001F1F8", "ME": "\U0001F1F2\U0001F1EA",
    "HR": "\U0001F1ED\U0001F1F7", "HU": "\U0001F1ED\U0001F1FA",
    "MK": "\U0001F1F2\U0001F1F0", "BA": "\U0001F1E7\U0001F1E6",
    "BG": "\U0001F1E7\U0001F1EC", "RO": "\U0001F1F7\U0001F1F4",
    "GR": "\U0001F1EC\U0001F1F7",
}
COUNTRY_SR = {
    "RS": "Srbija", "ME": "Crna Gora", "HR": "Hrvatska", "HU": "Ma\u0111arska",
    "MK": "Severna Makedonija", "BA": "Bosna i Hercegovina", "BG": "Bugarska",
    "RO": "Rumunija", "GR": "Gr\u010dka",
}


def parse_crossings(js_text):
    """Isti princip kao thumbs_scraper.py: deli tekst po 'id: \"...\"' granicama,
    pa iz svakog komada izvuce potrebna polja regex-om. Dovoljno pouzdano za
    nas fiksni, citljiv format borders-data.js."""
    ids = [(m.group(1), m.start()) for m in re.finditer(r'id:\s*"([a-z0-9-]+)"', js_text)]
    out = []
    for i, (cid, start) in enumerate(ids):
        end = ids[i + 1][1] if i + 1 < len(ids) else len(js_text)
        chunk = js_text[start:end]

        def field(name, default=None):
            m = re.search(rf'{name}:\s*"([^"]*)"', chunk)
            return m.group(1) if m else default

        has_camera = bool(re.search(r'src:\s*"[^"]+\.m3u8"', chunk))
        link_only = bool(re.search(r'linkOnly:\s*true', chunk))
        no_wait = bool(re.search(r'noWait:\s*true', chunk))
        cm = re.search(r'coords:\s*\[([\d.]+),\s*([\d.]+)\]', chunk)
        coords = (float(cm.group(1)), float(cm.group(2))) if cm else None

        out.append({
            "id": cid,
            "name": field("name", cid.title()),
            "from": field("from"),
            "to": field("to"),
            "pair": field("pair", ""),
            "road": field("road", ""),
            "provider": field("provider", ""),
            "official": field("official", "#"),
            "has_camera": has_camera,
            "link_only": link_only,
            "no_wait": no_wait,
            "coords": coords,
        })
    return out


def alt_crossings(all_c, this_c):
    """Drugi prelazi ka istoj zemlji (npr. Horgos i Kelebija oba ka HU) -
    za medjusobno linkovanje, isti princip kao renderComparisons u
    granice.html."""
    return [c for c in all_c if c["id"] != this_c["id"]
            and {c["from"], c["to"]} == {this_c["from"], this_c["to"]}]


def build_faq(c):
    naziv = c["name"]
    smer = f'{COUNTRY_SR.get(c["from"], c["from"])} \u2192 {COUNTRY_SR.get(c["to"], c["to"])}'
    items = [
        (f"Kolika je g\u0171\u017eva na prelazu {naziv} sada?",
         f'Na vrhu stranice prikazujemo trenutnu procenu \u010dekanja za oba smera, plus kameru u\u017eivo ako postoji. '
         f'Za detaljan prikaz sa svih izvora (grani\u010dna policija, susedna strana, prijave voza\u010da) idi na granice.html.'),
        (f"Gde vodi prelaz {naziv}?",
         f'{naziv} povezuje {smer}, naspram {c["pair"] or "susednog prelaza"} na putu {c["road"] or "-"}.'),
    ]
    alts = c.get("_alts") or []
    if alts:
        alt_names = ", ".join(a["name"] for a in alts)
        items.append((
            f"Postoji li alternativa prelazu {naziv}?",
            f'Da - {alt_names} vodi ka istoj zemlji. Kalkulator rute na Gasolini poredi oba prelaza kad planira\u0161 put, '
            f'a stranica granice.html direktno pokazuje koji je trenutno br\u017ei.'
        ))
    return items


PAGE_TMPL = """<!DOCTYPE html>
<html lang="sr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<meta name="description" content="{description}">
<link rel="canonical" href="https://gasolina.rs/granica-{id}.html">
<meta name="robots" content="index,follow">
<meta name="theme-color" content="#0d1620">

<meta property="og:type" content="website">
<meta property="og:site_name" content="Gasolina">
<meta property="og:locale" content="sr_RS">
<meta property="og:title" content="{title}">
<meta property="og:description" content="{description}">
<meta property="og:url" content="https://gasolina.rs/granica-{id}.html">
<meta property="og:image" content="https://gasolina.rs/{og_image}">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">

<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{title}">
<meta name="twitter:description" content="{description}">
<meta name="twitter:image" content="https://gasolina.rs/{og_image}">

<script type="application/ld+json">
{{
  "@context": "https://schema.org",
  "@type": "WebPage",
  "name": "{h1}",
  "url": "https://gasolina.rs/granica-{id}.html",
  "inLanguage": "sr-RS",
  "description": "{description}",
  "isPartOf": {{ "@type": "WebSite", "name": "Gasolina", "url": "https://gasolina.rs/" }}
}}
</script>
<script type="application/ld+json">
{{
  "@context": "https://schema.org",
  "@type": "BreadcrumbList",
  "itemListElement": [
    {{"@type":"ListItem","position":1,"name":"Gasolina","item":"https://gasolina.rs/"}},
    {{"@type":"ListItem","position":2,"name":"Granice","item":"https://gasolina.rs/granice.html"}},
    {{"@type":"ListItem","position":3,"name":"{name}","item":"https://gasolina.rs/granica-{id}.html"}}
  ]
}}
</script>
<script type="application/ld+json">
{{"@context":"https://schema.org","@type":"FAQPage","mainEntity":[{faq_json}]}}
</script>

<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Barlow+Condensed:wght@500;600;700&family=JetBrains+Mono:wght@500;700&display=swap" rel="stylesheet">

<!-- Google Analytics 4 -->
<script async src="https://www.googletagmanager.com/gtag/js?id=G-4EPLBJE8BL"></script>
<script>
  window.dataLayer = window.dataLayer || [];
  function gtag(){{dataLayer.push(arguments);}}
  gtag('js', new Date());
  gtag('config', 'G-4EPLBJE8BL');
  function track(name, params){{ try{{ gtag('event', name, params || {{}}); }}catch(e){{}} }}
</script>

<style>
  :root{{
    --ink:#0d1620; --panel:#15212e; --panel-2:#1b2a39; --line:#26384a;
    --text:#e9eff5; --dim:#8aa0b2; --faint:#5d7387;
    --fuel:#f5a623; --ok:#2fbf71; --warn:#f5a623; --bad:#e35d4f; --radius:14px;
  }}
  *{{box-sizing:border-box}}
  body{{margin:0;background:var(--ink);color:var(--text);font-family:"JetBrains Mono",monospace;line-height:1.5}}
  a{{color:inherit}}
  .topbar{{position:sticky;top:0;z-index:50;background:rgba(13,22,32,.85);backdrop-filter:blur(8px);border-bottom:1px solid var(--line)}}
  .topbar .inner{{max-width:1180px;margin:0 auto;padding:0 18px;height:58px;display:flex;align-items:center;justify-content:space-between;gap:16px}}
  .brand{{display:flex;align-items:center;gap:9px;text-decoration:none}}
  .brand .mark{{width:26px;height:26px;border-radius:7px;background:var(--fuel);display:grid;place-items:center;color:var(--ink);font-family:"Barlow Condensed",sans-serif;font-weight:700;font-size:18px}}
  .brand .bname{{font-family:"Barlow Condensed",sans-serif;font-weight:700;font-size:21px;letter-spacing:.04em;text-transform:uppercase;color:var(--text)}}
  .nav{{display:flex;align-items:center;gap:4px}}
  .nav a{{font-size:13px;color:var(--dim);text-decoration:none;padding:7px 11px;border-radius:8px;font-weight:500}}
  .nav a:hover{{color:var(--text);background:var(--panel)}}
  @media (max-width:560px){{
    .topbar .inner{{gap:8px}}
    .brand{{flex-shrink:0}}
    .nav{{overflow-x:auto;-webkit-overflow-scrolling:touch;scrollbar-width:none;min-width:0}}
    .nav::-webkit-scrollbar{{display:none}}
    .nav a{{padding:6px 10px;font-size:12px;white-space:nowrap;flex-shrink:0}}
    .brand .bname{{font-size:18px}}
  }}
  .wrap{{max-width:760px;margin:0 auto;padding:28px 18px 60px}}
  .crumb{{font-size:11px;color:var(--faint);letter-spacing:.06em;text-transform:uppercase;margin-bottom:10px}}
  .crumb a{{color:var(--faint);text-decoration:none}}
  .crumb a:hover{{color:var(--fuel)}}
  h1{{font-family:"Barlow Condensed",sans-serif;font-weight:700;font-size:36px;text-transform:uppercase;margin:0 0 12px;line-height:1.05}}
  .lead{{color:var(--dim);font-size:15px;line-height:1.65;margin:0 0 24px}}
  .hero{{position:relative;border-radius:var(--radius);overflow:hidden;border:1px solid var(--line);background:#070d13;aspect-ratio:16/9;display:block;text-decoration:none}}
  .hero img{{width:100%;height:100%;object-fit:cover;display:block}}
  .hero .play{{position:absolute;inset:0;display:flex;align-items:center;justify-content:center;gap:10px;background:linear-gradient(180deg,rgba(7,13,19,.15),rgba(7,13,19,.75));font-family:"Barlow Condensed",sans-serif;font-weight:700;text-transform:uppercase;font-size:16px;color:var(--text)}}
  .hero .play svg{{flex:none}}
  .no-cam{{border:1px dashed var(--line);border-radius:var(--radius);padding:24px;text-align:center;color:var(--dim);background:var(--panel)}}
  .wait-box{{display:grid;grid-template-columns:1fr 1fr;gap:1px;background:var(--line);margin-top:14px;border-radius:var(--radius);overflow:hidden}}
  .wcell{{background:var(--panel);padding:14px 16px}}
  .wlabel{{font-size:10px;letter-spacing:.1em;text-transform:uppercase;color:var(--faint)}}
  .wval{{font-family:"Barlow Condensed",sans-serif;font-weight:700;font-size:26px;margin-top:4px}}
  .cta{{display:flex;gap:10px;flex-wrap:wrap;margin-top:18px}}
  .btn{{font-family:"Barlow Condensed",sans-serif;font-weight:600;text-transform:uppercase;letter-spacing:.05em;font-size:14px;color:var(--ink);background:var(--fuel);border:none;border-radius:8px;padding:11px 18px;text-decoration:none;display:inline-flex;align-items:center;gap:7px}}
  .btn.ghost{{background:transparent;color:var(--text);border:1px solid var(--line)}}
  .info{{margin-top:28px;border-top:1px solid var(--line);padding-top:18px;font-size:13px;color:var(--dim);display:grid;gap:8px}}
  .info b{{color:var(--text)}}
  .faq{{margin:36px 0 10px}}
  .faq h2{{font-family:"Barlow Condensed",sans-serif;font-weight:700;font-size:22px;text-transform:uppercase;margin:0 0 14px}}
  .faq details{{border:1px solid var(--line);border-radius:11px;padding:2px 16px;margin-bottom:10px;background:var(--panel)}}
  .faq summary{{cursor:pointer;padding:13px 0;font-weight:600;font-size:14px;list-style:none;font-family:"JetBrains Mono",monospace}}
  .faq summary::-webkit-details-marker{{display:none}}
  .faq summary::before{{content:"+";color:var(--fuel);font-weight:700;margin-right:10px}}
  .faq details[open] summary::before{{content:"\\2212"}}
  .faq details p{{margin:0 0 15px;color:var(--dim);font-size:13.5px;line-height:1.6}}
  .others{{margin-top:30px;font-size:12px;color:var(--faint)}}
  .others a{{color:var(--fuel);text-decoration:none;margin-right:10px}}
</style>
</head>
<body>
<nav class="topbar">
  <div class="inner">
    <a class="brand" href="index.html">
      <span class="mark">G</span>
      <span class="bname">Gasolina</span>
    </a>
    <div class="nav">
      <a href="index.html">Cene goriva</a>
      <a href="index.html#kalkulator">Kalkulator</a>
      <a href="granice.html">Granice</a>
      <a href="istorija.html">Istorija</a>
    </div>
  </div>
</nav>

<div class="wrap">
  <div class="crumb"><a href="index.html">Gasolina</a> / <a href="granice.html">Granice</a> / {name}</div>
  <h1>{h1}</h1>
  <p class="lead">{intro}</p>

  {hero_block}

  <div class="cta">
    <a class="btn" href="granice.html#{id}" onclick="track('landing_cta', {{prelaz:'{id}', cilj:'granice'}})">Pogledaj sve detalje na granice.html \u2192</a>
    <a class="btn ghost" href="index.html#kalkulator" onclick="track('landing_cta', {{prelaz:'{id}', cilj:'kalkulator'}})">Izra\u010dunaj tro\u0161ak puta \u2192</a>
  </div>

  <div class="info">
    <div><b>Pravac:</b> {flag_from} {from_sr} \u2192 {flag_to} {to_sr}</div>
    <div><b>Put:</b> {road}</div>
    <div><b>Naspram:</b> {pair}</div>
    {alt_line}
  </div>

  <section class="faq">
    <h2>\u010cesta pitanja o prelazu {name}</h2>
    {faq_html}
  </section>

  <div class="others">Ostali grani\u010dni prelazi: {other_links}</div>
</div>

<script>
  const PRELAZ_ID = "{id}";
  const NO_WAIT = {no_wait_js};
  (async function(){{
    const box = document.getElementById("waitBox");
    if(!box) return;
    try{{
      const res = await fetch("granice.json?cb=" + Date.now());
      if(!res.ok) throw new Error("no data");
      const data = await res.json();
      const c = (data.crossings || {{}})[PRELAZ_ID];
      const fmt = m => (m == null) ? "nema podataka" : (m <= 30 ? "Bez guzve" : (m >= 60 ? Math.floor(m/60)+"h "+(m%60)+"m" : m + " min"));
      const p = (c && c.found && c.putnicka) ? c.putnicka : null;
      box.innerHTML = `
        <div class="wcell"><div class="wlabel">Ulaz u Srbiju</div><div class="wval">${{fmt(p ? p.ulaz : null)}}</div></div>
        <div class="wcell"><div class="wlabel">Izlaz iz Srbije</div><div class="wval">${{fmt(p ? p.izlaz : null)}}</div></div>`;
    }}catch(e){{
      box.innerHTML = `<div class="wcell" style="grid-column:1/-1;color:var(--faint)">Trenutno stanje nije dostupno - proveri direktno na <a href="granice.html#${{PRELAZ_ID}}" style="color:var(--fuel)">granice.html</a>.</div>`;
    }}
  }})();
</script>
</body>
</html>
"""


def render_page(c, all_c):
    c["_alts"] = alt_crossings(all_c, c)
    name = c["name"]
    from_sr = COUNTRY_SR.get(c["from"], c["from"])
    to_sr = COUNTRY_SR.get(c["to"], c["to"])
    title = f"{name} granica \u2014 kamera i \u010dekanje u\u017eivo | Gasolina"
    description = (f"Kamera u\u017eivo i procena \u010dekanja na prelazu {name} ({from_sr} \u2192 {to_sr}), "
                    f"put {c['road']}. Proveri gu\u017evu pre polaska.")
    h1 = f"{name} \u2014 kamera u\u017eivo i vreme \u010dekanja"

    intro_bits = [f"{name} povezuje {from_sr} i {to_sr}, na putu {c['road']}, naspram {c['pair'] or 'susednog prelaza'}."]
    if c["_alts"]:
        alt_names = " i ".join(a["name"] for a in c["_alts"])
        intro_bits.append(f"Alternativa ka istoj zemlji: {alt_names}.")
    intro_bits.append("Gasolina kombinuje graničnu policiju, kameru uživo i (gde postoji) susednu stranu radi realne procene.")
    intro = " ".join(intro_bits)

    if c["link_only"] or not c["has_camera"]:
        hero_block = (f'<div class="no-cam">Kamera za {name} nije dostupna direktno (zvanični izvor je van naše mreže). '
                       f'<a href="{c["official"]}" target="_blank" rel="noopener" style="color:var(--fuel)">Otvori zvaničnu kameru \u2197</a></div>')
    else:
        hero_block = (f'<a class="hero" href="granice.html#{c["id"]}" onclick="track(\'landing_hero_click\', {{prelaz:\'{c["id"]}\'}})">'
                       f'<img src="thumbs/{c["id"]}.jpg" alt="Kamera {name}" loading="lazy" onerror="this.style.display=\'none\'">'
                       f'<span class="play">\u25b6 Pusti kameru u\u017eivo</span></a>')
    if not c["no_wait"]:
        hero_block += '<div class="wait-box" id="waitBox"><div class="wcell" style="grid-column:1/-1;color:var(--faint)">U\u010ditavanje trenutnog stanja\u2026</div></div>'

    # Guzva na mapi (Waze embed): besplatan zvanicni iframe, bez API kljuca i
    # bez kartice - namerno NE Google Maps traffic layer koji trazi placeni
    # nalog. loading="lazy" da ne usporava ucitavanje stranice.
    if c.get("coords"):
        lat, lon = c["coords"]
        hero_block += (
            f'<div class="map-box"><h2 style="font-family:\'Barlow Condensed\',sans-serif;font-size:20px;'
            f'text-transform:uppercase;margin:26px 0 10px">Gu\u017eva na mapi</h2>'
            f'<iframe src="https://embed.waze.com/iframe?zoom=14&lat={lat}&lon={lon}&pin=1" '
            f'width="100%" height="320" style="border:1px solid var(--line);border-radius:12px" '
            f'loading="lazy" title="Gu\u017eva oko prelaza {name} (Waze)" allowfullscreen></iframe>'
            f'<div style="font-size:11px;color:var(--faint);margin-top:6px">Izvor: Waze live mapa \u2014 boje i prijave gu\u017eve od samih voza\u010da.</div></div>'
        )

    alt_line = ""
    if c["_alts"]:
        links = ", ".join(f'<a href="granica-{a["id"]}.html" style="color:var(--fuel)">{a["name"]}</a>' for a in c["_alts"])
        alt_line = f'<div><b>Alternativa:</b> {links}</div>'

    faq_items = build_faq(c)
    faq_json = ",".join(
        '{{"@type":"Question","name":"{}","acceptedAnswer":{{"@type":"Answer","text":"{}"}}}}'.format(
            q.replace('"', '\\"'), a.replace('"', '\\"'))
        for q, a in faq_items
    )
    faq_html = "\n    ".join(
        f'<details><summary>{q}</summary><p>{a}</p></details>' for q, a in faq_items
    )

    other_links = " ".join(
        f'<a href="granica-{o["id"]}.html">{o["name"]}</a>' for o in all_c if o["id"] != c["id"]
    )

    og_image = f'thumbs/{c["id"]}.jpg' if c["has_camera"] else "og.png"

    return PAGE_TMPL.format(
        title=title, description=description, id=c["id"], name=name, h1=h1, intro=intro,
        hero_block=hero_block, flag_from=FLAG.get(c["from"], ""), flag_to=FLAG.get(c["to"], ""),
        from_sr=from_sr, to_sr=to_sr, road=c["road"] or "-", pair=c["pair"] or "-",
        alt_line=alt_line, faq_html=faq_html, faq_json=faq_json,
        other_links=other_links, og_image=og_image,
        no_wait_js=("true" if c["no_wait"] else "false"),
    )


def main():
    with open(SRC, encoding="utf-8") as f:
        js_text = f.read()
    crossings = parse_crossings(js_text)
    if not crossings:
        print("Nijedan prelaz nije parsiran iz borders-data.js - proveri format.")
        return 1

    for c in crossings:
        html = render_page(c, crossings)
        out_path = f"granica-{c['id']}.html"
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(html)
        print(f"Napisano: {out_path}")

    print(f"Gotovo: {len(crossings)} landing stranica generisano.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
