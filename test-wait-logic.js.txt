#!/usr/bin/env node
/* Regresioni testovi za izbor prikazane brojke o čekanju.
 *
 * Ne testiraju kopiju logike nego LOGIKU IZ granice.html — funkcija se izvlači
 * iz same objavljene stranice. Ako neko promeni algoritam a zaboravi pravila
 * niže, ovo padne u CI pre nego što stigne na sajt.
 *
 * Svako pravilo ovde ima svoj incident iza sebe. Ne uklanjati ih da bi test
 * prošao — svrha im je da se ti incidenti ne ponove.
 *
 * Pokretanje:  node test-wait-logic.js
 */
const fs = require("fs");

const html = fs.readFileSync("granice.html", "utf8");
const a = html.indexOf("const NO_QUEUE_MAX");
const b = html.indexOf("function waitCell(");
if (a === -1 || b === -1 || a > b) {
  console.error("NE MOGU da nađem blok sa logikom u granice.html — je li preimenovan?");
  process.exit(1);
}
const effective = new Function(html.slice(a, b) + "\nreturn effective;")();

let pao = 0;
function test(ime, c, dirKey, provera) {
  const e = effective(c, dirKey);
  const poruka = provera(e);
  if (poruka) { pao++; console.log(`  [PAO ] ${ime}\n         ${poruka}\n         dobijeno: ${JSON.stringify(e)}`); }
  else console.log(`  [OK  ] ${ime}`);
}

console.log("\nPravila koja ne smeju da se pokvare:\n");

// 1. TomTom meri samo vozila koja se KRECU. Nikad ne sme da bude ukupno čekanje.
test("TomTom ne postaje glavna brojka",
  {ba: null, tt: {izlaz: 12, izlaz_kolona_m: 50}}, "izlaz",
  e => (e.stanje === "broj" || e.stanje === "prijavljeno")
       ? "TomTom je postao krupna brojka" : null);

// 2. Jedna prijava od 10 minuta nije dokaz da je prelaz prohodan.
//    94% dosadašnjih "Bez gužve" prikaza počivalo je baš na tome.
test("jedna kratka prijava ne daje 'Bez gužve'",
  {ba: {izlaz: 10}, tt: null}, "izlaz",
  e => e.stanje === "bez-guzve" ? "jedna prijava proglašena za 'Bez gužve'" : null);

// 3. Gradina 01.08.: prijava 10 min uz izmerenih 1478 m kolone.
test("duga kolona obara umirujući naslov",
  {ba: {ulaz: 10}, tt: {ulaz: 17, ulaz_kolona_m: 1478}}, "ulaz",
  e => ["bez-guzve", "kratko-prijava"].includes(e.stanje)
       ? "kilometar i po kolone prikazan kao kratko čekanje" : null);

// 4. Preševo 01.08.: prijava 2h oborena, TomTomova 1 minuta postala naslov -> "Bez gužve",
//    a kamera puna kolona. Donja granica ne sme da preuzme naslov.
test("osporena prijava ne pada na TomTomovu brojku",
  {ba: {ulaz: 120}, tt: {ulaz: 1, ulaz_kolona_m: 53}}, "ulaz",
  e => e.stanje !== "proveri" ? "osporena prijava nije završila na 'proveri kameru'" : null);

// 5. Batrovci: prijava 8h uz potvrđenu kolonu od 734 m. Broj ostaje, ali mora
//    da se vidi da je prijavljen, a ne izmeren.
test("potvrđena velika prijava ostaje označena kao prijava",
  {ba: {ulaz: 480}, tt: {ulaz: 20, ulaz_kolona_m: 734}}, "ulaz",
  e => e.stanje !== "prijavljeno" ? "velika prijava nije označena kao prijavljena" : null);

// 6. AMSS-ovih tačno 30 je podrazumevana vrednost, ne merenje.
test("AMSS-ovih tačno 30 nije kandidat",
  {wait: {putnicka: {izlaz: 30}}, ba: null, tt: null}, "izlaz",
  e => e.stanje !== "nema" ? "AMSS default je postao prikazana brojka" : null);

// 7. Kolona koja dolazi do granice koridora: ne znamo dokle se pruža.
{
  const kor = 1216, m = 1478;
  const src = html.slice(html.indexOf("function fmtKolona"), html.indexOf("function effective"));
  const fmtKolona = new Function(src + "\nreturn fmtKolona;")();
  const t = fmtKolona(m, kor);
  if (!/najmanje/.test(t)) { pao++; console.log(`  [PAO ] kolona na granici koridora mora da kaže "najmanje"\n         dobijeno: ${t}`); }
  else console.log("  [OK  ] kolona na granici koridora kaže 'najmanje'");
  const t2 = fmtKolona(600, 2926);
  if (!/oko/.test(t2)) { pao++; console.log(`  [PAO ] kolona duboko u koridoru treba "oko"\n         dobijeno: ${t2}`); }
  else console.log("  [OK  ] kolona duboko u koridoru kaže 'oko'");
}

console.log(pao ? `\nPALO: ${pao}\n` : "\nSve prolazi.\n");
process.exit(pao ? 1 : 0);
