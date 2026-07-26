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
      wait: { putnicka: { ulaz: 30, izlaz: 30 }, teretna: { ulaz: 30, izlaz: 30 } },
    },
    {
      id: "kelebija", mapPBin: [46.1693418, 19.5574239, 46.1670921, 19.5612977], mapPB: [46.1642685, 19.5626338, 46.1704754, 19.5563793], mapRoute: ["Granični prelaz Kelebija", "Tompa határátkelőhely"], coords: [46.191, 19.541], name: "Kelebija", from: "RS", to: "HU",
      pair: "Tompa (HU)", road: "M17/E75", provider: "MUP",
      official: "https://kamere.amss.org.rs/",
      feeds: [
        { label: "Ulaz", dir: "in",  src: "https://kamere.mup.gov.rs:4443/Kelebija/kelebija1.m3u8" },
        { label: "Izlaz", dir: "out", src: "https://kamere.mup.gov.rs:4443/Kelebija/kelebija2.m3u8" },
      ],
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
      wait: { putnicka: { ulaz: 30, izlaz: 30 }, teretna: { ulaz: 30, izlaz: 30 } },
    },
    {
      id: "bogorodica", pbId: ["", "0x135626c88b4d3907%3A0xc81c83269be4c289"], pbIdIn: ["0x135626c88b4d3907%3A0xc81c83269be4c289", "0x135626c9f9dda211%3A0x5d10bb96bd3d13f7"], mapPBin: [41.1276257, 22.5516536, 41.134253, 22.5490008], mapPB: [41.135969, 22.5464805, 41.1276257, 22.5516536], mapRoute: ["Граничен премин Богородица", "Border Crossing Point of Evzoni"], coords: [41.1264, 22.5092], name: "Bogorodica", from: "MK", to: "GR",
      pair: "Evzoni (GR)", road: "E75", provider: "roads.org.mk",
      official: "https://alltrafficcams.com/live/border-crossings/north-macedonia/greece/bogorodica-evzonoi/",
      noWait: true,
      feeds: [
        { label: "Izlaz (ka Grckoj)", dir: "out", src: "https://streaming1.neotel.net.mk/stream/bogorodica.m3u8" },
      ],
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
      intro: "Prohor Pčinjski je mali prelaz ka Severnoj Makedoniji, uz istoimeni manastir, i najčešća alternativa Preševu kad se tamo stvore kolone. Otvoren je 24 časa, ali samo za putnička i manja kombi vozila. Kamere nema — Gasolina ovde prikazuje procenu iz mape saobraćaja. Makedonska kontrola je oko kilometar južno od granice, pa računajte na dva zaustavljanja.",
      introEn: "Prohor Pcinjski is a small crossing into North Macedonia next to the monastery of the same name, and the usual alternative to Presevo when queues build up there. Open 24 hours, but for cars and small vans only. There is no camera — Gasolina shows a traffic-map estimate instead. Macedonian control sits about a kilometre south of the border, so expect two stops.",
      wait: { putnicka: { ulaz: 30, izlaz: 30 }, teretna: { ulaz: 30, izlaz: 30 } },
    },
    {
      id: "gostun", mapRoute: ["Granični prelaz Gostun", "Granični prelaz Dobrakovo"], coords: [43.3, 19.66], name: "Gostun", from: "RS", to: "ME",
      pair: "Dobrakovo (MNE)", road: "E763", provider: "MUP Crne Gore",
      official: "http://kamere.mup.gov.me/kamere.php?kamere=Dobrakovo&lang=me",
      linkOnly: true, feeds: [],
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
      wait: null,
    },
    {
      // MK->GR alternativa Bogorodici - bas prelaz na koji se preusmerava saobracaj
      // kad je Evzoni zakrcен. Isti obrazac kao Bogorodica: samo kamera (roads.org.mk /
      // neotel stream), bez pracenja cekanja (nije RS granica). Stream URL potvrdjen
      // rucno u browseru pre dodavanja (gvozdeno pravilo).
      id: "dojran", mapPB: [41.1821, 22.7580, 41.1726, 22.7594], mapRoute: ["Граничен премин Дојрани", "Doirani Border Station"], coords: [41.22, 22.72], name: "Dojran", from: "MK", to: "GR",
      pair: "Doirani (GR)", road: "regionalni put (uz Dojransko jezero)", provider: "roads.org.mk",
      official: "https://roads.org.mk/en/road-network/live-webcast",
      noWait: true,
      feeds: [
        { label: "Kamera (granica)", dir: "out", src: "https://streaming1.neotel.net.mk/stream/dojran.m3u8" },
      ],
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
