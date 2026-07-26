#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Gasolina - generise landing stranice granicnih prelaza iz borders-data.js,
na DVA jezika:
  sr: granica-<id>.html          (postojeci URL-ovi, ne diraju se - SEO)
  en: en/border-<id>.html        (nova engleska verzija, hreflang povezano)

Novo u ovoj verziji (zahtev: thumb klik -> posvecena stranica sa SVIM):
- PRAVI hls.js plejer na samoj stranici (isti CDN kao granice.html), sa
  dugmicima za vise kamera (Ulaz/Izlaz) i ?play=1 auto-pustanjem - vise se
  ne salje korisnik nazad na granice.html da bi gledao kameru.
- Dvojezicni izlaz iz istog sablona: svaki tekst zivi u L recniku, prevod
  se odrzava na jednom mestu. hreflang tagovi povezuju parove stranica.
- EN wait-box prevodi srpske statuse iz granice.json ("Bez guzve" itd) na
  engleski na frontendu - granice.json ostaje kakav jeste.
linkOnly prelazi (MUP CG: gostun, debeli-brijeg): thumb + zvanicni link,
bez plejera (HTTP izvor se ne moze embedovati na HTTPS sajtu).
"""

import json
import os
import re
import sys
import urllib.parse

SRC = "borders-data.js"

FLAG = {
    "RS": "\U0001F1F7\U0001F1F8", "ME": "\U0001F1F2\U0001F1EA",
    "HR": "\U0001F1ED\U0001F1F7", "HU": "\U0001F1ED\U0001F1FA",
    "MK": "\U0001F1F2\U0001F1F0", "BA": "\U0001F1E7\U0001F1E6",
    "BG": "\U0001F1E7\U0001F1EC", "RO": "\U0001F1F7\U0001F1F4",
    "GR": "\U0001F1EC\U0001F1F7",
}
COUNTRY = {
    "sr": {"RS": "Srbija", "ME": "Crna Gora", "HR": "Hrvatska", "HU": "Ma\u0111arska",
           "MK": "Severna Makedonija", "BA": "Bosna i Hercegovina", "BG": "Bugarska",
           "RO": "Rumunija", "GR": "Gr\u010dka"},
    "en": {"RS": "Serbia", "ME": "Montenegro", "HR": "Croatia", "HU": "Hungary",
           "MK": "North Macedonia", "BA": "Bosnia and Herzegovina", "BG": "Bulgaria",
           "RO": "Romania", "GR": "Greece"},
}

# Svi UI tekstovi na jednom mestu - prevod se odrzava OVDE, ne po sablonu.
L = {
  "sr": {
    "lang_attr": "sr", "og_locale": "sr_RS", "in_language": "sr-RS",
    "title": "{name} u\u017eivo: kamera i vreme \u010dekanja | Gasolina",
    "description": "Grani\u010dni prelaz {name} ({from_c} \u2192 {to_c}): kamera u\u017eivo, trenutno vreme \u010dekanja za oba smera i gu\u017eva na mapi. Bez naloga, besplatno.",
    "h1": "{name} \u2014 kamera u\u017eivo i vreme \u010dekanja",
    "intro": "{name} povezuje {from_c} i {to_c}, na putu {road}, naspram {pair}. Gasolina kombinuje grani\u010dnu policiju, kameru u\u017eivo i (gde postoji) susednu stranu radi realne procene.",
    "nav_prices": "Cene goriva", "nav_calc": "Kalkulator", "nav_borders": "Granice", "nav_history": "Istorija", "nav_guides": "Vodi\u010di",
    "crumb_borders": "Granice",
    "play": "Pusti kameru u\u017eivo",
    "cam_official_note": "Kamera se otvara na zvani\u010dnom izvoru.",
    "cam_official_btn": "Otvori kameru",
    "snap_note": "Poslednja slika \u00b7 klik za zvani\u010dnu kameru \u2197",
    "no_cam": "Za ovaj prelaz jo\u0161 nema javno dostupne kamere.",
    "wait_in": "Ulaz u Srbiju", "wait_out": "Izlaz iz Srbije",
    "wait_loading": "U\u010ditavanje trenutnog stanja\u2026",
    "wait_unavail": 'Trenutno stanje nije dostupno - proveri direktno na <a href="{root}granice.html#{id}" style="color:var(--fuel)">granice.html</a>.',
    "no_queue": "Bez guzve", "no_data": "nema podataka",
    "src_amss_only": "jedini izvor: AMSS (podrazumevana vrednost)",
    "map_h": "Gu\u017eva na mapi: {a} \u2192 {b}",
    "src_ba": "Prijave voza\u010da (BorderAlarm)", "src_hu": "Ma\u0111arska strana", "src_mk": "Makedonska strana",
    "src_tt": "Mapa saobra\u0107aja", "tt_note": "bez paso\u0161ke kontrole", "tt_kolona": "kolona",
    "lbl_out": "izlaz", "lbl_in": "ulaz", "src_label": "izvor",
    "share_label": "Podeli:", "share_copy": "Kopiraj", "share_copied": "Kopirano!",
    "share_out": "izlaz iz Srbije", "share_in": "ulaz u Srbiju", "share_noq": "bez guzve", "share_nd": "nema podataka",
    "share_nowait": "kamera dostupna, cekanje se ne prati",
    "map_note": "Vreme na mapi je procena vo\u017enje kroz zonu prelaza u trenutnoj gu\u017evi \u2014 ne uklju\u010duje paso\u0161ku kontrolu.",
    "cta_borders": "Uporedi sve prelaze \u2192",
    "cta_calc": "Izra\u010dunaj tro\u0161ak puta \u2192",
    "dir": "Pravac", "road_l": "Put", "pair_l": "Naspram",
    "alt_l": "Alternativa", "alt_txt": "{alts} vodi ka istoj zemlji",
    "faq_h": "\u010cesta pitanja o prelazu {name}",
    "others": "Ostali grani\u010dni prelazi:",
    "switch_label": "EN", "switch_title": "Read in English",
    "faq1_q": "Kolika je gu\u017eva na prelazu {name} sada?",
    "faq1_a": "Na vrhu stranice su kamera u\u017eivo i trenutna procena \u010dekanja za oba smera, plus gu\u017eva na mapi. Za pore\u0111enje svih prelaza idi na stranicu Granice.",
    "faq2_q": "Gde vodi prelaz {name}?",
    "faq2_a": "{name} povezuje {smer}, naspram {pair} na putu {road}.",
    "faq3_q": "Postoji li alternativa prelazu {name}?",
    "faq3_a": "Da - {alts} vodi ka istoj zemlji. Kalkulator rute na Gasolini poredi prelaze kad planira\u0161 put, a stranica Granice direktno pokazuje koji je trenutno br\u017ei.",
  },
  "en": {
    "lang_attr": "en", "og_locale": "en_US", "in_language": "en",
    "title": "{name} border crossing live: camera and waiting time | Gasolina",
    "description": "{name} border crossing ({from_c} \u2192 {to_c}): live camera, current waiting time in both directions and traffic on the map. Free, no account needed.",
    "h1": "{name} \u2014 live camera and waiting time",
    "intro": "{name} connects {from_c} and {to_c} on route {road}, opposite {pair}. Gasolina combines border police data, a live camera and (where available) the neighbouring side for a realistic estimate.",
    "nav_prices": "Fuel prices", "nav_calc": "Trip calculator", "nav_borders": "Borders", "nav_history": "History", "nav_guides": "Guides",
    "crumb_borders": "Borders",
    "play": "Play live camera",
    "cam_official_note": "The camera opens on the official source.",
    "cam_official_btn": "Open camera",
    "snap_note": "Latest snapshot \u00b7 click for the official camera \u2197",
    "no_cam": "No publicly available camera for this crossing yet.",
    "wait_in": "Entering Serbia", "wait_out": "Exiting Serbia",
    "wait_loading": "Loading current status\u2026",
    "wait_unavail": 'Current status unavailable - check directly on <a href="{root}granice.html#{id}" style="color:var(--fuel)">the borders page</a>.',
    "no_queue": "No queue", "no_data": "no data",
    "src_amss_only": "only source: AMSS (default value)",
    "map_h": "Traffic on the map: {a} \u2192 {b}",
    "src_ba": "Driver reports (BorderAlarm)", "src_hu": "Hungarian side", "src_mk": "North Macedonian side",
    "src_tt": "Traffic map", "tt_note": "excludes passport control", "tt_kolona": "queue",
    "lbl_out": "exit", "lbl_in": "entry", "src_label": "source",
    "share_label": "Share:", "share_copy": "Copy", "share_copied": "Copied!",
    "share_out": "exiting Serbia", "share_in": "entering Serbia", "share_noq": "no queue", "share_nd": "no data",
    "share_nowait": "camera available, waiting not tracked",
    "map_note": "The time on the map is a driving estimate through the crossing zone in current traffic \u2014 it does not include passport control.",
    "cta_borders": "Compare all crossings \u2192",
    "cta_calc": "Calculate trip cost \u2192",
    "dir": "Direction", "road_l": "Route", "pair_l": "Opposite",
    "alt_l": "Alternative", "alt_txt": "{alts} leads to the same country",
    "faq_h": "Frequently asked questions about {name}",
    "others": "Other border crossings:",
    "switch_label": "SR", "switch_title": "\u010citaj na srpskom",
    "faq1_q": "How long is the wait at {name} right now?",
    "faq1_a": "The live camera and the current waiting estimate for both directions are at the top of this page, plus traffic on the map. To compare all crossings, open the Borders page.",
    "faq2_q": "Where does the {name} crossing lead?",
    "faq2_a": "{name} connects {smer}, opposite {pair} on route {road}.",
    "faq3_q": "Is there an alternative to {name}?",
    "faq3_a": "Yes - {alts} leads to the same country. Gasolina's route calculator compares crossings when you plan a trip, and the Borders page shows which one is currently faster.",
  },
}


def parse_crossings(js_text):
    out = []
    for m in re.finditer(r'\{\s*(?:\/\/[^\n]*\n\s*)*id:\s*"([a-z-]+)"(.*?)\n    \}', js_text, re.S):
        cid, chunk = m.group(1), m.group(2)

        def field(name, default=None):
            fm = re.search(rf'{name}:\s*"([^"]*)"', chunk)
            return fm.group(1) if fm else default

        feeds = []
        for fm in re.finditer(r'\{\s*label:\s*"([^"]+)",\s*dir:\s*"[^"]*",\s*src:\s*"([^"]+\.m3u8)"\s*\}', chunk):
            feeds.append({"label": fm.group(1), "src": fm.group(2)})

        link_only = bool(re.search(r'linkOnly:\s*true', chunk))
        no_wait = bool(re.search(r'noWait:\s*true', chunk))
        pm = re.search(r'mapPB:\s*\[([\d.]+),\s*([\d.]+),\s*([\d.]+),\s*([\d.]+)\]', chunk)
        map_pb = tuple(float(x) for x in pm.groups()) if pm else None
        pim = re.search(r'mapPBin:\s*\[([\d.]+),\s*([\d.]+),\s*([\d.]+),\s*([\d.]+)\]', chunk)
        map_pb_in = tuple(float(x) for x in pim.groups()) if pim else None
        # Opcioni uvodni tekst po prelazu. Podrazumevani govori o "kameri uzivo",
        # sto za prelaze bez kamere nije tacno - "posten prikaz je brend".
        im = re.search(r'intro:\s*"([^"]+)"', chunk)
        intro_sr = im.group(1) if im else None
        ime = re.search(r'introEn:\s*"([^"]+)"', chunk)
        intro_en = ime.group(1) if ime else None
        rm = re.search(r'mapRoute:\s*\["([^"]+)",\s*"([^"]+)"\]', chunk)
        map_route = (rm.group(1), rm.group(2)) if rm else None
        # Opcioni Google place ID-jevi za pb mapu (preuzeti VERBATIM sa
        # alltrafficcams embed-a, nikad izmisljeni). Bez njih Google reverse-
        # geokodira tacku na najblizi POI - kod bogorodice je to bila spedicija
        # "Blue Bell Customs Broker" umesto same granicne stanice.
        # Format: pbId: ["0x...%3A0x...", "0x...%3A0x..."] (A = nasa strana, B = susedna)
        idm = re.search(r'pbId:\s*\["([^"]*)",\s*"([^"]*)"\]', chunk)
        pb_id = (idm.group(1) or None, idm.group(2) or None) if idm else None
        # Ulazna mapa moze da ima DRUGI par ID-jeva: mapPB i mapPBin pokazuju na
        # razlicite tacke (jednosmerne trake), pa se i place ID kaci gde odgovara.
        # Prazan string = bez ID-ja (koristi se gola koordinata).
        idim = re.search(r'pbIdIn:\s*\["([^"]*)",\s*"([^"]*)"\]', chunk)
        pb_id_in = (idim.group(1) or None, idim.group(2) or None) if idim else None

        out.append({
            "id": cid,
            "name": field("name", cid.title()),
            "from": field("from"), "to": field("to"),
            "pair": field("pair", ""), "road": field("road", ""),
            "provider": field("provider", ""), "official": field("official", "#"),
            "feeds": feeds, "link_only": link_only, "no_wait": no_wait,
            "map_pb": map_pb, "map_pb_in": map_pb_in, "map_route": map_route,
            "pb_id": pb_id, "pb_id_in": pb_id_in,
            "intro_sr": intro_sr, "intro_en": intro_en,
        })
    return out


def alt_crossings(all_c, this_c):
    return [c for c in all_c if c["id"] != this_c["id"]
            and {c["from"], c["to"]} == {this_c["from"], this_c["to"]}]


def page_href(cid, lang, from_lang):
    """Relativna putanja do stranice prelaza cid na jeziku lang, gledano
    SA stranice na jeziku from_lang."""
    if lang == "sr":
        return ("../" if from_lang == "en" else "") + f"granica-{cid}.html"
    return ("" if from_lang == "en" else "en/") + f"border-{cid}.html"


PAGE_TMPL = """<!DOCTYPE html>
<html lang="{lang_attr}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<meta name="description" content="{description}">
<link rel="canonical" href="https://gasolina.rs/{self_path}">
<link rel="alternate" hreflang="sr" href="https://gasolina.rs/granica-{id}.html">
<link rel="alternate" hreflang="en" href="https://gasolina.rs/en/border-{id}.html">
<link rel="alternate" hreflang="x-default" href="https://gasolina.rs/granica-{id}.html">
<meta name="robots" content="index,follow">
<meta name="theme-color" content="#0d1620">

