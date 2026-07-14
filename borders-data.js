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
  };

  const CROSSINGS = [
    {
      id: "gradina", name: "Gradina", from: "RS", to: "BG",
      pair: "Kalotina (BG)", road: "E80", provider: "AMSS",
      official: "https://kamere.amss.org.rs/",
      feeds: [
        { label: "Ulaz", dir: "in",  src: "https://kamere.amss.org.rs/gradina1/gradina1.m3u8" },
        { label: "Izlaz", dir: "out", src: "https://kamere.amss.org.rs/gradina2/gradina2.m3u8" },
      ],
      wait: { putnicka: { ulaz: 30, izlaz: 30 }, teretna: { ulaz: 30, izlaz: 30 } },
    },
    {
      id: "horgos", name: "Horgos", from: "RS", to: "HU",
      pair: "Roszke (HU)", road: "E75", provider: "AMSS",
      official: "https://kamere.amss.org.rs/",
      feeds: [
        { label: "Ulaz", dir: "in",  src: "https://kamere.amss.org.rs/horgos1/horgos1.m3u8" },
        { label: "Izlaz", dir: "out", src: "https://kamere.amss.org.rs/horgos2/horgos2.m3u8" },
      ],
      wait: { putnicka: { ulaz: 30, izlaz: 30 }, teretna: { ulaz: 30, izlaz: 30 } },
    },
    {
      id: "kelebija", name: "Kelebija", from: "RS", to: "HU",
      pair: "Tompa (HU)", road: "M17/E75", provider: "MUP",
      official: "https://kamere.amss.org.rs/",
      feeds: [
        { label: "Ulaz", dir: "in",  src: "https://kamere.mup.gov.rs:4443/Kelebija/kelebija1.m3u8" },
        { label: "Izlaz", dir: "out", src: "https://kamere.mup.gov.rs:4443/Kelebija/kelebija2.m3u8" },
      ],
      wait: { putnicka: { ulaz: 30, izlaz: 30 }, teretna: { ulaz: 30, izlaz: 30 } },
    },
    {
      id: "batrovci", name: "Batrovci", from: "RS", to: "HR",
      pair: "Bajakovo (HR)", road: "E70", provider: "AMSS",
      official: "https://kamere.amss.org.rs/",
      feeds: [
        { label: "Ulaz", dir: "in",  src: "https://kamere.amss.org.rs/batrovci1/batrovci1.m3u8" },
        { label: "Izlaz", dir: "out", src: "https://kamere.amss.org.rs/batrovci2/batrovci2.m3u8" },
      ],
      wait: { putnicka: { ulaz: 30, izlaz: 30 }, teretna: { ulaz: 30, izlaz: 300 } },
    },
    {
      id: "presevo", name: "Presevo", from: "RS", to: "MK",
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
      id: "bogorodica", name: "Bogorodica", from: "MK", to: "GR",
      pair: "Evzoni (GR)", road: "E75", provider: "roads.org.mk",
      official: "https://alltrafficcams.com/live/border-crossings/north-macedonia/greece/bogorodica-evzonoi/",
      noWait: true,
      feeds: [
        { label: "Izlaz (ka Grckoj)", dir: "out", src: "https://streaming1.neotel.net.mk/stream/bogorodica.m3u8" },
      ],
      wait: null,
    },
    {
      id: "sremska-raca", name: "Sremska Raca", from: "RS", to: "BA",
      pair: "Raca (BiH)", road: "E70", provider: "MUP",
      official: "https://kamere.amss.org.rs/",
      feeds: [
        { label: "Ulaz", dir: "in",  src: "https://kamere.mup.gov.rs:4443/SremskaRaca/sremskaraca1.m3u8" },
        { label: "Izlaz", dir: "out", src: "https://kamere.mup.gov.rs:4443/SremskaRaca/sremskaraca2.m3u8" },
      ],
      wait: { putnicka: { ulaz: 30, izlaz: 30 }, teretna: { ulaz: 30, izlaz: 240 } },
    },
    {
      id: "spiljani", name: "Spiljani", from: "RS", to: "ME",
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
      id: "gostun", name: "Gostun", from: "RS", to: "ME",
      pair: "Dobrakovo (MNE)", road: "E763", provider: "MUP Crne Gore",
      official: "http://kamere.mup.gov.me/kamere.php?kamere=Dobrakovo&lang=me",
      linkOnly: true, feeds: [],
      wait: { putnicka: { ulaz: 30, izlaz: 30 }, teretna: { ulaz: 30, izlaz: 30 } },
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
