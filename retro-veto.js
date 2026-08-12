#!/usr/bin/env node
/* RETROSPEKTIVNI TEST: sta bi se promenilo da TomTom-ova nula vise ne brise
   prijavu vozaca.

   CISTO CITANJE. Ne pise nijedan fajl, ne commit-uje, ne dira sajt.

   Odluka se NE reimplementira. Ucitava se kanonski wait-logic.v1.js, a
   varijante nastaju STRING-ZAKRPOM nad njegovim izvorom. Svaka zakrpa se
   ispisuje doslovno i pada ako se ne primeni, da nema tihe divergencije.

   Pokretanje:
     node retro-veto.js --selftest     provera samih zakrpa nad rucnim ulazima
     node retro-veto.js                analiza nad git istorijom granice.json
*/
"use strict";
const fs = require("fs");
const vm = require("vm");
const { execFileSync } = require("child_process");

const KANON = "wait-logic.v1.js";

// ---------------------------------------------------------------------------
// VARIJANTE
// ---------------------------------------------------------------------------
// Sidro: tacan tekst iz kanonske datoteke. Ako se promeni, sve pada odmah.
const SIDRO_VETO =
`      if (v >= BA_PROVERA_MIN && merenjeMirno) baOsporen = v;
      else cands.push({v, src: "ba", tip: "prijava"});`;

const SIDRO_KORAK1 =
`  if (baOsporen != null && !zvanicniPostoji)
    return {stanje: "proveri", baOsporen, kolona, dugaKolona, ttMin};`;

const SIDRO_KORAK2 =
`    if (kratkoZvanicno && best.tip === "prijava" && best.v >= BA_PROVERA_MIN)
      return {stanje: "proveri", baOsporen: best.v, kolona, dugaKolona, ttMin};`;

const SIDRO_KORAK4 =
`    if (best.tip === "prijava")
      return {stanje: "prijavljeno", v: best.v, src: best.src, kolona, dugaKolona, ttMin};`;

function zameni(src, sidro, novo, ime) {
  const n = src.split(sidro).length - 1;
  if (n !== 1) throw new Error(`zakrpa "${ime}": sidro nadjeno ${n} puta, ocekivano 1`);
  return src.replace(sidro, novo);
}