<meta property="og:type" content="website">
<meta property="og:site_name" content="Gasolina">
<meta property="og:locale" content="{og_locale}">
<meta property="og:title" content="{title}">
<meta property="og:description" content="{description}">
<meta property="og:url" content="https://gasolina.rs/{self_path}">
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
  "name": "{title}",
  "url": "https://gasolina.rs/{self_path}",
  "inLanguage": "{in_language}",
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
    {{"@type":"ListItem","position":2,"name":"{crumb_borders}","item":"https://gasolina.rs/granice.html"}},
    {{"@type":"ListItem","position":3,"name":"{name}","item":"https://gasolina.rs/{self_path}"}}
  ]
}}
</script>
<script type="application/ld+json">
{{"@context":"https://schema.org","@type":"FAQPage","mainEntity":[{faq_json}]}}
</script>

<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Barlow+Condensed:wght@500;600;700&family=JetBrains+Mono:wght@500;700&display=swap" rel="stylesheet">
<!-- hls.js se ucitava tek na prvi klik na kameru (ensureHls) - stedi ~150 KB na svakom otvaranju stranice -->

<script>
  // pre renderovanja: ako je autoplay zatrazen, sakrij "pusti" overlay odmah
  // (inace blesne na ~100ms dok video ne krene)
  if (new URLSearchParams(location.search).get("play") === "1") {{
    document.documentElement.classList.add("autoplay");
  }}
