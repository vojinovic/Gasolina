/* ===========================================================================
   borders-data.js  -  jedinstveni izvor istine za granicne prelaze
   Koriste ga:
     - granice.html  (prikaz kamera + vreme cekanja)
     - index.html    (kalkulator -> "granice na ovoj ruti")

   Svaki prelaz ima:
     id        -> mora da se poklapa sa granice.json (scraper TARGETS)
     from/to   -> ISO kod zemlje (RS, ME, HR, HU, MK, BA, BG, RO)
     feeds     -> HLS .m3u8 kamere (prazno ako nema kamere)
     noCamera  -> true kad za prelaz ne postoji zvanicna kamera
     wait      -> DEMO brojke (fallback dok granice.json ne stigne)
=========================================================================== */
window.BORDERS = (function () {
  const FLAG = {
    RS: "\uD83C\uDDF7\uD83C\uDDF8", ME: "\uD83C\uDDF2\uD83C\uDDEA",
    HR: "\uD83C\uDDED\uD83C\uDDF7", HU: "\uD83C\uDDED\uD83C\uDDFA",
    MK: "\uD83C\uDDF2\uD83C\uDDF0", BA: "\uD83C\uDDE7\uD83C\uDDE6",
    BG: "\uD83C\uDDE7\uD83C\uDDEC", RO: "\uD83C\uDDF7\uD83C\uDDF4",
    GR: "\uD83C\uDDEC\uD83C\uDDF7",
  };

  const CROSSINGS = [
    {
      id: "gradina", mapPBin: [42.993661, 22.8438965, 43.0003028, 22.8248447], mapPB: [43.0003029, 22.8241663, 42.9957489, 22.8377659], mapRoute: ["Granični prelaz Gradina", "ГКПП Калотина"], coords: [43.0125, 22.8231], name: "Gradina", from: "RS", to: "BG",
      pair: "Kalotina (BG)", road: "E80", provider: "AMSS",
      official: "https://kamere.amss.org.rs/",
      feeds: [
        { label: "Ulaz", dir: "in",  src: "https://kamere.amss.org.rs/gradina1/gradina1.m3u8" },
        { label: "Izlaz", dir: "out", src: "https://kamere.amss.org.rs/gradina2/gradina2.m3u8" },
      ],
      intro: "Gradina je glavni prelaz ka Bugarskoj, na E80 naspram Kalotine, i jedan od tri najprometnija na sajtu. U našem arhivu od 665 snimaka po smeru (24.06–15.08.2026) izlazni smer ima brojku u dve trećine slučajeva: tipično 45 minuta, ali svaki deseti zapis prelazi 150, a najduže zabeleženo je 5 sati i 30 minuta (18.07, prijava vozača). Ulazni smer je znatno lakši — tipično 25 minuta. Najgore je oko 14 časova i petkom, kad dve trećine zapisa nije prohodno. Gradina je i redak prelaz na kom granična policija zaista objavljuje raznovrsne vrednosti, od 40 do 240 minuta, a ne samo podrazumevanih 30. Saobraćajno merenje ovde radi pouzdano — koridor daje signal u 94 odsto odgovora, sa najdužom izmerenom kolonom od 1.226 metara.",
      introEn: "Gradina is the main crossing into Bulgaria, on the E80 opposite Kalotina, and one of the three busiest on this site. Across our archive of 665 snapshots per direction (24 June – 15 August 2026) the outbound side carries a figure two thirds of the time: typically 45 minutes, though one record in ten exceeds 150, and the longest recorded was 5 hours 30 minutes (18 July, driver report). Inbound is much easier — typically 25 minutes. The worst window is around 2 pm and on Fridays, when two thirds of records are not clear. Gradina is also one of the rare crossings where the border police genuinely publish varied values, from 40 to 240 minutes, rather than only the default 30. Traffic measurement works reliably here — the corridor returns a signal in 94 percent of responses, with a longest measured queue of 1,226 metres.",
      wait: { putnicka: { ulaz: 30, izlaz: 30 }, teretna: { ulaz: 30, izlaz: 30 } },
    },
    {
      id: "horgos", mapPBin: [46.1827699, 19.9869952, 46.1696718, 19.9712071], mapPB: [46.1662695, 19.9615223, 46.1834449, 19.9880802], mapRoute: ["Granični prelaz Horgoš", "Röszke határátkelőhely"], coords: [46.1755, 19.9772], name: "Horgos", from: "RS", to: "HU",
      pair: "Roszke (HU)", road: "E75", provider: "AMSS",
      official: "https://kamere.amss.org.rs/",
      feeds: [
        { label: "Ulaz", dir: "in",  src: "https://kamere.amss.org.rs/horgos1/horgos1.m3u8" },
        { label: "Izlaz", dir: "out", src: "https://kamere.amss.org.rs/horgos2/horgos2.m3u8" },
      ],
      intro: "Horgoš je najveći prelaz ka Mađarskoj, na E75 naspram Rösckea, i jedini na sajtu koji ima dva nezavisna zvanična izvora: srpsku graničnu policiju i mađarsku policiju, koja je za ovaj prelaz javila vrednost u 328 zapisa. Zato Horgoš ima i najviše zabeleženih neslaganja između izvora — u oko devet odsto zapisa dve procene se razilaze toliko da sajt ne bira pobednika nego pokazuje obe. Tipično čekanje je 45 minuta na izlazu i 30 na ulazu, sa najdužim zabeleženim od 3 i 4 sata. Najoštriji trenutak nije veče nego jutro: ulazni smer petkom oko 9 časova nije prohodan u 91 odsto zapisa. Izlaz je najgori oko 16 časova i nedeljom. Izmerena kolona dosezala je 2.222 metra.",
      introEn: "Horgos is the largest crossing into Hungary, on the E75 opposite Roszke, and the only one on this site with two independent official sources: the Serbian border police and the Hungarian police, who reported a value for it in 328 records. That is why Horgos also shows the most disagreement between sources — in about nine percent of records two estimates differ so widely that the site picks no winner and shows both. Typical waits are 45 minutes outbound and 30 inbound, with the longest recorded at 3 and 4 hours. The sharpest moment is not the evening but the morning: inbound on Fridays around 9 am is not clear in 91 percent of records. Outbound peaks around 4 pm and on Sundays. The measured queue has reached 2,222 metres.",
      wait: { putnicka: { ulaz: 30, izlaz: 30 }, teretna: { ulaz: 30, izlaz: 30 } },
    },
    {
      // Koridor prosiren 26.07.2026: stari je bio 842 m (izlaz) / 389 m (ulaz) -
      // prekratko da TomTom uhvati kolonu, pa je prelaz sistematski javljao
      // "bez zadrzavanja". Nove tacke su IZVAN obe stanice (kod Granicnog
      // terminala i severno od Tompe), 1274 m vazdusno / 1.4 km rutom.
      id: "kelebija", mapPBin: [46.172760, 19.554454, 46.163229, 19.563629], mapPB: [46.163229, 19.563629, 46.172760, 19.554454], mapRoute: ["Granični prelaz Kelebija", "Tompa határátkelőhely"], coords: [46.191, 19.541], name: "Kelebija", from: "RS", to: "HU",
      pair: "Tompa (HU)", road: "M17/E75", provider: "MUP",
      official: "https://kamere.amss.org.rs/",
      feeds: [
        { label: "Ulaz", dir: "in",  src: "https://kamere.mup.gov.rs:4443/Kelebija/kelebija1.m3u8" },
        { label: "Izlaz", dir: "out", src: "https://kamere.mup.gov.rs:4443/Kelebija/kelebija2.m3u8" },
      ],
      intro: "Kelebija je manji prelaz ka Mađarskoj, naspram Tompe, četrdesetak kilometara zapadno od Horgoša — i po našim merenjima znatno mirniji. U 451 snimku po smeru (14.07–15.08.2026) oba smera su bez gužve u oko dve trećine zapisa, dok je Horgoš u istom periodu bez gužve u svega desetak odsto. Kad se čekanje ipak pojavi, tipično je 40 do 45 minuta, a najduže zabeleženo svega sat i po. Zato je Kelebija prva razumna zamena kad Horgoš stane. Dve ograde: mađarska policija za Kelebiju javlja retko, pa se ovde više oslanjamo na prijave vozača nego na Horgošu, a saobraćajno merenje vidi kolonu tek u petini odgovora. Najgore je subotom, oko 17 časova.",
      introEn: "Kelebija is a smaller crossing into Hungary, opposite Tompa, some forty kilometres west of Horgos — and by our measurements considerably calmer. Across 451 snapshots per direction (14 July – 15 August 2026) both directions are clear in about two thirds of records, while Horgos over the same period is clear in barely ten percent. When a wait does appear it is typically 40 to 45 minutes, and the longest recorded was just an hour and a half. That makes Kelebija the first sensible substitute when Horgos seizes up. Two caveats: the Hungarian police report for Kelebija rarely, so we lean more on driver reports here than at Horgos, and traffic measurement sees a queue in only a fifth of responses. The worst window is Saturdays around 5 pm.",
      wait: { putnicka: { ulaz: 30, izlaz: 30 }, teretna: { ulaz: 30, izlaz: 30 } },
    },
    {
      id: "batrovci", mapPBin: [45.0487588, 19.0878578, 45.0453227, 19.1216674], mapPB: [45.0455054, 19.1216508, 45.048986, 19.0847306], mapRoute: ["Granični prelaz Batrovci", "Granični prijelaz Bajakovo"], coords: [45.0492, 19.0989], name: "Batrovci", from: "RS", to: "HR",
      pair: "Bajakovo (HR)", road: "E70", provider: "AMSS",
      official: "https://kamere.amss.org.rs/",
      feeds: [
        { label: "Ulaz", dir: "in",  src: "https://kamere.amss.org.rs/batrovci1/batrovci1.m3u8" },
        { label: "Izlaz", dir: "out", src: "https://kamere.amss.org.rs/batrovci2/batrovci2.m3u8" },
      ],
      intro: "Batrovci su glavni prelaz ka Hrvatskoj i Zapadnoj Evropi, na E70 naspram Bajakova, i po našem arhivu nose najduže repove na celom sajtu. U 665 snimaka po smeru (24.06–15.08.2026) tipično čekanje je oko sat vremena u oba smera, ali svaki deseti zapis na ulazu prelazi šest sati, a najduže zabeleženo je 13 sati (18.07, prijava vozača). Na izlazu je najgore zabeleženo 10 sati. Najoštrije je oko podneva i petkom. Vredi znati odakle to znamo: za ulazni smer granična policija u svih 665 zapisa objavljuje isto podrazumevanih 30 minuta, pa sve što na ovoj stranici piše o dugim kolonama dolazi iz prijava vozača i iz izmerene dužine kolone, koja je dosezala 2.235 metara.",
      introEn: "Batrovci is the main crossing into Croatia and onward to Western Europe, on the E70 opposite Bajakovo, and our archive shows it carries the longest tails on the whole site. Across 665 snapshots per direction (24 June – 15 August 2026) the typical wait is about an hour in both directions, but one inbound record in ten exceeds six hours, and the longest recorded was 13 hours (18 July, driver report). Outbound the longest recorded was 10 hours. The sharpest window is around midday and on Fridays. It is worth knowing where that comes from: for the inbound direction the border police published the same default 30 minutes in all 665 records, so everything this page says about long queues comes from driver reports and from the measured queue length, which has reached 2,235 metres.",
      wait: { putnicka: { ulaz: 30, izlaz: 30 }, teretna: { ulaz: 30, izlaz: 300 } },
    },
    {
      id: "presevo", mapPBin: [42.235423, 21.704292, 42.242780, 21.702422], mapPB: [42.2398219, 21.7026983, 42.2314251, 21.704081], mapRoute: ["Granični prelaz Preševo", "Граничен премин Табановце"], coords: [42.2436, 21.6433], name: "Presevo", from: "RS", to: "MK",
      pair: "Tabanovce (MK)", road: "E75", provider: "AMSS / MUP",
      official: "https://kamere.amss.org.rs/",
      feeds: [
        { label: "Ulaz (AMSS)", dir: "in",  src: "https://kamere.amss.org.rs/presevo1/presevo1.m3u8" },
        { label: "Izlaz (AMSS)", dir: "out", src: "https://kamere.amss.org.rs/presevo2/presevo2.m3u8" },
        { label: "Ulaz (MUP)", dir: "in",  src: "https://kamere.mup.gov.rs:4443/Presevo/presevo1.m3u8" },
        { label: "Izlaz (MUP)", dir: "out", src: "https://kamere.mup.gov.rs:4443/Presevo/presevo2.m3u8" },
      ],
      intro: "Preševo je glavni prelaz ka Severnoj Makedoniji i Grčkoj, na E75 naspram Tabanovaca, i jedini na sajtu sa dve kamere u oba smera. U 665 snimaka po smeru (24.06–15.08.2026) tipično čekanje je 45 minuta na izlazu i 35 na ulazu, sa najdužim zabeleženim od 6 i po sati na izlazu (20.07, prijava vozača). Najgore je oko 16 časova i nedeljom. Za ovaj prelaz javlja i makedonska strana, u 221 zapisu, vrednostima od 15 do 120 minuta — što je važno jer se ta procena odnosi na makedonsku kontrolu, nizvodno od kamere koja gleda srpski plato. Prazan plato na slici zato ne opovrgava makedonsku brojku. Izmerena kolona dosezala je 1.908 metara.",
      introEn: "Presevo is the main crossing into North Macedonia and onward to Greece, on the E75 opposite Tabanovce, and the only one on this site with two cameras in both directions. Across 665 snapshots per direction (24 June – 15 August 2026) the typical wait is 45 minutes outbound and 35 inbound, with the longest recorded at six and a half hours outbound (20 July, driver report). The worst window is around 4 pm and on Sundays. The North Macedonian side also reports here, in 221 records, with values from 15 to 120 minutes — which matters, because that estimate covers the North Macedonian control, downstream of the camera pointed at the Serbian apron. An empty apron in the picture therefore does not refute the North Macedonian figure. The measured queue has reached 1,908 metres.",
      wait: { putnicka: { ulaz: 30, izlaz: 30 }, teretna: { ulaz: 30, izlaz: 30 } },
    },
    {
      id: "bogorodica", pbId: ["", "0x135626c88b4d3907%3A0xc81c83269be4c289"], pbIdIn: ["0x135626c88b4d3907%3A0xc81c83269be4c289", "0x135627f315b1847f%3A0x8ca1dfa25e55ace1"], mapPBin: [41.1276257, 22.5516536, 41.134253, 22.5490008], mapPB: [41.135969, 22.5464805, 41.1276257, 22.5516536], mapRoute: ["Граничен премин Богородица", "Border Crossing Point of Evzoni"], coords: [41.1309, 22.5503], name: "Bogorodica", from: "MK", to: "GR",
      pair: "Evzoni (GR)", road: "E75", provider: "roads.org.mk",
      official: "https://alltrafficcams.com/live/border-crossings/north-macedonia/greece/bogorodica-evzonoi/",
      feeds: [
        { label: "Izlaz (ka Grckoj)", dir: "out", src: "https://streaming1.neotel.net.mk/stream/bogorodica.m3u8" },
      ],
      intro: "Bogorodica je glavni prelaz iz Severne Makedonije u Grčku, na E75 naspram Evzona, i za mnoge sa ovih prostora poslednja rampa pre mora. Pratimo je od 12.07.2026, u 484 snimka po smeru. Tipično čekanje je 30 minuta na izlazu i 25 na ulazu, a najduže zabeleženo 3 sata (03.08, makedonski izvor). Najgore je oko 13 časova i subotom. AMSM za ovaj prelaz koristi finiju skalu od većine izvora — objavljuje 15, 20, 30, 40, 50, 60 pa i 180 minuta. Dve ograde: kamera postoji samo za izlazni smer ka Grčkoj, a saobraćajno merenje ovde skoro ništa ne vidi — ulazni koridor je dao signal u svega 0,3 odsto odgovora, pa njegova nula ovde ne znači da je prohodno.",
      introEn: "Bogorodica is the main crossing from North Macedonia into Greece, on the E75 opposite Evzoni, and for many travellers from this region the last barrier before the sea. We have tracked it since 12 July 2026, across 484 snapshots per direction. Typical waits are 30 minutes outbound and 25 inbound, with the longest recorded at 3 hours (3 August, North Macedonian source). The worst window is around 1 pm and on Saturdays. AMSM uses a finer scale here than most sources — it publishes 15, 20, 30, 40, 50, 60 and even 180 minutes. Two caveats: there is a camera only for the outbound direction towards Greece, and traffic measurement sees almost nothing here — the inbound corridor returned a signal in just 0.3 percent of responses, so its zero does not mean the road is clear.",
      wait: null,
    },
    {
      // Koridor kalibrisan 26.07.2026 - tacke su IZVAN obe stanice (selo
      // Medzitlija i Kaoil pumpa), 1425 m vazdusno / 1.5 km rutom, odnos 1.05,
      // bez petlje. Stare tacke (same stanice, 455 m) davale su 6.4 km jer su
      // bile sa suprotnih strana rampi.
      id: "medzitlija", mapPB: [40.925092, 21.417021, 40.912327, 21.418543], mapPBin: [40.912327, 21.418543, 40.925092, 21.417021], mapRoute: ["Граничен премин Меџитлија", "Niki Customs"], coords: [40.9199, 21.4167], name: "Medzitlija", from: "MK", to: "GR",
      pair: "Niki (GR)", road: "E65", provider: "neotel.net.mk",
      official: "https://alltrafficcams.com/live/border-crossings/north-macedonia/greece/medzitlija-niki/",
      feeds: [
        { label: "Ulaz (ka Makedoniji)", dir: "in", src: "https://streaming1.neotel.net.mk/stream/medzitlija.m3u8" },
      ],
      intro: "Medžitlija je manji prelaz iz Severne Makedonije u Grčku, na E65 naspram Nikija, jugozapadno od Bitolja, i po našim merenjima najmirniji prelaz koji pratimo. U 284 snimka po smeru (26.07–15.08.2026) tipično čekanje je 10 minuta, a u tri četvrtine zapisa vozači prijavljuju kratko zadržavanje. To ne znači da je uvek tako: 04.08. je zabeležena prijava od pet sati u izlaznom smeru. Za Medžitliju nijedan zvanični izvor ne objavljuje procenu, pa sve što ovde piše dolazi iz prijava vozača, a saobraćajno merenje daje signal u svega jedan do tri odsto odgovora. Kamera postoji samo za ulazni smer. Drugim rečima: prelaz je verovatno prohodan, ali to ovde nema ko nezavisno da potvrdi.",
      introEn: "Medzitlija is a smaller crossing from North Macedonia into Greece, on the E65 opposite Niki, southwest of Bitola, and by our measurements the calmest crossing we track. Across 284 snapshots per direction (26 July – 15 August 2026) the typical wait is 10 minutes, and in three quarters of records drivers report only a short hold. That does not make it reliable: on 4 August a five-hour report was recorded in the outbound direction. No official source publishes an estimate for Medzitlija, so everything here comes from driver reports, while traffic measurement returns a signal in only one to three percent of responses. There is a camera for the inbound direction only. In short: the crossing is probably clear, but here there is nobody to confirm that independently.",
      wait: null,
    },
    {
      id: "sremska-raca", mapRoute: ["Granični prelaz Sremska Rača", "Granični prelaz Rača"], coords: [44.9042, 19.2958], name: "Sremska Raca", from: "RS", to: "BA",
      pair: "Raca (BiH)", road: "E70", provider: "MUP",
      official: "https://kamere.amss.org.rs/",
      feeds: [
        { label: "Ulaz", dir: "in",  src: "https://kamere.mup.gov.rs:4443/SremskaRaca/sremskaraca1.m3u8" },
        { label: "Izlaz", dir: "out", src: "https://kamere.mup.gov.rs:4443/SremskaRaca/sremskaraca2.m3u8" },
      ],
      intro: "Sremska Rača je prelaz ka Bosni i Hercegovini, na E70 naspram Rače, najkraća veza Beograda sa Bijeljinom i Tuzlom. Ovde smo dužni da budemo izričiti: u 665 snimaka po smeru (24.06–15.08.2026) ovaj prelaz nije imao nijednu upotrebljivu procenu čekanja — nijednom. Granična policija za oba smera objavljuje isključivo podrazumevanih 30 minuta, što je vrednost koju drže dok im se ne javi promena, a ne merenje stanja. Za Sremsku Raču ne javlja nijedan susedni izvor, nema prijava vozača preko BorderAlarma, i nije definisan koridor za merenje saobraćaja. Zato je kamera uživo ovde jedini stvarni podatak, i zato stranica piše da pouzdane procene nema umesto da prikaže brojku koja bi zvučala uverljivo.",
      introEn: "Sremska Raca is the crossing into Bosnia and Herzegovina, on the E70 opposite Raca, the shortest link from Belgrade to Bijeljina and Tuzla. Here we owe you a blunt statement: across 665 snapshots per direction (24 June – 15 August 2026) this crossing never once carried a usable waiting estimate. The border police publish only the default 30 minutes for both directions, a value they hold until a change is reported to them, not a measurement of conditions. No neighbouring source reports for Sremska Raca, there are no driver reports via BorderAlarm, and no corridor is defined for traffic measurement. The live camera is therefore the only real data here, which is why the page says there is no reliable estimate instead of showing a figure that would merely sound convincing.",
      wait: { putnicka: { ulaz: 30, izlaz: 30 }, teretna: { ulaz: 30, izlaz: 240 } },
    },
    {
      id: "spiljani", mapRoute: ["Granični prelaz Špiljani", "Granični prelaz Dračenovac"], coords: [42.93, 20.35], name: "Spiljani", from: "RS", to: "ME",
      pair: "Dracenovac (MNE)", road: "E65/E80", provider: "MUP",
      official: "https://kamere.amss.org.rs/",
      feeds: [
        { label: "Ulaz", dir: "in",  src: "https://kamere.mup.gov.rs:4443/Spiljani/spiljani1.m3u8" },
        { label: "Izlaz", dir: "out", src: "https://kamere.mup.gov.rs:4443/Spiljani/spiljani2.m3u8" },
      ],
      official2: { label: "kamera CG strane (Dracenovac) \u2197", url: "http://kamere.mup.gov.me/kamere.php?kamere=Dracenovac&lang=me" },
      intro: "Špiljani su glavni prelaz ka Crnoj Gori na pravcu preko Novog Pazara, naspram Dračenovca, i jedan od najtraženijih prelaza na ovom sajtu. Utoliko je pošteniji ovaj podatak: u 664 snimka po smeru (24.06–15.08.2026) procena čekanja je postojala u svega četiri zapisa — 20.07. je granična policija objavila 35 minuta za izlaz i 50 za ulaz. U svemu ostalom stoji podrazumevanih 30 minuta, što nije merenje. Za Špiljane ne javlja crnogorska strana, nema prijava vozača preko BorderAlarma, i nije definisan koridor za merenje saobraćaja. Kamere postoje za oba smera i trenutno su jedini stvaran izvor. Ako vam je bitno stanje pre polaska, ovde gledajte sliku, ne brojku.",
      introEn: "Spiljani is the main crossing into Montenegro on the route through Novi Pazar, opposite Dracenovac, and one of the most searched-for crossings on this site. Which makes this all the more worth stating plainly: across 664 snapshots per direction (24 June – 15 August 2026) a waiting estimate existed in just four records — on 20 July the border police published 35 minutes outbound and 50 inbound. Everything else is the default 30 minutes, which is not a measurement. The Montenegrin side does not report for Spiljani, there are no driver reports via BorderAlarm, and no corridor is defined for traffic measurement. Cameras exist for both directions and are currently the only real source. If the state of the crossing matters before you set off, look at the picture here, not at a number.",
      wait: { putnicka: { ulaz: 30, izlaz: 30 }, teretna: { ulaz: 30, izlaz: 30 } },
    },
    {
      // Alternativa Presevu kad se tamo stvore kolone. Nema kamere (nije ni na MUP
      // ni na AMSS spisku, provereno 26.07.2026) - stranica radi na mapi saobracaja.
      // Koridor: 42.314123,21.886043 (RS, ~300 m pre rampe iz pravca Vranja) ->
      // 42.311669,21.878821 (MK, iza policijske stanice Pelince). Jedan kolovoz,
      // pa mapPBin nije potreban - generator sam okrene tacke.
      id: "prohor-pcinjski",
      mapPB: [42.314123, 21.886043, 42.311669, 21.878821],
      mapRoute: ["Granični prelaz Prohor Pčinjski", "Граничен премин Пелинце"],
      coords: [42.3132, 21.8824], name: "Prohor Pcinjski", from: "RS", to: "MK",
      pair: "Pelince (MK)", road: "233 / R1207", provider: "mapa saobraćaja",
      noCamera: true, feeds: [],
      intro: "Prohor Pčinjski je mali prelaz ka Severnoj Makedoniji, uz istoimeni manastir, i najčešća alternativa Preševu kad se tamo stvore kolone. Otvoren je 24 časa, ali samo za putnička i manja kombi vozila. Kamere nema — Gasolina ovde prikazuje procenu iz mape saobraćaja. Makedonska kontrola je oko kilometar južno od granice, pa računajte na dva zaustavljanja. Jedna ograda oko brojke: u 285 snimaka izlaznog smera (26.07–15.08.2026) granična policija je objavila tačno 60 minuta u tri četvrtine zapisa, i nijednom nijednu drugu vrednost. Vrednost koja se kroz tri nedelje ne pomeri ni jednom verovatnije je držana nego merena, pa je i ovde treba čitati kao orijentir, ne kao stanje na rampi.",
      introEn: "Prohor Pcinjski is a small crossing into North Macedonia next to the monastery of the same name, and the usual alternative to Presevo when queues build up there. Open 24 hours, but for cars and small vans only. There is no camera — Gasolina shows a traffic-map estimate instead. Macedonian control sits about a kilometre south of the border, so expect two stops. One caveat about the figure: across 285 outbound snapshots (26 July – 15 August 2026) the border police published exactly 60 minutes in three quarters of records, and never any other value. A number that does not move once in three weeks is more likely held than measured, so read it here as a rough marker rather than the state at the barrier.",
      wait: { putnicka: { ulaz: 30, izlaz: 30 }, teretna: { ulaz: 30, izlaz: 30 } },
    },
    {
      id: "gostun", mapRoute: ["Granični prelaz Gostun", "Granični prelaz Dobrakovo"], coords: [43.3, 19.66], name: "Gostun", from: "RS", to: "ME",
      pair: "Dobrakovo (MNE)", road: "E763", provider: "MUP Crne Gore",
      official: "http://kamere.mup.gov.me/kamere.php?kamere=Dobrakovo&lang=me",
      linkOnly: true, feeds: [],
      intro: "Gostun je prelaz ka Crnoj Gori na E763 naspram Dobrakova, na pravcu Nova Varoš – Bijelo Polje, i najkraća veza sa crnogorskim primorjem preko Sandžaka. U 664 snimka po smeru (24.06–15.08.2026) procena čekanja je postojala u svega 24 zapisa: 01.08. je granična policija objavila 60 minuta za izlaz i 50 za ulaz. Ostatak vremena stoji podrazumevanih 30 minuta, što nije merenje stanja. Za Gostun nema prijava vozača preko BorderAlarma niti koridora za merenje saobraćaja. Sopstvenu kameru ovde ne prikazujemo — otvara se zvanična kamera MUP-a Crne Gore, sa naznačenim izvorom.",
      introEn: "Gostun is the crossing into Montenegro on the E763 opposite Dobrakovo, on the Nova Varos – Bijelo Polje route, and the shortest link to the Montenegrin coast through the Sandzak. Across 664 snapshots per direction (24 June – 15 August 2026) a waiting estimate existed in just 24 records: on 1 August the border police published 60 minutes outbound and 50 inbound. The rest of the time the default 30 minutes stands, which is not a measurement of conditions. There are no driver reports via BorderAlarm for Gostun and no corridor for traffic measurement. We do not host a camera here — the official Montenegrin Ministry of the Interior camera opens instead, with the source credited.",
      wait: { putnicka: { ulaz: 30, izlaz: 30 }, teretna: { ulaz: 30, izlaz: 30 } },
    },
    {
      // ME->HR, ne dodiruje Srbiju - isti slucaj kao Bogorodica (MK->GR): AMSS/MUP RS
      // nema kako da prati cekanje ovde, pa nema wait praceenja. Crnogorski MUP ima
      // svoju kamera-stranicu (isti obrazac kao za Gostun), ali je to embed stranica sa
      // vise kamera, ne pojedinacan m3u8 link koji mozemo da ubacimo direktno - linkOnly.
      id: "debeli-brijeg", mapRoute: ["Granični prelaz Debeli Brijeg", "Granični prijelaz Karasovići"], coords: [42.4617, 18.535], name: "Debeli Brijeg", from: "ME", to: "HR",
      pair: "Karasovici (HR)", road: "Jadranska magistrala (E65)", provider: "MUP Crne Gore",
      official: "http://kamere.mup.gov.me/kamere.php?kamere=Debeli_brijeg",
      linkOnly: true, noWait: true, feeds: [],
      intro: "Debeli Brijeg je prelaz iz Crne Gore u Hrvatsku na Jadranskoj magistrali, naspram Karasovića, poslednja rampa pred Dubrovnik. Za ovaj prelaz namerno ne prikazujemo procenu čekanja: nije srpska granica, pa ga ne pokriva Uprava granične policije, a nijedan drugi izvor koji pratimo ne objavljuje procenu za njega. Umesto brojke koja bi zvučala uverljivo, ovde stoji zvanična kamera MUP-a Crne Gore i jasna napomena da se čekanje ne prati. Ako putujete ka Dubrovniku, sliku sa kamere kombinujte sa stanjem na Karasovićima na hrvatskoj strani, jer se kolona najčešće gradi tamo.",
      introEn: "Debeli Brijeg is the crossing from Montenegro into Croatia on the Adriatic highway, opposite Karasovici, the last barrier before Dubrovnik. For this crossing we deliberately show no waiting estimate: it is not a Serbian border, so it is not covered by the Serbian border police, and no other source we follow publishes an estimate for it. Instead of a figure that would merely sound convincing, you get the official Montenegrin Ministry of the Interior camera and a plain note that waiting is not tracked. If you are heading for Dubrovnik, read the camera together with conditions at Karasovici on the Croatian side, since the queue usually builds there.",
      wait: null,
    },
    {
      // MK->GR alternativa Bogorodici - bas prelaz na koji se preusmerava saobracaj
      // kad je Evzoni zakrcен. Isti obrazac kao Bogorodica: samo kamera (roads.org.mk /
      // neotel stream), bez pracenja cekanja (nije RS granica). Stream URL potvrdjen
      // rucno u browseru pre dodavanja (gvozdeno pravilo).
      id: "dojran",
      // Koridor kalibrisan 01.08.2026. Stare tacke su lezale 1.2-1.7 km od rampe
      // (kod pristanista u Star Dojranu), pa je Google rutao kroz seoske ulice i
      // davao rute krace od vazdusne linije - siguran znak da krajevi nisu tamo gde
      // mislimo. Nove tacke su same stanice, 1346 m, sto je u opsegu Kelebije (1274)
      // i Medzitlije (1425). mapPBin namerno NIJE dodat - selftest u granice_scraper
      // ima konzervirane TomTom odgovore samo za izlazni koridor. Ranije je
      // mapRoute nosio GRCKI oblik imena na
      // makedonskoj strani ("Дојрани"), pa bi rezervna mapa vodila u grcko selo.
      mapPB: [41.1705414, 22.7452727, 41.1771878, 22.7587158],
      pbId: ["0x14a9dd8bff8c70ab%3A0x1f9a5b0bf0240f1f", "0x14a9e78aebffdd95%3A0x6fdb4272043303e5"],
      mapRoute: ["Star Dojran Border Crossing", "Doirani Customs House"], coords: [41.1739, 22.7520], name: "Dojran", from: "MK", to: "GR",
      pair: "Doirani (GR)", road: "regionalni put (uz Dojransko jezero)", provider: "roads.org.mk",
      official: "https://roads.org.mk/en/road-network/live-webcast",
      noWait: true,
      feeds: [
        { label: "Kamera (granica)", dir: "out", src: "https://streaming1.neotel.net.mk/stream/dojran.m3u8" },
      ],
      intro: "Dojran je prelaz iz Severne Makedonije u Grčku uz istoimeno jezero, naspram Doiranija, i uobičajena alternativa Bogorodici kad se tamo stvore kolone. Čekanje ovde ne prikazujemo: nijedan izvor koji pratimo ne objavljuje procenu za ovaj prelaz. Vredi znati i ovo — u 290 zapisa saobraćajno merenje na izlaznom koridoru nije javilo apsolutno ništa, nijednom. To je jedini takav koridor na sajtu, i dobar podsetnik zašto nulu iz merenja ne tumačimo kao dokaz da je put prohodan. Ostaje kamera uživo, koja je ovde jedini stvaran podatak.",
      introEn: "Dojran is the crossing from North Macedonia into Greece beside the lake of the same name, opposite Doirani, and the usual alternative to Bogorodica when queues build up there. We show no waiting time here: no source we follow publishes an estimate for this crossing. One more thing worth knowing — across 290 records, traffic measurement on the outbound corridor reported absolutely nothing, not once. It is the only corridor on the site of which that is true, and a good reminder of why we do not read a zero from measurement as proof that the road is clear. What remains is the live camera, which here is the only real data.",
      wait: null,
    },
  ];

  function pairKey(a, b) { return [a, b].sort().join("-"); }
  function forPair(a, b) {
    const k = pairKey(a, b);
    return CROSSINGS.filter((c) => pairKey(c.from, c.to) === k);
  }
  function byId(id) { return CROSSINGS.find((c) => c.id === id) || null; }

  return { FLAG, CROSSINGS, forPair, byId, pairKey };
})();