const VARIJANTE = {
  // Osnova: kanonska datoteka bez ijedne izmene. Ovo je "pre".
  OSNOVA: (src) => src,

  // V1 - veto se uklanja. Nula nikad ne dira prijavu.
  V1_BEZ_VETA: (src) =>
    zameni(src, SIDRO_VETO,
`      cands.push({v, src: "ba", tip: "prijava"});   // V1: veto uklonjen`,
      "V1"),

  // V2 - veto vazi samo na koridorima koji su istorijski dokazali da umeju da
  // izmere guzvu. Zadrzano SAMO radi poredjenja: trazi da kanonska funkcija zna
  // IDENTITET koridora, koji joj danas niko ne prosledjuje (granice.json nema
  // `id` unutar zapisa prelaza). Test ga ubacuje kao c.__id - to je merna
  // proteza, ne predlog za produkciju.
  V2_VETO_PO_KORIDORU: (src) =>
    zameni(src, SIDRO_VETO,
`      const __k = (c.__id || "") + "/" + dirKey;
      const __pouzdan = ["batrovci/izlaz","batrovci/ulaz","gradina/izlaz",
                         "horgos/izlaz","horgos/ulaz"].indexOf(__k) !== -1;
      if (v >= BA_PROVERA_MIN && merenjeMirno && __pouzdan) baOsporen = v;
      else cands.push({v, src: "ba", tip: "prijava"});`,
      "V2"),

  // V3 - veto ne brise prijavu nego pravi NEIZVESNOST.
  //   * prijava ostaje kandidat, pa vise ne nestaje
  //   * ali nosi oznaku `nepotvrdjena`: ako pobedi, NE daje krupnu brojku
  //   * ako uz nju postoji ZVANICNA procena, ona ostaje krupna (kao u
  //     source_conflict modelu), a prijava ide kao napomena "znatno duze".
  //     Zato "neizvesno" nosi `niza` (zvanicni) i `visa` (prijava), a NE `v` -
  //     isto kao "sukob": cim postoji `v`, svaki prikaz ga ispise kao naslov
  //     i time proglasi pobednika.
  //   * korak 1 (osporena prijava bez zvanicnog -> "proveri") se gasi, jer
  //     prijava sada ucestvuje u izboru
  //   * duga kolona i dalje nosi "kolona": merenjeMirno trazi !dugaKolona, pa
  //     se `nepotvrdjena` i duga kolona ne mogu pojaviti zajedno
  V3_NEIZVESNOST: (src) => {
    let s = zameni(src, SIDRO_VETO,
`      if (v >= BA_PROVERA_MIN && merenjeMirno) {
        baOsporen = v;                                  // V3: samo evidencija
        cands.push({v, src: "ba", tip: "prijava", nepotvrdjena: true});
      } else cands.push({v, src: "ba", tip: "prijava"});`, "V3-veto");
    s = zameni(s, SIDRO_KORAK1,
`  // V3: korak 1 ugasen - prijava ostaje kandidat, pa nema sta da preuzme.`, "V3-korak1");
    s = zameni(s, SIDRO_KORAK4,
`    if (best.tip === "prijava" && best.nepotvrdjena) {
      const zvNaj = zvanicniSvi.length
        ? zvanicniSvi.reduce((a, b) => b.v > a.v ? b : a) : null;
      return {stanje: "neizvesno", niza: zvNaj, visa: {v: best.v, src: best.src},
              kolona, dugaKolona, ttMin};
    }
    if (best.tip === "prijava")
      return {stanje: "prijavljeno", v: best.v, src: best.src, kolona, dugaKolona, ttMin};`,
      "V3-korak4");
    return s;
  },

  // V3B - V3 plus KORAK 2 sveden na isti oblik.
  // Korak 2 vec opisuje istu semantiku ("zvanicni kaze kratko, vozac kaze dugo,
  // nema osnova za pobednika"), samo starijim izlazom koji gubi OBA podatka.
  // Bez ovoga bi postojala dva razlicita prikaza za istu vrstu neizvesnosti, i
  // ostala bi regresija broj:60 -> proveri koju retro test vidi u sve tri
  // varijante.
  //
  // PAZI NA IMENILAC: ovo NIJE rep. Mereno nad golden fixture-om, korak 2 nosi
  // otprilike POLOVINU ukupnog zahvata (41 kombinacija naspram 41). I `niza` je
  // tu najcesce PRAZNO: `kratkoZvanicno` znaci da je zvanicni javio NULU, a nula
  // ne ulazi u zvanicniSvi. Oblik je dakle obicno neizvesno[-<->N].
  V3B_SA_KORAKOM2: (src) => {
    let s = VARIJANTE.V3_NEIZVESNOST(src);
    return zameni(s, SIDRO_KORAK2,
`    if (kratkoZvanicno && best.tip === "prijava" && best.v >= BA_PROVERA_MIN) {
      const zvNaj = zvanicniSvi.length
        ? zvanicniSvi.reduce((a, b) => b.v > a.v ? b : a) : null;
      return {stanje: "neizvesno", niza: zvNaj, visa: {v: best.v, src: best.src},
              kolona, dugaKolona, ttMin};
    }`, "V3B-korak2");
  },
};

function ucitaj(src) {
  const ctx = { module: { exports: {} }, console };
  vm.runInNewContext(src, ctx, { filename: "wait-logic.variant.js" });
  const f = ctx.module.exports.procena;
  if (typeof f !== "function") throw new Error("varijanta ne izvozi procena()");
  return f;
}

function sviProcena(kanonSrc) {
  const out = {};
  for (const [ime, patch] of Object.entries(VARIJANTE)) out[ime] = ucitaj(patch(kanonSrc));
  return out;
}

