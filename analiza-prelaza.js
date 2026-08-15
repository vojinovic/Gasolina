#!/usr/bin/env node
/* PROFIL SVAKOG PRELAZA IZ SOPSTVENOG ARHIVA (15.08.2026)
 *
 * ZASTO POSTOJI: 26 landing stranica ima medijanu od 173 jedinstvene reci, a
 * mehanizam za jedinstven tekst (`intro` / `introEn` u borders-data.js) stoji
 * napisan za TACNO JEDAN prelaz. Da bi se napisalo dvanaest preostalih uvoda
 * koji nesto TVRDE, treba nam ono sto niko drugi nema: sopstveni arhiv.
 *
 * Ovaj alat NE PISE tekst. On vadi cinjenice iz kojih se tekst sme napisati,
 * i to tako da se svaka recenica moze proveriti nazad do broja.
 *
 * CISTO CITANJE. Ne pise nijedan fajl, ne commit-uje, ne dira sajt.
 *
 * Odluka se NE reimplementira - ucitava se kanonski wait-logic.v1.js, isti onaj
 * koji radi na sajtu. Ako bi se ovde pisala kopija pravila, profil bi opisivao
 * sajt koji ne postoji.
 *
 * Pokretanje IZ KORENA javnog repoa:
 *   node analiza-prelaza.js --selftest    provera racuna nad rucnim ulazima
 *   node analiza-prelaza.js               analiza nad git istorijom granice.json
 */
"use strict";
const fs = require("fs");
const vm = require("vm");
const { execFileSync } = require("child_process");

const KANON = "wait-logic.v1.js";

// Arhiv ide 24.06-15.08.2026, sto je CEO u letnjem racunanju vremena (UTC+2).
// Zato se lokalni sat racuna fiksnim pomerajem, a ne bibliotekom za zone: kad
// arhiv jednom predje 25.10., ovaj broj MORA da se zameni pravom konverzijom.
// Ranije je `git log --since` vec jednom tiho pojeo ceo dan zbog zone.
const POMERAJ_H = 2;
const DAN = ["nedelja", "ponedeljak", "utorak", "sreda", "cetvrtak", "petak", "subota"];

function ucitaj(src) {
  const ctx = { module: { exports: {} }, console };
  vm.runInNewContext(src, ctx, { filename: "wait-logic.v1.js" });
  const f = ctx.module.exports.procena;
  if (typeof f !== "function") throw new Error("kanonska datoteka ne izvozi procena()");
  return f;
}

function git(args) {
  return execFileSync("git", args, { maxBuffer: 1 << 28 }).toString();
}

/** Koridori i kamere iz ISTORIJSKE verzije borders-data.js. Blob iz stabla bas
 *  tog commita, ne po datumu: datum omasi kod rebase-a i naknadnog push-a, i to
 *  je vec jednom svrstalo pravo merenje od 11 min / 640 m u pogresnu kolonu. */
function konfigIz(text) {
  const kor = {}, kam = {};
  const delovi = text.split('id: "');
  for (let i = 1; i < delovi.length; i++) {
    const chunk = delovi[i];
    const cid = chunk.split('"')[0];
    const kraj = chunk.indexOf("wait:");
    const telo = kraj > 0 ? chunk.slice(0, kraj + 1) : chunk;
    kor[cid + "/izlaz"] = /mapPB:\s*\[/.test(telo);
    kor[cid + "/ulaz"] = /mapPBin:\s*\[/.test(telo);
    kam[cid + "/izlaz"] = /dir:\s*"out"[^}]*src:\s*"/.test(telo);
    kam[cid + "/ulaz"] = /dir:\s*"in"[^}]*src:\s*"/.test(telo);
  }
  return { kor, kam };
}

const kv = (niz, p) => {
  if (!niz.length) return null;
  const s = [...niz].sort((a, b) => a - b);
  return s[Math.min(s.length - 1, Math.floor(p * (s.length - 1) + 0.5))];
};

/** Prazan profil jednog pravca. */
function novProfil() {
  return {
    celija: 0, prvi: null, poslednji: null,
    stanja: {},                       // stanje -> broj celija
    brojevi: [],                      // sve prikazane krupne brojke
    najgore: { v: null, kada: null, src: null },
    izvori: {                         // koliko puta je izvor dao POZITIVNU vrednost
      amss: 0, amss30: 0, amssDrugo: new Set(),
      hu: 0, huVred: new Set(), mk: 0, mkVred: new Set(),
      ba: 0, user: 0,
    },
    tt: { koridor: false, odgovora: 0, nula: 0, pozitivnih: 0, najduzaKolona: 0 },
    kamera: false,
    poSatu: new Map(),                // lokalni sat -> {n, guzva}
    poDanu: new Map(),                // dan u nedelji -> {n, guzva}
  };
}

