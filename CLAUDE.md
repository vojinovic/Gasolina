# Gasolina — pravila rada

Sajt: gasolina.rs — cene goriva za 12 zemalja, kalkulator puta, granični prelazi uživo.
Hosting: GitHub Pages sa `main` grane, DNS na Cloudflare. Vlasnik radi kroz GitHub browser UI.

## Gvozdena pravila

1. **Nula obaveza.** Nikad servis koji traži karticu. Zato: Google `pb` embed umesto Maps API,
   TomTom freemium, ORS. Ako neko rešenje traži plaćanje — predloži ga, ali ne ugrađuj.
2. **Ne nagađaj URL-ove, putanje ni koordinate.** Stream adrese, `pb` stringovi i koordinate
   koridora se ne izmišljaju — vlasnik ih potvrđuje u browseru pre ugradnje.
3. **Pošten prikaz je brend.** Ograničenja podataka se pišu na sajtu. Primeri koji već stoje:
   „ne uključuje pasošku kontrolu", „vidi se samo deo kolone", „jedini izvor: AMSS
   (podrazumevana vrednost)". Ako podatak ne nosi tvrdnju — ne tvrdi je.
4. **Vizuelne izmene prvo na jednom probnom fajlu**, tek onda svuda.
5. **Označi šta je stvarno promenjeno** vs samo regenerisano pri isporuci.

## Validacija pre isporuke (obavezno)

- `python3 -m py_compile *.py`
- `python3 <scraper>.py --selftest` za svaki scraper koji diraš
- `python3 ci_checks.py` — `node --check` za inline JS, `json.loads` za JSON-LD i `.json`
- CI (`.github/workflows/ci.yml`) radi isto na svaki push; ne obaraj ga.

Svaki novi parser dobija **selftest sa fixture-om prepisanim sa žive stranice**, bez mreže.

## Automatizacija — šta okida šta

- Push na `borders-data.js` ili `generate_crossing_pages.py` → workflow „Generate Crossing Pages"
  regeneriše svih 24 landing stranice (12 SR + 12 `en/`). Za izmene prelaza isporučuj **samo**
  generator i/ili `borders-data.js`, nikad ručno editovane generisane stranice.
- `update-granice.yml`: cron 30 min, koristi Secret `TOMTOM_KEY`.
- `update.yml` (cene): subota 07:00 UTC.
- `update-thumbs.yml`: 2h ciklus.
- Statičan HTML/sitemap ne traži workflow — Pages objavi sam.

## Naučene lekcije (ne ponavljati)

- **Duga ruta za kratko rastojanje = koordinata na pogrešnom kolovozu.** Pre ugradnje proveri
  `https://www.google.com/maps/dir/<lat1>,<lon1>/<lat2>,<lon2>`. Odnos rute prema vazdušnoj
  liniji preko ~1.3 znači da Google pravi petlju i da tačka nije na traci u tom smeru.
- **Google place ID nadjačava koordinatu** u `pb` stringu. Ne mogu se kombinovati lepo ime i
  ručno kalibrisana tačka — bira se jedno. Svaki ID dodaje +2 brojačima `!1mN` i `!4mN`.
- **`mapPB` hrani i pb mapu i TomTom koridor**, pa jedna loša koordinata kvari i sliku i podatke.
- **Sintaksno ispravan JS može da pukne u browseru.** `srcs.push()` pre `const srcs = []` je
  oborio wait-box na svih 22 stranice; `node --check` to ne hvata. `ci_checks.py` sada hvata.
- **AMSS-ovih 30 minuta je podrazumevana vrednost, ne merenje.** Ne sme da nadjača tuđih 60.
- **Prekratak koridor ne vidi kolonu.** Ispod ~500 m TomTom prijavi „bez zadržavanja" i kad se stoji.
- Kad izvor cena pukne, scraper zadrži poslednje vrednosti — zato `index.html` označava
  podatke starije od 7 dana. Ne uklanjaj tu oznaku.
- **Novi izvor mora da uđe i u `build()`.** Generička grana za prelaze van AMSS mape
  spajala je samo `mk` i `tt`, pa su TomTom (jutro) pa BorderAlarm (veče) tiho ispadali.
  Sad ide kroz `set(mk) | set(tt) | set(ba) | set(hu)`.
- **BorderAlarm ima zasebnu stranicu po zemlji.** Srpska ne sadrži MK–GR prelaze;
  za Medžitliju i Bogorodicu se čita `countries/northmacedonia/`.
- **Natpisi smerova prate zemlju prelaza**, ne Srbiju (`AKUZATIV`/`GENITIV` u generatoru).
  „Ulaz u Srbiju" na Bogorodici je bio besmislen.
- `onerror` na slici: prvo dodaj klasu roditelju, pa tek onda `this.remove()` —
  posle uklanjanja iz DOM-a `closest()` vraća `null`.

## Stil koda

- Bez build koraka i bez framework-a: čist HTML/CSS/JS, Python bez zavisnosti van
  `requests` + `beautifulsoup4`.
- Komentari na srpskom, bez dijakritike u Python fajlovima.
- `\uXXXX` eskejpi NE rade u `borders-data.js` ni u `.py` šablonima — piši pravi UTF-8.
- Mobilni prvo: polja ≥16px (iOS zumira ispod toga), dodirne mete ≥44px.
- `hls.js` se ne učitava unapred nego na prvi klik (`ensureHls`) — stranica se otvara
  na granici gde je mreža zakrčena.

## Rad kroz Claude Code

- Svaki zadatak ide u **novu sesiju**: nastavak u staroj sesiji gura na već merge-ovanu
  granu i izmene ostanu bez PR-a.
- Pre commita obavezno `python3 ci_checks.py`; za izmene scrapera i `--selftest`.
- Ne generiši `granica-*.html` ručno — to radi workflow na push `borders-data.js`.