// ---------------------------------------------------------------------------
// SELFTEST
// ---------------------------------------------------------------------------
function selftest(kanonSrc) {
  const P = sviProcena(kanonSrc);
  let pao = 0, proslo = 0;
  const T = (opis, c, dir, ocek) => {
    for (const [v, e] of Object.entries(ocek)) {
      const r = P[v]({ ...c }, dir);
      const dobio = r.v != null ? r.stanje + ":" + r.v
        : (r.niza || r.visa)
          ? r.stanje + "[" + (r.niza ? r.niza.v : "-") + "<->" + (r.visa ? r.visa.v : "-") + "]"
          : r.stanje;
      if (dobio !== e) { pao++; console.log(`  [PAO ] ${opis} / ${v}: ocekivano ${e}, dobijeno ${dobio}`); }
      else proslo++;
    }
  };

  // 1. Velika prijava + TomTom nula + BEZ zvanicnog izvora (AMSS tacno 30).
  //    Osnova brise prijavu i salje na kameru. V1 je proglasava naslovom.
  //    V3 je zadrzava, ali kao neizvesnost.
  T("velika prijava, nula, bez zvanicnog",
    { putnicka: { ulaz: 30, izlaz: 30 }, ba: { ulaz: 240 }, tt: { ulaz: 0, ulaz_kolona_m: 0 } },
    "ulaz",
    { OSNOVA: "proveri", V1_BEZ_VETA: "prijavljeno:240", V3_NEIZVESNOST: "neizvesno[-<->240]" });

  // 2. Velika prijava + DUGA KOLONA. Veto ne sme ni da se okine (merenjeMirno
  //    trazi !dugaKolona), pa sve varijante moraju biti iste.
  T("velika prijava, duga kolona",
    { putnicka: { ulaz: 30 }, ba: { ulaz: 240 }, tt: { ulaz: 2, ulaz_kolona_m: 800 } },
    "ulaz",
    { OSNOVA: "prijavljeno:240", V1_BEZ_VETA: "prijavljeno:240", V3_NEIZVESNOST: "prijavljeno:240" });

  // 3. Velika prijava + NEMA TomToma. Veto se ne okida nigde.
  T("velika prijava, nema merenja",
    { putnicka: { ulaz: 30 }, ba: { ulaz: 240 }, tt: { ulaz: null, ulaz_kolona_m: null } },
    "ulaz",
    { OSNOVA: "prijavljeno:240", V1_BEZ_VETA: "prijavljeno:240", V3_NEIZVESNOST: "prijavljeno:240" });

  // 4. Velika prijava + nula + ZVANICNI 80 (odnos 3x) -> sukob se okida PRE
  //    veta, u svim varijantama isto. Veto tu nikad nije ni radio.
  T("sukob izvora ima prednost",
    { putnicka: { ulaz: 80 }, ba: { ulaz: 240 }, tt: { ulaz: 0, ulaz_kolona_m: 0 } },
    "ulaz",
    { OSNOVA: "sukob[80<->240]", V1_BEZ_VETA: "sukob[80<->240]", V3_NEIZVESNOST: "sukob[80<->240]" });

  // 5. Velika prijava + nula + ZVANICNI 120 (odnos 2x, ispod praga sukoba).
  //    Osnova: prijava izbacena, zvanicni nosi naslov. V3: prijava je veca,
  //    pa pobedjuje - ali kao neizvesnost, ne kao brojka.
  T("zvanicni ispod praga sukoba",
    { putnicka: { ulaz: 120 }, ba: { ulaz: 200 }, tt: { ulaz: 0, ulaz_kolona_m: 0 } },
    "ulaz",
    { OSNOVA: "broj:120", V1_BEZ_VETA: "prijavljeno:200", V3_NEIZVESNOST: "neizvesno[120<->200]" });

  // 5b. ZVANICNI je VECI od prijave. Prijava ionako ne bi bila naslov, pa
  //     nijedna varijanta ne sme nista da promeni.
  T("zvanicni veci od prijave",
    { putnicka: { ulaz: 300 }, ba: { ulaz: 130 }, tt: { ulaz: 0, ulaz_kolona_m: 0 } },
    "ulaz",
    { OSNOVA: "broj:300", V1_BEZ_VETA: "broj:300", V3_NEIZVESNOST: "broj:300" });

  // 5c. KORAK 2: zvanicni javlja NULU (kratkoZvanicno), vozac 240.
  //     Veto se ne okida (nema TomToma), pa V1 i V3 daju isto sto i osnova -
  //     "proveri". Tek V3B to svodi na isti oblik neizvesnosti.
  //     `niza` je prazno jer nula ne ulazi u zvanicniSvi.
  T("korak 2: zvanicni javlja nulu, vozac 240",
    { putnicka: { ulaz: 30 }, hu: { ulaz: 0 }, ba: { ulaz: 240 }, tt: { ulaz: null } },
    "ulaz",
    { OSNOVA: "proveri", V1_BEZ_VETA: "proveri", V3_NEIZVESNOST: "proveri",
      V3B_SA_KORAKOM2: "neizvesno[-<->240]" });

  // 5d. KORAK 2 uz DUGU KOLONU. U fixture-u postoji 13 takvih slucajeva:
  //     kolona potvrdjuje da guzva POSTOJI, samo prijavljeno trajanje nije
  //     potvrdjeno. Zato ime `driverReportUncorroborated` ne bi bilo tacno.
  T("korak 2 uz dugu kolonu",
    { putnicka: { ulaz: 30 }, hu: { ulaz: 0 }, ba: { ulaz: 240 },
      tt: { ulaz: 14, ulaz_kolona_m: 752 } },
    "ulaz",
    { OSNOVA: "proveri", V3B_SA_KORAKOM2: "neizvesno[-<->240]" });

  // 6. MALA prijava (ispod BA_PROVERA_MIN) - veto se ne tice nje.
  T("mala prijava",
    { putnicka: { ulaz: 30 }, ba: { ulaz: 40 }, tt: { ulaz: 0, ulaz_kolona_m: 0 } },
    "ulaz",
    { OSNOVA: "prijavljeno:40", V1_BEZ_VETA: "prijavljeno:40", V3_NEIZVESNOST: "prijavljeno:40" });

  // 7. V2 na POUZDANOM koridoru mora da se ponasa kao osnova, a na
  //    nepouzdanom kao V1.
  T("V2 na pouzdanom (gradina/izlaz)",
    { __id: "gradina", putnicka: { izlaz: 30 }, ba: { izlaz: 240 }, tt: { izlaz: 0, izlaz_kolona_m: 0 } },
    "izlaz", { V2_VETO_PO_KORIDORU: "proveri" });
  T("V2 na nepouzdanom (bogorodica/ulaz)",
    { __id: "bogorodica", putnicka: { ulaz: 30 }, ba: { ulaz: 240 }, tt: { ulaz: 0, ulaz_kolona_m: 0 } },
    "ulaz", { V2_VETO_PO_KORIDORU: "prijavljeno:240" });

  // 8. Nijedan izvor - sve varijante isto.
  T("nema nicega",
    { putnicka: { ulaz: 30 }, tt: { ulaz: 0, ulaz_kolona_m: 0 } },
    "ulaz",
    { OSNOVA: "nema", V1_BEZ_VETA: "nema", V3_NEIZVESNOST: "nema" });

  console.log(`\nSELFTEST: ${proslo} provera proslo, ${pao} palo.`);
  return pao === 0;
}