// Sta se racuna kao "guzva" za profil po satu: stanje koje covek cita kao
// "nije prohodno". Namerno UKLJUCUJE neizvesno i sukob - u oba slucaja sajt
// kaze da mirno nije potvrdjeno. NE ukljucuje "nema", jer odsustvo podatka
// nije gustina saobracaja nego rupa u izvorima.
const GUZVA = new Set(["broj", "prijavljeno", "kolona", "sukob", "neizvesno"]);
const PRAZNO = new Set(["nema"]);

function analiza() {
  const procena = ucitaj(fs.readFileSync(KANON, "utf8"));

  const log = git(["log", "--format=%H\t%cI", "--", "granice.json"])
    .split("\n").filter(Boolean).map((l) => l.split("\t")).reverse();
  console.log(`Commitova koji menjaju granice.json: ${log.length}`);

  const kfgKes = new Map();
  const videni = new Set();
  const prof = new Map();             // "cid/smer" -> profil
  let duplikata = 0, snapshotova = 0;

  for (const [sha, ts] of log) {
    let snap;
    try { snap = JSON.parse(git(["show", `${sha}:granice.json`])); } catch (e) { continue; }
    const sa = snap.scraped_at || ts;
    if (videni.has(sa)) { duplikata++; continue; }
    videni.add(sa); snapshotova++;

    let bdOid = null;
    try { bdOid = git(["rev-parse", `${sha}:borders-data.js`]).trim(); } catch (e) { bdOid = "NEMA"; }
    if (!kfgKes.has(bdOid)) {
      let t = "";
      if (bdOid !== "NEMA") { try { t = git(["cat-file", "blob", bdOid]); } catch (e) { t = ""; } }
      kfgKes.set(bdOid, konfigIz(t));
    }
    const { kor, kam } = kfgKes.get(bdOid);

    const d = new Date(sa);
    const lok = new Date(d.getTime() + POMERAJ_H * 3600 * 1000);
    const sat = lok.getUTCHours(), dan = lok.getUTCDay();

    for (const [cid, c] of Object.entries(snap.crossings || {})) {
      for (const smer of ["izlaz", "ulaz"]) {
        const k = cid + "/" + smer;
        if (!prof.has(k)) prof.set(k, novProfil());
        const p = prof.get(k);
        p.celija++;
        if (!p.prvi || sa < p.prvi) p.prvi = sa;
        if (!p.poslednji || sa > p.poslednji) p.poslednji = sa;
        p.koridorDef = p.tt.koridor = p.tt.koridor || !!kor[k];
        p.kamera = p.kamera || !!kam[k];

        // --- sirovi izvori, pre odluke -----------------------------------
        const pv = c.putnicka ? c.putnicka[smer] : null;
        if (pv != null) { if (pv === 30) p.izvori.amss30++; else if (pv > 0) { p.izvori.amss++; p.izvori.amssDrugo.add(pv); } }
        if (c.hu && c.hu[smer] != null && c.hu[smer] > 0) { p.izvori.hu++; p.izvori.huVred.add(c.hu[smer]); }
        const mkv = c.mk ? (smer === "izlaz" ? c.mk.vlez : c.mk.izlez) : null;
        if (mkv != null && mkv > 0) { p.izvori.mk++; p.izvori.mkVred.add(mkv); }
        if (c.mk && c.mk.opsto != null && c.mk.opsto > 0) { p.izvori.mk++; p.izvori.mkVred.add(c.mk.opsto); }
        if (c.ba && c.ba[smer] != null && c.ba[smer] > 0) p.izvori.ba++;
        if (c.user && c.user[smer] != null && c.user[smer] > 0) p.izvori.user++;

        const ttv = c.tt ? c.tt[smer] : null;
        const ttk = c.tt ? c.tt[smer + "_kolona_m"] : null;
        if (ttv != null) {
          p.tt.odgovora++;
          if (ttv === 0 && (ttk == null || ttk === 0)) p.tt.nula++; else p.tt.pozitivnih++;
        }
        if (ttk != null && ttk > p.tt.najduzaKolona) p.tt.najduzaKolona = ttk;

        // --- odluka (kanonska funkcija, ista koja radi na sajtu) ----------
        const e = procena(c, smer);
        p.stanja[e.stanje] = (p.stanja[e.stanje] || 0) + 1;
        if (e.v != null) {
          p.brojevi.push(e.v);
          if (p.najgore.v == null || e.v > p.najgore.v) p.najgore = { v: e.v, kada: sa, src: e.src || null };
        }

        for (const [mapa, kljuc] of [[p.poSatu, sat], [p.poDanu, dan]]) {
          if (!mapa.has(kljuc)) mapa.set(kljuc, { n: 0, guzva: 0, prazno: 0 });
          const o = mapa.get(kljuc);
          o.n++;
          if (GUZVA.has(e.stanje)) o.guzva++;
          if (PRAZNO.has(e.stanje)) o.prazno++;
        }
      }
    }
  }

  console.log(`Jedinstvenih snapshotova: ${snapshotova}   odbaceno duplikata: ${duplikata}`);
  const ukupno = [...prof.values()].reduce((a, p) => a + p.celija, 0);
  console.log(`Celija (prelaz x smer x snapshot): ${ukupno}\n`);

  const kljucevi = [...prof.keys()].sort();
  const izlaz = {};

  for (const k of kljucevi) {
    const p = prof.get(k);
    const n = p.celija;
    const pct = (x) => (100 * x / n).toFixed(1) + "%";
    const st = Object.entries(p.stanja).sort((a, b) => b[1] - a[1]);

    // sat i dan sa najvecim udelom "nije prohodno" - samo ako ima dovoljno uzorka
    const najgoriSat = [...p.poSatu].filter(([, o]) => o.n >= 20)
      .sort((a, b) => (b[1].guzva / b[1].n) - (a[1].guzva / a[1].n))[0];
    const najmirnijiSat = [...p.poSatu].filter(([, o]) => o.n >= 20)
      .sort((a, b) => (a[1].guzva / a[1].n) - (b[1].guzva / b[1].n))[0];
    const najgoriDan = [...p.poDanu].filter(([, o]) => o.n >= 40)
      .sort((a, b) => (b[1].guzva / b[1].n) - (a[1].guzva / a[1].n))[0];

    console.log("=".repeat(78));
    console.log(`${k}    ${n} celija    ${p.prvi ? p.prvi.slice(0, 10) : "-"} .. ${p.poslednji ? p.poslednji.slice(0, 10) : "-"}`);
    console.log(`  kamera za ovaj smer: ${p.kamera ? "DA" : "ne"}    TomTom koridor: ${p.tt.koridor ? "DA" : "NE"}`);
    console.log(`  stanja: ${st.map(([s, c]) => `${s} ${pct(c)}`).join(" · ")}`);
    if (p.brojevi.length) {
      console.log(`  prikazana brojka u ${pct(p.brojevi.length)} celija: ` +
        `medijana ${kv(p.brojevi, 0.5)} min · p75 ${kv(p.brojevi, 0.75)} · p90 ${kv(p.brojevi, 0.9)} min`);
      console.log(`  najgore zabelezeno: ${p.najgore.v} min (${p.najgore.kada}, izvor ${p.najgore.src || "-"})`);
    } else {
      console.log(`  nijedna krupna brojka nije prikazana u celom periodu`);
    }
    console.log(`  izvori (broj celija sa POZITIVNOM vrednoscu):`);
    console.log(`     AMSS: tacno 30 u ${pct(p.izvori.amss30)}, druga vrednost ${p.izvori.amss} ` +
      `${p.izvori.amssDrugo.size ? "(" + [...p.izvori.amssDrugo].sort((a, b) => a - b).join(", ") + ")" : ""}`);
    console.log(`     police.hu: ${p.izvori.hu}${p.izvori.huVred.size ? " (" + [...p.izvori.huVred].sort((a, b) => a - b).join(", ") + ")" : ""}` +
      `   AMSM: ${p.izvori.mk}${p.izvori.mkVred.size ? " (" + [...p.izvori.mkVred].sort((a, b) => a - b).join(", ") + ")" : ""}`);
    console.log(`     prijave vozaca: BorderAlarm ${p.izvori.ba}, sopstvena forma ${p.izvori.user}`);
    if (p.tt.koridor) {
      const o = p.tt.odgovora;
      console.log(`  TomTom: ${o} odgovora, nula u ${o ? (100 * p.tt.nula / o).toFixed(1) + "%" : "-"}, ` +
        `najduza izmerena kolona ${p.tt.najduzaKolona} m`);
      if (o && p.tt.pozitivnih === 0)
        console.log(`     MRTAV KORIDOR: nijedan pozitivan signal u ${o} odgovora`);
    } else {
      console.log(`  TomTom: koridor nije definisan za ovaj smer - merenja nema`);
    }
    if (najgoriSat) console.log(`  najgori sat: ${String(najgoriSat[0]).padStart(2, "0")}h ` +
      `(${(100 * najgoriSat[1].guzva / najgoriSat[1].n).toFixed(0)}% celija nije prohodno)` +
      (najmirnijiSat ? `   najmirniji: ${String(najmirnijiSat[0]).padStart(2, "0")}h (${(100 * najmirnijiSat[1].guzva / najmirnijiSat[1].n).toFixed(0)}%)` : ""));
    if (najgoriDan) console.log(`  najgori dan: ${DAN[najgoriDan[0]]} ` +
      `(${(100 * najgoriDan[1].guzva / najgoriDan[1].n).toFixed(0)}%)`);

    izlaz[k] = {
      celija: n, od: p.prvi, do: p.poslednji, kamera: p.kamera, koridor: p.tt.koridor,
      stanja: p.stanja, medijana: kv(p.brojevi, 0.5), p90: kv(p.brojevi, 0.9),
      najgore: p.najgore, ttNula: p.tt.odgovora ? p.tt.nula / p.tt.odgovora : null,
      ttOdgovora: p.tt.odgovora, najduzaKolona: p.tt.najduzaKolona,
      amss30: p.izvori.amss30, amssDrugo: [...p.izvori.amssDrugo].sort((a, b) => a - b),
      hu: p.izvori.hu, mk: p.izvori.mk, ba: p.izvori.ba, user: p.izvori.user,
      najgoriSat: najgoriSat ? najgoriSat[0] : null,
      najgoriDan: najgoriDan ? DAN[najgoriDan[0]] : null,
    };
  }

  console.log("\n" + "=".repeat(78));
  console.log("MASINSKI CITLJIVO (za pisanje uvoda):\n");
  console.log(JSON.stringify(izlaz, null, 1));
}