</script>
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
  .nav a.lang{{border:1px solid var(--line);font-weight:700}}
  @media (max-width:560px){{
    .topbar .inner{{gap:8px}}
    .brand{{flex-shrink:0}}
    .nav{{overflow-x:auto;-webkit-overflow-scrolling:touch;scrollbar-width:none;min-width:0}}
    .nav::-webkit-scrollbar{{display:none}}
    .nav a{{padding:6px 10px;font-size:12px;white-space:nowrap;flex-shrink:0}}
    .brand .bname{{font-size:18px}}
  }}
  .wrap{{max-width:1000px;margin:0 auto;padding:28px 18px 60px}}
  .crumb{{font-size:11px;color:var(--faint);letter-spacing:.06em;text-transform:uppercase;margin-bottom:10px}}
  .crumb a{{color:var(--faint);text-decoration:none}}
  .crumb a:hover{{color:var(--fuel)}}
  h1{{font-family:"Barlow Condensed",sans-serif;font-weight:700;font-size:36px;text-transform:uppercase;margin:0;line-height:1.05}}
  .h1row{{display:flex;align-items:center;justify-content:space-between;gap:14px;flex-wrap:wrap;margin:0 0 16px}}
  .dirchip{{font-family:"Barlow Condensed",sans-serif;font-weight:600;font-size:19px;letter-spacing:.04em;border:1px solid var(--line);border-radius:10px;padding:8px 16px;white-space:nowrap;background:var(--panel)}}
  .lead{{color:var(--dim);font-size:14px;line-height:1.65;margin:26px 0 0}}
  .pane{{position:relative;border-radius:var(--radius);overflow:hidden;border:1px solid var(--line);background:#070d13;aspect-ratio:16/9}}
  .pane img.thumb{{position:absolute;inset:0;width:100%;height:100%;object-fit:cover;display:block}}
  .pane video{{position:absolute;inset:0;width:100%;height:100%;object-fit:cover;display:none;background:#000}}
  .autoplay .pane .overlay{{display:none}}
  .pane .overlay{{position:absolute;inset:0;display:flex;align-items:center;justify-content:center;gap:10px;background:linear-gradient(180deg,rgba(7,13,19,.15),rgba(7,13,19,.75));font-family:"Barlow Condensed",sans-serif;font-weight:700;text-transform:uppercase;font-size:16px;color:var(--text);cursor:pointer;border:none;width:100%}}
  .pane .badge{{position:absolute;top:10px;left:10px;z-index:3;font-size:10px;letter-spacing:.06em;background:rgba(7,13,19,.75);color:var(--dim);padding:4px 9px;border-radius:7px}}
  .pane .live{{position:absolute;top:10px;right:10px;z-index:3;display:none;font-size:10px;letter-spacing:.08em;background:rgba(227,93,79,.9);color:#fff;padding:4px 9px;border-radius:7px;font-weight:700}}
  .thumb-link{{position:absolute;inset:0;z-index:1;display:block}}
  .snap-note{{position:absolute;left:10px;bottom:10px;z-index:2;font-size:10.5px;letter-spacing:.04em;background:rgba(7,13,19,.75);color:var(--dim);padding:4px 9px;border-radius:7px}}
  .feeds{{display:flex;gap:10px;margin-top:12px;flex-wrap:wrap}}
  .feeds button{{font-family:"Barlow Condensed",sans-serif;font-weight:600;text-transform:uppercase;letter-spacing:.05em;font-size:15px;background:var(--panel);color:var(--dim);border:1px solid var(--line);border-radius:10px;padding:12px 26px;cursor:pointer;flex:1;min-width:120px;max-width:220px;transition:all .15s ease}}
  .feeds button:hover{{color:var(--text);border-color:var(--faint)}}
  .feeds button.on{{background:var(--fuel);color:var(--ink);font-weight:700;border-color:var(--fuel)}}
  .no-cam{{border:1px dashed var(--line);border-radius:var(--radius);padding:24px;text-align:center;color:var(--dim);background:var(--panel)}}
  .wait-box{{display:grid;grid-template-columns:1fr 1fr;gap:1px;background:var(--line);margin-top:14px;border-radius:var(--radius);overflow:hidden}}
  .wcell{{background:var(--panel);padding:14px 16px}}
  .wlabel{{font-size:10px;letter-spacing:.1em;text-transform:uppercase;color:var(--faint)}}
  .wval{{font-family:"Barlow Condensed",sans-serif;font-weight:700;font-size:26px;margin-top:4px}}
  .map-box iframe{{display:block}}
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
  .share-row{{display:flex;align-items:center;gap:6px;margin-top:14px;flex-wrap:wrap}}
  .share-label{{font-size:11px;color:var(--faint)}}
  .share-btn{{font-family:"JetBrains Mono",monospace;font-size:12.5px;background:var(--panel);color:var(--dim);border:1px solid var(--line);border-radius:8px;padding:11px 15px;cursor:pointer}}
  .share-btn:hover{{color:var(--text);border-color:var(--fuel)}}
  .others{{margin-top:30px;font-size:12px;color:var(--faint)}}
  .others a{{color:var(--fuel);text-decoration:none;margin-right:10px}}
</style>
</head>
<body>
<nav class="topbar">
  <div class="inner">
    <a class="brand" href="{home_href}">
      <span class="mark">G</span>
      <span class="bname">Gasolina</span>
    </a>
    <div class="nav">
      <a href="{home_href}">{nav_prices}</a>
      <a href="{root}index.html#kalkulator">{nav_calc}</a>
      <a href="{root}granice.html">{nav_borders}</a>
      <a href="{root}istorija.html">{nav_history}</a>
      <a href="{root}vodici.html">{nav_guides}</a>
      <a class="lang" href="{switch_href}" title="{switch_title}">{switch_label}</a>
    </div>
  </div>
</nav>

<div class="wrap">
  <div class="crumb"><a href="{root}index.html">Gasolina</a> / <a href="{root}granice.html">{crumb_borders}</a> / {name}</div>
  <div class="h1row">
    <h1>{h1}</h1>
    <span class="dirchip">{flag_from} {from_code} → {flag_to} {to_code}</span>
  </div>

  {hero_block}

  <p class="lead">{intro}</p>

  <div class="cta">
    <a class="btn" href="{root}granice.html" onclick="track('landing_cta', {{prelaz:'{id}', cilj:'granice'}})">{cta_borders}</a>
    <a class="btn ghost" href="{root}index.html#kalkulator" onclick="track('landing_cta', {{prelaz:'{id}', cilj:'kalkulator'}})">{cta_calc}</a>
  </div>

  <div class="info">
    <div><b>{dir}:</b> {flag_from} {from_c} \u2192 {flag_to} {to_c}</div>
    <div><b>{road_l}:</b> {road}</div>
    <div><b>{pair_l}:</b> {pair}</div>
    {alt_line}
  </div>

  <section class="faq">
    <h2>{faq_h}</h2>
    {faq_html}
  </section>

  <div class="others">{others} {other_links}</div>
</div>

<script>
  const PRELAZ_ID = "{id}";
  const FEEDS = {feeds_json};
  const T = {{noQueue: "{no_queue}", noData: "{no_data}"}};
  const SHARE = {{label:"{share_label}", copied:"{share_copied}", out:"{share_out}", inn:"{share_in}", noq:"{share_noq}", nd:"{share_nd}", nowait:"{share_nowait}"}};
  let _waitState = null; // popunjava waitBox IIFE, koristi doShare

  function doShare(kind, btn) {{
    const url = "https://gasolina.rs/{self_path}";
    let parts = [];
    if (_waitState) {{
      const f = v => v==null ? SHARE.nd : (v<=30 ? SHARE.noq : (v>=60 ? Math.floor(v/60)+"h "+(v%60)+"m" : v+" min"));
      parts.push(`${{SHARE.out}}: ${{f(_waitState.out)}}`);
      parts.push(`${{SHARE.inn}}: ${{f(_waitState.inn)}}`);
    }} else {{
      parts.push(SHARE.nowait);
    }}
    const text = `{name} ({from_c} - {to_c}): ${{parts.join(", ")}}`;
    track("podeli_granica", {{prelaz: PRELAZ_ID, kanal: kind, izvor: "landing"}});
    if (kind === "copy") {{
      navigator.clipboard.writeText(text + " " + url).then(() => {{
        if (btn) {{ const old = btn.textContent; btn.textContent = SHARE.copied; setTimeout(() => {{ btn.textContent = old; }}, 1500); }}
      }}).catch(() => {{}});
      return;
    }}
    const et = encodeURIComponent(text), eu = encodeURIComponent(url);
    const urls = {{
      viber: `viber://forward?text=${{et}}%20${{eu}}`,
      whatsapp: `https://wa.me/?text=${{et}}%20${{eu}}`,
      facebook: `https://www.facebook.com/sharer/sharer.php?u=${{eu}}&quote=${{et}}`,
    }};
    window.open(urls[kind], "_blank", "noopener");
  }}

  // --- wait box ---
  (async function(){{
    const box = document.getElementById("waitBox");
    if(!box) return;
    try{{
      const res = await fetch("{root}granice.json?cb=" + Date.now());
      if(!res.ok) throw new Error("no data");
      const data = await res.json();
      const c = (data.crossings || {{}})[PRELAZ_ID];
      const fmt = m => (m == null) ? T.noData : (m <= 30 ? T.noQueue : (m >= 60 ? Math.floor(m/60)+"h "+(m%60)+"m" : m + " min"));
      // NAJGORI dostupan podatak po smeru, iz SVIH izvora - identicna logika
      // kao effective() na granice.html. Sam AMSS cesto kaze "bez zadrzavanja"
      // i kad prijave vozaca kazu 4h - bez ovoga landing laze "Bez guzve".
      const eff = (dirKey) => {{
        const cands = [];
        const p = (c && c.found && c.putnicka) ? c.putnicka[dirKey] : null;
        if (p != null) cands.push({{v: p, src: null}});
        if (c && c.hu) {{ const v = c.hu[dirKey]; if (v != null && v > 0) cands.push({{v, src: "{src_hu}"}}); }}
      if (c && c.mk) {{
          const v = (dirKey === 'izlaz') ? c.mk.vlez : c.mk.izlez;
          if (v != null && v > 0) cands.push({{v, src: "{src_mk}"}});
          if (c.mk.opsto != null && c.mk.opsto > 0) cands.push({{v: c.mk.opsto, src: "{src_mk}"}});
        }}
        if (c && c.ba) {{ const v = c.ba[dirKey]; if (v != null && v > 0) cands.push({{v, src: "{src_ba}"}}); }}
        if (c && c.tt) {{ const v = c.tt[dirKey]; if (v != null && v > 0) cands.push({{v, src: "{src_tt}"}}); }}
        if (!cands.length) return {{v: null, src: null, samAmss: false}};
        let best = cands[0];
        cands.forEach(x => {{ if (best.v == null || (x.v != null && x.v > best.v)) best = x; }});
        // AMSS-ovih 30 je podrazumevana vrednost ("bez zadrzavanja"), ne merenje.
        // Kad je jedini kandidat, uz brojku se ispisuje odakle dolazi.
        best.samAmss = (cands.length === 1 && best.src === null && best.v === 30);
        return best;
      }};
      const eIn = eff('ulaz'), eOut = eff('izlaz');
      _waitState = {{inn: eIn.v, out: eOut.v}};
      const srcNote = (e) => e.src
        ? `<div style="font-size:10px;color:var(--faint);margin-top:3px">{src_label}: ${{e.src}}</div>`
        : (e.samAmss ? `<div style="font-size:10px;color:var(--faint);margin-top:3px">{src_amss_only}</div>` : '');
      box.innerHTML = `
        <div class="wcell"><div class="wlabel">{wait_in}</div><div class="wval">${{fmt(eIn.v)}}</div>${{srcNote(eIn)}}</div>
        <div class="wcell"><div class="wlabel">{wait_out}</div><div class="wval">${{fmt(eOut.v)}}</div>${{srcNote(eOut)}}</div>`;
      // dodatni izvori (isti kao na granice.html karticama): prijave vozaca,
      // madjarska/makedonska strana - landing ne sme da bude siromasniji od pregleda
      const srcs = [];
      const mfmt = m => (m == null) ? "-" : (m + " min");
      if (c && c.ba) srcs.push(`\\uD83D\\uDE97 <b>{src_ba}:</b> {lbl_out} ${{mfmt(c.ba.izlaz)}} \\u00b7 {lbl_in} ${{mfmt(c.ba.ulaz)}}`);
      if (c && c.hu) srcs.push(`\\uD83C\\uDDED\\uD83C\\uDDFA <b>{src_hu}:</b> {lbl_in} ${{fmt(c.hu.ulaz)}} \\u00b7 {lbl_out} ${{fmt(c.hu.izlaz)}}`);
      if (c && c.mk) {{
        const mkTxt = (c.mk.opsto != null) ? ("~" + c.mk.opsto + " min")
          : ["vlez: " + mfmt(c.mk.vlez), "izlez: " + mfmt(c.mk.izlez)].join(" \\u00b7 ");
        srcs.push(`\\uD83C\\uDDF2\\uD83C\\uDDF0 <b>{src_mk}:</b> ${{mkTxt}}`);
      }}
      if (c && c.tt && (c.tt.izlaz != null || c.tt.ulaz != null)) {{
      const km = (m) => m ? ` ({tt_kolona} ~${{m}}m)` : "";
      srcs.push(`🗺️ <b>{src_tt}:</b> {lbl_out} ${{mfmt(c.tt.izlaz)}}${{km(c.tt.izlaz_kolona_m)}} \u00b7 {lbl_in} ${{mfmt(c.tt.ulaz)}}${{km(c.tt.ulaz_kolona_m)}} \u00b7 {tt_note}`);
      }}
      const sbox = document.getElementById("sources");
      if (sbox && srcs.length) {{
        sbox.innerHTML = srcs.map(s => `<div>${{s}}</div>`).join("");
        sbox.style.display = "grid";
      }}
    }}catch(e){{
      box.innerHTML = `<div class="wcell" style="grid-column:1/-1;color:var(--faint)">{wait_unavail}</div>`;
    }}
  }})();

  // --- plejer (isti hls.js kao granice.html) ---
  let _hls = null;
  // hls.js (~150 KB) se ne ucitava unapred: stranica se cesto otvara na granici
  // gde je mobilna mreza zakrcena, a kamera krece tek na klik. Povlaci se ovde,
  // jednom, i to samo ako browser nema nativni HLS (Safari/iOS ga ima).
  let _hlsLoad = null;
  function ensureHls(){{
    if (window.Hls) return Promise.resolve();
    if (_hlsLoad) return _hlsLoad;
    _hlsLoad = new Promise((res) => {{
      const s = document.createElement("script");
      s.src = "https://cdnjs.cloudflare.com/ajax/libs/hls.js/1.5.13/hls.min.js";
      s.onload = () => res();
      s.onerror = () => res();   // pad na video.src kao i do sada
      document.head.appendChild(s);
    }});
    return _hlsLoad;
  }}
  async function playFeed(idx, opts){{
    if(!FEEDS.length) return;
    const pane = document.getElementById("pane");
    const video = document.getElementById("cam");
    const overlay = document.getElementById("playOverlay");
    const liveTag = document.getElementById("liveTag");
    const src = FEEDS[idx].src;
    document.querySelectorAll(".feeds button").forEach((b,i)=>b.classList.toggle("on", i===idx));
    if(overlay) overlay.style.display = "none";
    video.style.display = "block";
    if(liveTag) liveTag.style.display = "block";
    if(_hls){{ try{{_hls.destroy();}}catch(e){{}} _hls = null; }}
    if(video.canPlayType("application/vnd.apple.mpegurl")){{
      video.src = src;
    }} else if ((await ensureHls(), window.Hls && Hls.isSupported())){{
      _hls = new Hls({{maxBufferLength:10}});
      _hls.loadSource(src);
      _hls.attachMedia(video);
    }} else {{
      video.src = src;
    }}
    if(opts && opts.muted) video.muted = true;
    video.play().catch(()=>{{}});
    // upisi stanje u URL (bez reload-a): jezicki prekidac i share link tako
    // uvek nose "koja kamera trenutno ide"
    try {{
      const u = new URL(window.location.href);
      u.searchParams.set("play", "1");
      u.searchParams.set("feed", String(idx));
      history.replaceState(null, "", u.toString());
    }} catch(e) {{}}
    track('kamera_play', {{prelaz: PRELAZ_ID, izvor: 'landing'}});
  }}
  // ?play=1 iz granice.html thumb klika: odmah pusti kameru (muted, browseri
  // ne dozvoljavaju autoplay sa zvukom). &feed=N bira konkretnu kameru
  // (Ulaz/Izlaz tabovi sa granice.html vode direktno na pravu).
  const _params = new URLSearchParams(window.location.search);
  if (FEEDS.length && _params.get("play") === "1") {{
    const _fi = Math.min(parseInt(_params.get("feed") || "0", 10) || 0, FEEDS.length - 1);
    document.addEventListener("DOMContentLoaded", () => playFeed(_fi, {{muted:true}}));
  }} else if (FEEDS.length) {{
    // bez autoplay-a: vizuelno oznaci prvu kameru kao izabranu, da tabovi
    // ne izgledaju "mrtvo" pre prvog klika (overlay pusta bas nju)
    document.addEventListener("DOMContentLoaded", () => {{
      const first = document.querySelector(".feeds button");
      if (first) first.classList.add("on");
    }});
  }}
  // SR<->EN prekidac: parametre cita U TRENUTKU KLIKA (playFeed ih upisuje u
  // URL tek kad kamera krene), pa prebacivanje jezika nastavlja istu kameru
  document.addEventListener("DOMContentLoaded", () => {{
    const ll = document.querySelector(".nav a.lang");
    if (!ll) return;
    const base = ll.getAttribute("href");
    ll.addEventListener("click", () => {{
      ll.href = base + window.location.search;
    }});
  }});
</script>
</body>
</html>
"""


def build_hero(c, lang, root):
    t = L[lang]
    name = c["name"]
    cid = c["id"]
    parts = []
    if c["feeds"]:
        btns = ""
        if len(c["feeds"]) > 1:
            btns = '<div class="feeds">' + "".join(
                f'<button onclick="playFeed({i})">{translate_feed_label(f["label"], lang)}</button>'
                for i, f in enumerate(c["feeds"])
            ) + "</div>"
        parts.append(
            f'<div class="pane" id="pane">'
            f'<span class="badge">{c["provider"]}</span>'
            f'<span class="live" id="liveTag">LIVE</span>'
            f'<img class="thumb" src="{root}thumbs/{cid}.jpg" alt="{name}" loading="lazy" onerror="this.remove()">'
            f'<video id="cam" playsinline controls muted></video>'
            f'<button class="overlay" id="playOverlay" onclick="playFeed(0)">'
            f'<svg width="26" height="26" viewBox="0 0 24 24" fill="currentColor"><path d="M8 5v14l11-7z"/></svg>'
            f'{t["play"]}</button>'
            f'</div>{btns}'
        )
    elif c["link_only"]:
        parts.append(
            f'<div class="pane">'
            f'<span class="badge">{c["provider"]}</span>'
            f'<a class="thumb-link" href="{c["official"]}" target="_blank" rel="noopener">'
            f'<img class="thumb" src="{root}thumbs/{cid}.jpg" alt="{name}" loading="lazy" '
            f'onerror="this.closest(\'.pane\').innerHTML=\'<div class=&quot;no-cam&quot; style=&quot;position:absolute;inset:0;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:10px&quot;>{t["cam_official_note"]}<br><a class=&quot;btn&quot; href=&quot;{c["official"]}&quot; target=&quot;_blank&quot; rel=&quot;noopener&quot;>{t["cam_official_btn"]}</a></div>\'">'
            f'<span class="snap-note">{t["snap_note"]}</span></a></div>'
        )
    else:
        parts.append(f'<div class="no-cam">{t["no_cam"]}</div>')

    if not c["no_wait"]:
        parts.append(f'<div class="wait-box" id="waitBox"><div class="wcell" style="grid-column:1/-1;color:var(--faint)">{t["wait_loading"]}</div></div>')
        parts.append('<div id="sources" style="display:none;gap:6px;margin-top:10px;font-size:12.5px;color:var(--dim);border:1px dashed var(--line);border-radius:10px;padding:12px 14px"></div>')

    if c.get("map_pb"):
        from_c = COUNTRY[lang].get(c["from"], c["from"])
        to_c = COUNTRY[lang].get(c["to"], c["to"])
        o_lat, o_lon, d_lat, d_lon = c["map_pb"]
        mid_lat, mid_lon = (o_lat + d_lat) / 2, (o_lon + d_lon) / 2
        lp = "!1ssr!2srs" if lang == "sr" else "!1sen!2sus"

        def pb_iframe(a_lat, a_lon, b_lat, b_lon, heading, a_id=None, b_id=None):
            # Tacka bez place ID-ja: !4m3!3m2!1d..!2d.. (Google sam trazi najblizi POI).
            # Tacka sa ID-jem:      !4m5!1s<id>!2s<ime>!3m2!1d..!2d..
            # Brojaci moraju da prate: svaki ID dodaje +2 i unutrasnjem (!4mN)
            # i spoljnom (!1mN) brojacu - inace Google odbaci ceo pb.
            names = c.get("map_route") or ("", "")
            label_by_id = {}
            for pair in (c.get("pb_id"), c.get("pb_id_in")):
                if pair:
                    for pid, nm in zip(pair, names):
                        if pid:
                            label_by_id.setdefault(pid, nm)

            def point(lat, lon, pid):
                if not pid:
                    return f"!4m3!3m2!1d{lat}!2d{lon}"
                lbl = urllib.parse.quote(label_by_id.get(pid, ""))
                return f"!4m5!1s{pid}!2s{lbl}!3m2!1d{lat}!2d{lon}"

            extra = (2 if a_id else 0) + (2 if b_id else 0)
            pb = (f"!1m{24 + extra}!1m12!1m3!1d11672.3!2d{mid_lon}!3d{mid_lat}"
                  f"!2m3!1f0!2f0!3f0!3m2!1i1024!2i768!4f13.1"
                  f"!4m{9 + extra}!3e0{point(a_lat, a_lon, a_id)}{point(b_lat, b_lon, b_id)}"
                  f"!5e0!3m2{lp}!4v1627540443619!5m2{lp}")
            return (
                f'<div class="map-box"><h2 style="font-family:\'Barlow Condensed\',sans-serif;font-size:20px;'
                f'text-transform:uppercase;margin:26px 0 10px">{heading}</h2>'
                f'<iframe src="https://www.google.com/maps/embed?pb={pb}" '
                f'width="100%" height="340" style="border:1px solid var(--line);border-radius:12px" '
                f'loading="lazy" title="{heading}" allowfullscreen></iframe></div>'
            )

        # smer 1 (kalibrisan izlaz) + smer 2: poseban kalibrisan ULAZNI par ako
        # postoji (mapPBin - trake na stanicama su jednosmerne pa obrnute tacke
        # rutaju obilazno i oblacic sa vremenom ode van kadra), inace obrnute tacke
        id_a, id_b = c.get("pb_id") or (None, None)
        parts.append(pb_iframe(o_lat, o_lon, d_lat, d_lon, t["map_h"].format(a=from_c, b=to_c),
                               id_a, id_b))
        if c.get("map_pb_in"):
            i_olat, i_olon, i_dlat, i_dlon = c["map_pb_in"]
            in_a, in_b = c.get("pb_id_in") or (id_b, id_a)
            parts.append(pb_iframe(i_olat, i_olon, i_dlat, i_dlon, t["map_h"].format(a=to_c, b=from_c),
                                   in_a, in_b))
        else:
            parts.append(pb_iframe(d_lat, d_lon, o_lat, o_lon, t["map_h"].format(a=to_c, b=from_c),
                                   id_b, id_a))
        parts.append(f'<div style="font-size:11px;color:var(--faint);margin-top:6px">{t["map_note"]}</div>')
    elif c.get("map_route"):
        from_c2 = COUNTRY[lang].get(c["from"], c["from"])
        to_c2 = COUNTRY[lang].get(c["to"], c["to"])
        map_h_txt = t["map_h"].format(a=from_c2, b=to_c2)
        a, b = c["map_route"]
        qa, qb = urllib.parse.quote(a), urllib.parse.quote(b)
        hl = "sr" if lang == "sr" else "en"
        parts.append(
            f'<div class="map-box"><h2 style="font-family:\'Barlow Condensed\',sans-serif;font-size:20px;'
            f'text-transform:uppercase;margin:26px 0 10px">{map_h_txt}</h2>'
            f'<iframe src="https://maps.google.com/maps?saddr={qa}&daddr={qb}&hl={hl}&t=m&z=13&output=embed" '
            f'width="100%" height="340" style="border:1px solid var(--line);border-radius:12px" '
            f'loading="lazy" title="{c["name"]}" allowfullscreen></iframe>'
            f'<div style="font-size:11px;color:var(--faint);margin-top:6px">{t["map_note"]}</div></div>'
        )
    # share red ide na SVAKU stranicu, nezavisno od tipa mape (bug: ranije je
    # bio uvucen u elif granu pa se video samo na prelazima sa fallback mapom)
    parts.append(
        f'<div class="share-row"><span class="share-label">{t["share_label"]}</span>'
        f'<button class="share-btn" onclick="doShare(\'viber\', this)">Viber</button>'
        f'<button class="share-btn" onclick="doShare(\'whatsapp\', this)">WhatsApp</button>'
        f'<button class="share-btn" onclick="doShare(\'facebook\', this)">Facebook</button>'
        f'<button class="share-btn" onclick="doShare(\'copy\', this)">{t["share_copy"]}</button></div>'
    )
    return "\n  ".join(parts)


def translate_feed_label(label, lang):
    """Labele kamera u borders-data.js su na srpskom - za EN stranice prevedi
    poznate reci, ostatak (AMSS/MUP u zagradi) ostaje isti."""
    if lang != "en":
        return label
    out = label
    for sr, en in (("Ulaz", "Entry"), ("Izlaz", "Exit"), ("Kamera", "Camera"), ("granica", "border")):
        out = out.replace(sr, en)
    return out


def render_page(c, all_c, lang):
    t = L[lang]
    root = "../" if lang == "en" else ""
    self_path = f"en/border-{c['id']}.html" if lang == "en" else f"granica-{c['id']}.html"
    from_c = COUNTRY[lang].get(c["from"], c["from"])
    to_c = COUNTRY[lang].get(c["to"], c["to"])
    name = c["name"]
    road = c["road"] or "-"
    pair = c["pair"] or "-"
    smer = f"{from_c} \u2192 {to_c}"

    fmtargs = dict(name=name, from_c=from_c, to_c=to_c, road=road, pair=pair, smer=smer)

    alts = alt_crossings(all_c, c)
    alt_names = ", ".join(a["name"] for a in alts)
    faq = [
        (t["faq1_q"].format(**fmtargs), t["faq1_a"].format(**fmtargs)),
        (t["faq2_q"].format(**fmtargs), t["faq2_a"].format(**fmtargs)),
    ]
    if alts:
        faq.append((t["faq3_q"].format(**fmtargs), t["faq3_a"].format(alts=alt_names, **fmtargs)))

    faq_json = ",".join(
        json.dumps({"@type": "Question", "name": q,
                    "acceptedAnswer": {"@type": "Answer", "text": re.sub(r"<[^>]+>", "", a)}},
                   ensure_ascii=False)
        for q, a in faq
    )
    faq_html = "".join(f"<details><summary>{q}</summary><p>{a}</p></details>" for q, a in faq)

    alt_line = ""
    if alts:
        links = ", ".join(f'<a href="{page_href(a["id"], lang, lang)}" style="color:var(--fuel)">{a["name"]}</a>' for a in alts)
        alt_line = f'<div><b>{t["alt_l"]}:</b> {t["alt_txt"].format(alts=links)}</div>'

    other_links = " ".join(
        f'<a href="{page_href(o["id"], lang, lang)}">{o["name"]}</a>'
        for o in all_c if o["id"] != c["id"]
    )

    og_image = f"thumbs/{c['id']}.jpg" if (c["feeds"] or c["link_only"]) else "og.png"

    return PAGE_TMPL.format(
        lang_attr=t["lang_attr"], og_locale=t["og_locale"], in_language=t["in_language"],
        title=t["title"].format(**fmtargs),
        description=t["description"].format(**fmtargs),
        h1=t["h1"].format(**fmtargs),
        intro=(c.get("intro_sr") if lang == "sr" else c.get("intro_en")) or t["intro"].format(**fmtargs),
        self_path=self_path, id=c["id"], name=name, root=root, home_href="index.html",
        crumb_borders=t["crumb_borders"],
        nav_prices=t["nav_prices"], nav_calc=t["nav_calc"], nav_borders=t["nav_borders"],
        nav_history=t["nav_history"], nav_guides=t["nav_guides"],
        switch_href=page_href(c["id"], "en" if lang == "sr" else "sr", lang),
        switch_label=t["switch_label"], switch_title=t["switch_title"],
        hero_block=build_hero(c, lang, root),
        cta_borders=t["cta_borders"], cta_calc=t["cta_calc"],
        dir=t["dir"], road_l=t["road_l"], pair_l=t["pair_l"],
        flag_from=FLAG.get(c["from"], ""), flag_to=FLAG.get(c["to"], ""),
        from_code=c["from"], to_code=c["to"],
        from_c=from_c, to_c=to_c, road=road, pair=pair,
        alt_line=alt_line,
        faq_h=t["faq_h"].format(**fmtargs), faq_html=faq_html, faq_json=faq_json,
        others=t["others"], other_links=other_links,
        og_image=og_image,
        feeds_json=json.dumps([{"label": translate_feed_label(f["label"], lang), "src": f["src"]} for f in c["feeds"]], ensure_ascii=False),
        no_queue=t["no_queue"], no_data=t["no_data"],
        src_amss_only=t["src_amss_only"],
        src_ba=t["src_ba"], src_hu=t["src_hu"], src_mk=t["src_mk"],
        src_tt=t["src_tt"], tt_note=t["tt_note"], tt_kolona=t["tt_kolona"],
        lbl_out=t["lbl_out"], lbl_in=t["lbl_in"], src_label=t["src_label"],
        share_label=t["share_label"], share_copied=t["share_copied"],
        share_out=t["share_out"], share_in=t["share_in"],
        share_noq=t["share_noq"], share_nd=t["share_nd"], share_nowait=t["share_nowait"],
        wait_in=t["wait_in"], wait_out=t["wait_out"],
        wait_loading=t["wait_loading"],
        wait_unavail=t["wait_unavail"].format(root=root, id=c["id"]),
    )


def main():
    js = open(SRC, encoding="utf-8").read()
    crossings = parse_crossings(js)
    if not crossings:
        print("Nijedan prelaz nije parsiran iz borders-data.js!")
        return 1
    os.makedirs("en", exist_ok=True)
    for c in crossings:
        for lang in ("sr", "en"):
            path = f"en/border-{c['id']}.html" if lang == "en" else f"granica-{c['id']}.html"
            with open(path, "w", encoding="utf-8") as f:
                f.write(render_page(c, crossings, lang))
            print(f"Napisano: {path}")
    print(f"Gotovo: {len(crossings)} prelaza x 2 jezika = {len(crossings)*2} stranica.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