// ---------------------------------------------------------------------------
// ANALIZA NAD ISTORIJOM
// ---------------------------------------------------------------------------
function git(args) {
  return execFileSync("git", args, { maxBuffer: 1 << 28 }).toString();
}

// koridori i kamere iz ISTORIJSKE verzije borders-data.js (blob iz stabla
// bas tog commita - ne po datumu, jer datum omasi kod rebase-a i naknadnog pusha)
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
    // kamera po smeru: feed sa dir "out" (izlaz) ili "in" (ulaz) koji ima src
    kam[cid + "/izlaz"] = /dir:\s*"out"[^}]*src:\s*"/.test(telo);
    kam[cid + "/ulaz"] = /dir:\s*"in"[^}]*src:\s*"/.test(telo);
  }
  return { kor, kam };
}

function analiza(kanonSrc) {
  const P = sviProcena(kanonSrc);
  const IMENA = Object.keys(VARIJANTE).filter((x) => x !== "OSNOVA");

  const log = git(["log", "--format=%H\t%cI", "--", "granice.json"])
    .split("\n").filter(Boolean).map((l) => l.split("\t")).reverse();
  console.log(`Commitova koji menjaju granice.json: ${log.length}`);

  const kfgKes = new Map();
  const zapisi = [];
  const videni = new Set();
  let duplikata = 0;

  for (const [sha, ts] of log) {
    let snap;
    try { snap = JSON.parse(git(["show", `${sha}:granice.json`])); } catch (e) { continue; }
    const sa = snap.scraped_at || ts;
    if (videni.has(sa)) { duplikata++; continue; }
    videni.add(sa);

    let bdOid = null;
    try { bdOid = git(["rev-parse", `${sha}:borders-data.js`]).trim(); } catch (e) { bdOid = "NEMA"; }
    if (!kfgKes.has(bdOid)) {
      let t = "";
      if (bdOid !== "NEMA") { try { t = git(["cat-file", "blob", bdOid]); } catch (e) { t = ""; } }
      kfgKes.set(bdOid, konfigIz(t));
    }
    const { kor, kam } = kfgKes.get(bdOid);

    for (const [cid, c] of Object.entries(snap.crossings || {})) {
      for (const smer of ["izlaz", "ulaz"]) {
        zapisi.push({ sa, cid, smer, c, korDef: !!kor[cid + "/" + smer], kamera: !!kam[cid + "/" + smer] });
      }
    }
  }
  zapisi.sort((a, b) => (a.sa < b.sa ? -1 : a.sa > b.sa ? 1 : 0));
  console.log(`Jedinstvenih snapshotova: ${videni.size}   odbaceno duplikata: ${duplikata}`);
  console.log(`Celija (prelaz x smer x snapshot): ${zapisi.length}\n`);

  // Stanja bez `v` (sukob, neizvesno) nemaju pobednika po dizajnu - opis mora
  // da pokaze OBE vrednosti, inace bi "neizvesno" izgledalo isto bez obzira na
  // to da li je zvanicni broj sacuvan ili izgubljen.
  const opis = (r) => {
    if (r.v != null) return r.stanje + ":" + r.v;
    if (r.niza || r.visa)
      return r.stanje + "[" + (r.niza ? r.niza.v : "-") + "<->" + (r.visa ? r.visa.v : "-") + "]";
    return r.stanje;
  };
  const INCIDENTI = ["bogorodica", "medzitlija", "gradina", "presevo", "batrovci"];

  for (const V of IMENA) {
    const prelaz = new Map();      // "pre -> posle" : broj
    const poKoridoru = new Map();
    const konteksti = { sa_zvanicnim: 0, bez_zvanicnog: 0, dva_zvanicna: 0 };
    const bezKamere = new Set();
    let promenjenih = 0;
    let nestaloBezGuzve = 0, nestaloNema = 0, nestaloProveri = 0;
    let uNeizvesno = 0, uKolona = 0, novaKrupnaBrojka = 0, prijavaVracena = 0;
    let brojPresaoUNiza = 0, bezIkakvogBroja = 0;
    const primeri = [];
    const incidentPrimeri = new Map();

    for (const z of zapisi) {
      const ulaz = { ...z.c, __id: z.cid };
      const a = P.OSNOVA(ulaz, z.smer);
      const b = P[V](ulaz, z.smer);
      const ka = opis(a), kb = opis(b);
      if (ka === kb) continue;
      promenjenih++;

      const kljuc = `${ka}  ->  ${kb}`;
      prelaz.set(kljuc, (prelaz.get(kljuc) || 0) + 1);
      const kk = `${z.cid}/${z.smer}`;
      poKoridoru.set(kk, (poKoridoru.get(kk) || 0) + 1);
      if (!z.kamera) bezKamere.add(kk);

      // kontekst: koliko ZVANICNIH procena postoji za taj smer
      const pu = (z.c.putnicka || {})[z.smer];
      const zv = [];
      if (pu != null && pu > 0 && pu !== 30) zv.push("policija");
      if (z.c.hu && z.c.hu[z.smer] > 0) zv.push("hu");
      if (z.c.mk) {
        const m = z.smer === "izlaz" ? z.c.mk.vlez : z.c.mk.izlez;
        if (m > 0) zv.push("mk");
        if (z.c.mk.opsto > 0) zv.push("mk-opsto");
      }
      if (zv.length === 0) konteksti.bez_zvanicnog++;
      else if (zv.length === 1) konteksti.sa_zvanicnim++;
      else konteksti.dva_zvanicna++;

      if (a.stanje === "bez-guzve") nestaloBezGuzve++;
      if (a.stanje === "nema") nestaloNema++;
      if (a.stanje === "proveri") nestaloProveri++;
      if (b.stanje === "neizvesno") uNeizvesno++;
      if (b.stanje === "kolona") uKolona++;
      // "nova krupna brojka" = ranije NIJE bilo broja u naslovu, sada JESTE i
      // to velik. To je cena varijante, ne dobit - zato stoji uz oznaku rizika.
      if (a.v == null && b.v != null && b.v >= 120) novaKrupnaBrojka++;
      // Pre je stajao broj u naslovu, posle ga nema u polju `v`. To NIJE isto
      // sto i gubitak podatka: ako "neizvesno" nosi `niza`, zvanicni broj je
      // sacuvan i prikaz ga i dalje moze ispisati krupno. Razdvojeno, jer bi
      // jedan zbirni broj citao kao da smo covjeku oduzeli procenu.
      if (a.v != null && b.v == null) {
        if (b.niza) brojPresaoUNiza++;
        else bezIkakvogBroja++;
      }
      if (a.baOsporen != null && b.stanje !== "proveri") prijavaVracena++;

      if (primeri.length < 12) {
        primeri.push(
          `${z.sa.slice(0, 16)}  ${kk}\n` +
          `      pre:   ${ka}${a.baOsporen != null ? `  (prijava ${a.baOsporen} min potisnuta)` : ""}` +
          `  tt=${a.ttMin}min/kolona=${a.kolona}\n` +
          `      posle: ${kb}`);
      }
      if (INCIDENTI.indexOf(z.cid) !== -1) {
        const lst = incidentPrimeri.get(z.cid) || [];
        if (lst.length < 3) { lst.push(`${z.sa.slice(0, 16)} ${z.smer}: ${ka} -> ${kb}`); incidentPrimeri.set(z.cid, lst); }
      }
    }

    console.log("=".repeat(100));
    console.log(`VARIJANTA ${V}`);
    console.log("=".repeat(100));
    console.log(`Promenjenih celija: ${promenjenih} od ${zapisi.length} (${(100 * promenjenih / zapisi.length).toFixed(2)}%)\n`);
    console.log(`  nestalo "bez-guzve":              ${nestaloBezGuzve}`);
    console.log(`  nestalo "nema podataka":          ${nestaloNema}`);
    console.log(`  nestalo "proveri kameru":         ${nestaloProveri}`);
    console.log(`  velikih prijava vise nije skriveno: ${prijavaVracena}`);
    console.log(`  novih KRUPNIH brojki u naslovu:   ${novaKrupnaBrojka}   <-- rizik`);
    console.log(`  preslo u "neizvesno":             ${uNeizvesno}`);
    console.log(`  preslo u "kolona" (velika guzva): ${uKolona}`);
    console.log(`  broj presao u "niza" (sacuvan):   ${brojPresaoUNiza}`);
    console.log(`  OSTALO BEZ IKAKVOG BROJA:         ${bezIkakvogBroja}   <-- cena`);
    console.log(`\n  kontekst promenjenih celija:`);
    console.log(`     bez zvanicnog izvora:  ${konteksti.bez_zvanicnog}`);
    console.log(`     jedan zvanicni izvor:  ${konteksti.sa_zvanicnim}`);
    console.log(`     dva ili vise:          ${konteksti.dva_zvanicna}`);
    console.log(`\n  pogodjenih smerova BEZ KAMERE: ${bezKamere.size}`
      + (bezKamere.size ? `  (${[...bezKamere].join(", ")})` : ""));

    console.log(`\n  PRELAZI STANJA:`);
    [...prelaz.entries()].sort((x, y) => y[1] - x[1])
      .forEach(([k, n]) => console.log(`     ${String(n).padStart(6)}  ${k}`));

    console.log(`\n  PO KORIDORU:`);
    [...poKoridoru.entries()].sort((x, y) => y[1] - x[1])
      .forEach(([k, n]) => console.log(`     ${String(n).padStart(6)}  ${k}`));

    console.log(`\n  POZNATI INCIDENTI (pre -> posle):`);
    for (const cid of INCIDENTI) {
      const lst = incidentPrimeri.get(cid);
      console.log(`     ${cid}: ${lst ? "" : "nijedna celija se ne menja"}`);
      (lst || []).forEach((x) => console.log(`        ${x}`));
    }

    console.log(`\n  KONKRETNE PROMENE (prvih ${primeri.length}):`);
    primeri.forEach((p) => console.log("     " + p));
    console.log();
  }
}

// ---------------------------------------------------------------------------
const src = fs.readFileSync(KANON, "utf8");
if (process.argv.indexOf("--selftest") !== -1) {
  console.log("Zakrpe koje se primenjuju:\n");
  for (const ime of Object.keys(VARIJANTE)) {
    if (ime === "OSNOVA") continue;
    const s = VARIJANTE[ime](src);
    const i = s.indexOf("merenjeMirno");
    console.log(`--- ${ime} ---`);
    console.log(s.slice(i - 120, i + 420).split("\n").map((l) => "   " + l).join("\n"));
    console.log();
  }
  process.exit(selftest(src) ? 0 : 1);
} else {
  if (!selftest(src)) { console.log("\nSELFTEST PAO - analiza se ne pokrece."); process.exit(1); }
  console.log();
  analiza(src);
}