// ---------------------------------------------------------------------------
// SELFTEST - racun mora da se proveri pre nego sto se iz njega pisu tvrdnje
// ---------------------------------------------------------------------------
function selftest() {
  let pao = 0;
  const T = (opis, uslov) => { if (uslov) console.log(`  [OK  ] ${opis}`); else { pao++; console.log(`  [PAO ] ${opis}`); } };

  T("percentil: medijana [1,2,3] = 2", kv([1, 2, 3], 0.5) === 2);
  // p90 nad deset vrednosti je DEVETA, ne deseta. Prva verzija ovog testa je
  // ocekivala 10 i pala - greska je bila u ocekivanju, ne u racunu. Ostavljeno
  // zapisano jer je to tacno vrsta zabune zbog koje bi se posle u tekstu
  // uvoda pojavila najgora vrednost predstavljena kao "devedeseti percentil".
  T("percentil: p90 od 1..10 = 9", kv([1,2,3,4,5,6,7,8,9,10], 0.9) === 9);
  T("percentil: p90 nije maksimum", kv([1,2,3,4,5,6,7,8,9,10], 0.9) !== 10);
  T("percentil: prazan niz -> null", kv([], 0.5) === null);

  // Lokalni sat: 22:30 UTC je 00:30 po nasem vremenu SLEDECEG dana. Ako se ovo
  // pokvari, "najgori sat" bi pokazivao pogresno doba dana - a bas to je
  // podatak zbog kog covek menja vreme polaska.
  // 04.07.2026. je SUBOTA (prva verzija testa je tvrdila petak - moja greska,
  // ne racunova; zato je dan sada i eksplicitno proveren pre pomeraja).
  const d = new Date("2026-07-04T22:30:00+00:00");
  T("kontrola: 04.07.2026 u UTC je subota", DAN[d.getUTCDay()] === "subota");
  const lok = new Date(d.getTime() + POMERAJ_H * 3600 * 1000);
  T("lokalni sat: 22:30 UTC -> 00h", lok.getUTCHours() === 0);
  T("lokalni dan: subota 22:30 UTC -> nedelja", DAN[lok.getUTCDay()] === "nedelja");

  // konfigIz mora da razlikuje smerove: Bogorodica ima kameru samo za izlaz.
  const { kor, kam } = konfigIz(`
    { id: "bogorodica", mapPB: [1,2,3,4], mapPBin: [5,6,7,8],
      feeds: [ { label: "x", dir: "out", src: "https://x.m3u8" } ], wait: null },
    { id: "gostun", feeds: [], wait: null },
  `);
  T("konfigIz: bogorodica ima kameru za izlaz", kam["bogorodica/izlaz"] === true);
  T("konfigIz: bogorodica nema kameru za ulaz", kam["bogorodica/ulaz"] === false);
  T("konfigIz: bogorodica ima oba koridora", kor["bogorodica/izlaz"] && kor["bogorodica/ulaz"]);
  T("konfigIz: gostun nema koridor", !kor["gostun/izlaz"] && !kor["gostun/ulaz"]);

  // Kanonska funkcija mora da se ucita i da radi - inace profil opisuje nista.
  const procena = ucitaj(fs.readFileSync(KANON, "utf8"));
  const e = procena({ putnicka: { ulaz: 45 }, tt: {} }, "ulaz");
  T("kanonska funkcija radi (45 min -> broj:45)", e.stanje === "broj" && e.v === 45);

  console.log(pao ? `\nPALO: ${pao}\n` : "\nSelftest prolazi.\n");
  process.exit(pao ? 1 : 0);
}

if (process.argv.includes("--selftest")) selftest();
else analiza();
