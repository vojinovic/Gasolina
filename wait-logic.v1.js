/**
 * Gasolina - KANONSKA logika cekanja. Jedini izvor istine.
 *
 * ZASTO POSTOJI: ista logika je do 02.08.2026 zivela u CETIRI fajla (granice.html,
 * en/borders.html, generate_crossing_pages.py, index.html). index.html je dvaput
 * zaboravljen pri izmeni pravila, pa je naslovna za Gradina/ulaz pisala 34 min a
 * landing 20. Dok postoje cetiri kopije, svaka izmena pravila mora rucno u sve.
 *
 * VRACA PODATAK, NE TEKST. Nikakvo "proveri kameru" ni "1h 20m" - to je posao
 * prikaza, koji se granatira po jeziku. Time en/borders.html vise nema sopstvenu
 * verziju ODLUKE, nego samo prevod PRIKAZA.
 *
 * IZLAZ nosi `src` kao KLJUC ("policija" | "hu" | "mk" | "ba" | "user"), ne kao
 * natpis. Do 02.08.2026 su tu stajale srpske reci, pa je engleska stranica
 * ispisivala "source: prijave vozaca" - odluka i jezik su bili u istoj funkciji.
 * Prevod kljuca radi svaka stranica za sebe.
 *
 * ULAZ je sirovi zapis prelaza iz granice.json:
 *   {putnicka:{ulaz,izlaz}, hu:{...}, mk:{...}, ba:{...}, user:{...}, tt:{...}}
 *
 * NAZIVI SU MENJANI 03.08.2026, POSLE REVIZIJE AMSS-a. Stara imena su tvrdila
 * vise nego sto znamo:
 *   AMSS_DEFAULT_MIN -> AMSS_NAJNIZA_MIN   "default" tvrdi kako njihov sistem
 *                                          radi; mi znamo samo da je 30 najniza
 *                                          vrednost koju ikad objave (6.890
 *                                          celija kroz 40 dana, nijedna ispod).
 *   samAmss          -> amss30Only         staro ime nije govorilo NISTA - ni
 *                                          koja vrednost ni zasto je izdvojena.
 *                                          Novo opisuje SITUACIJU (jedini izvor
 *                                          je AMSS-ovih tacno 30), ne odluku
 *                                          algoritma.
 * Preimenovanje je islo zasebnim commitom, uz regeneraciju zamrznutog fixture-a
 * i dokaz da se nijedno stanje, brojka ni korisnicki tekst nisu promenili.
 *
 * NAZIVI: zvanicni izvori NISU merenje. AMSS, police.hu i AMSM daju PROCENU
 * (police.hu izricito pise da su podaci "tapasztalati uton megallapitottak es
 * tajekoztato jellegűek" - iskustveni i informativni). Merenje daje samo TomTom,
 * i to donju granicu, jer ne vidi kolonu koja STOJI na pasoskoj kontroli.
 *
 * NE MENJATI PRAVILA U ISTOM COMMITU SA PRESELJENJEM KODA. Ponasanje je zamrznuto
 * u engine/wait-golden.json (1.046 kombinacija iz arhiva) - posle preseljenja mora
 * biti identicno, tek onda se sme menjati pravilo.
 *
 * OMOTAC (IIFE) NIJE UKRAS. Klasicni <script> tagovi dele isti globalni leksicki
 * opseg: bez njega bi `const NO_QUEUE_MAX` iz ovog fajla i isti taj `const` u
 * granice.html bili DVE deklaracije istog imena, sto je SyntaxError - i cela
 * inline skripta stranice prestaje da se parsira, pa se ne ucita nijedna kartica.
 * Tako je 02.08.2026 granice.html ostala prazna. Nista se ne sme izneti u globalni
 * opseg osim window.GasolinaWait.
 */

(function () {
const NO_QUEUE_MAX = 15;
const AMSS_NAJNIZA_MIN = 30;
const QUEUE_HARD_M = 200;
const BA_PROVERA_MIN = 120;
const TT_MIRNO_MIN = 5;
// Koliko puta jedna procena mora da nadmasi drugu da bi to bio SUKOB, a ne
// razlika. Arhiv 24.06-03.08.2026: odnos izmedju 2,5x i 4x menja zahvat za samo
// jednu celiju, pa broj nije osetljiv - 3 je izabrano jer je najlakse objasniti.
const SUKOB_ODNOS = 3;

function procena(c, dirKey){
  // --- saobracajni signal (nikad krupna brojka) ---
  const ttMin  = (c.tt && c.tt[dirKey] != null) ? c.tt[dirKey] : null;
  const kolona = (c.tt && c.tt[dirKey + "_kolona_m"] != null) ? c.tt[dirKey + "_kolona_m"] : null;
  const dugaKolona = (kolona != null && kolona >= QUEUE_HARD_M);

  // --- kandidati za UKUPNO cekanje ---
  const cands = [];              // {v, src, tip}
  let kratkoZvanicno = false;    // zvanicni izvor izricito kaze "nema cekanja"

  // SIROVE vrednosti po vrsti izvora, pre nego sto ijedno pravilo nesto potisne.
  // Sukob se racuna nad njima, a ne nad `cands`: Bogorodica 28.07.2026 - prijava
  // od 4h je bila potisnuta mirnim merenjem, ostalo je AMSM-ovih 15 min i sajt je
  // napisao "Bez guzve" dok su vozaci prijavljivali cetiri sata. Potisnuta prijava
  // ne sme da nestane bez traga.
  const zvanicniSvi = [];        // {v, src} - procene UKUPNOG cekanja, zvanicne
  const prijaveSve = [];         // {v, src} - prijave vozaca

  // JEDINO mesto koje se razlikovalo medju cetiri kopije: pregled je citao
  // c.wait.putnicka, generator c.putnicka uz uslov c.found. Kanonski ulaz je
  // SIROVI zapis prelaza iz granice.json; pozivaoci prilagodjavaju svoj oblik.
  const p = c.putnicka ? c.putnicka[dirKey] : null;
  const amss30 = (p === AMSS_NAJNIZA_MIN);
  if (p != null && !amss30) {
    if (p > 0) { cands.push({v: p, src: "policija", tip: "zvanicni"});
                 zvanicniSvi.push({v: p, src: "policija"}); }
    else kratkoZvanicno = true;
  }
  if (c.hu) {
    const v = c.hu[dirKey];
    if (v != null) { if (v > 0) { cands.push({v, src: "hu", tip: "zvanicni"});
                                  zvanicniSvi.push({v, src: "hu"}); }
                     else kratkoZvanicno = true; }
  }
  if (c.mk) {
    const v = (dirKey === 'izlaz') ? c.mk.vlez : c.mk.izlez;
    if (v != null) { if (v > 0) { cands.push({v, src: "mk", tip: "zvanicni"});
                                  zvanicniSvi.push({v, src: "mk"}); }
                     else kratkoZvanicno = true; }
    // `opsto` je AMSM-ova recenica u kojoj je prelaz IMENOVAN ali bez oznake
    // smera - dakle procena za taj prelaz, koju primenjujemo na oba smera.
    // Slabija je od vrednosti sa smerom, pa prikaz to i kaze.
    if (c.mk.opsto != null) { if (c.mk.opsto > 0) { cands.push({v: c.mk.opsto, src: "mk", tip: "zvanicni"});
                                                    zvanicniSvi.push({v: c.mk.opsto, src: "mk-opsto"}); }
                              else kratkoZvanicno = true; }
  }
  // sopstvena forma: medijana vec izracunata u scraperu; broj prijava nosi tezinu
  let user = null;
  if (c.user && c.user[dirKey] != null) {
    user = c.user[dirKey];
    cands.push({v: user, src: "user", tip: "prijava"});
    if (user > 0) prijaveSve.push({v: user, src: "user"});
  }

  // --- prijava vozaca, uz proveru merenjem ---
  // Merenje sme da ospori SAMO ekstremnu prijavu, i samo tako sto joj oduzme
  // pravo na krupnu brojku - nikad tako sto svoju vrednost stavi umesto nje.
  let baOsporen = null;
  if (c.ba) {
    const v = c.ba[dirKey];
    if (v != null && v > 0) {
      const merenjeMirno = (ttMin != null && ttMin <= TT_MIRNO_MIN && !dugaKolona);
      prijaveSve.push({v, src: "ba"});
      if (v >= BA_PROVERA_MIN && merenjeMirno) baOsporen = v;
      else cands.push({v, src: "ba", tip: "prijava"});
    }
  }

  const zvanicniPostoji = cands.some(x => x.tip === "zvanicni");

  // --- odluka ---

  // 0. SUKOB IZVORA. Dve procene UKUPNOG cekanja koje se razilaze vise od tri
  //    puta nisu razlika nego neslaganje, i sajt nema cime da presudi. Umesto da
  //    tiho uzme vecu, kaze da se izvori ne slazu i pokaze OBE vrednosti.
  //
  //    Okida se u dva slucaja:
  //      A) prijava vozaca je mnogo VECA od zvanicne procene
  //      C) dva zvanicna izvora se razilaze medjusobno (policija naspram AMSM-a,
  //         Presevo 01.08.2026: 180 naspram 30 minuta)
  //
  //    NE okida se kad je zvanicna procena mnogo veca od prijave (slucaj B).
  //    To NIJE proizvoljna asimetrija: invarijanta 2 kaze da jedna kratka prijava
  //    nije dokaz da je prelaz prohodan. Ako prijava od 5 minuta ne sme da da
  //    "Bez guzve", ne sme ni da obori zvanicnih 240 na "ne znamo". Arhiv:
  //    11 takvih celija, sve sa prijavom od 5 do 60 minuta.
  //
  //    Prag je VECA vrednost >= BA_PROVERA_MIN: sitna neslaganja (20 naspram 5)
  //    nisu vredna oduzimanja brojke.
  {
    const par = [];
    if (zvanicniSvi.length && prijaveSve.length) {
      const z = zvanicniSvi.reduce((a, b) => b.v > a.v ? b : a);   // najveci zvanicni:
      const p2 = prijaveSve.reduce((a, b) => b.v > a.v ? b : a);   // najstroze prema sukobu
      if (p2.v >= SUKOB_ODNOS * z.v) par.push({niza: z, visa: p2});
    }
    if (zvanicniSvi.length >= 2) {
      const mx = zvanicniSvi.reduce((a, b) => b.v > a.v ? b : a);
      const mn = zvanicniSvi.reduce((a, b) => b.v < a.v ? b : a);
      if (mx.v >= SUKOB_ODNOS * mn.v) par.push({niza: mn, visa: mx});
    }
    // Vrednost 0 nikad ne ulazi u ove nizove (nula je "nema cekanja", pa ide u
    // kratkoZvanicno), tako da mnozenje ne moze da uporedi nista sa nistom.
    const sukob = par.filter(x => x.visa.v >= BA_PROVERA_MIN)
                     .sort((a, b) => (b.visa.v / b.niza.v) - (a.visa.v / a.niza.v))[0];
    if (sukob) {
      // NEMA `v`. Da postoji, svaki prikaz bi ga ispisao kao naslov i time
      // proglasio pobednika - a cela poenta je da pobednika nema.
      return {stanje: "sukob", niza: sukob.niza, visa: sukob.visa,
              kolona, dugaKolona, ttMin};
    }
  }

  // 1. Osporena ekstremna prijava, a nema zvanicnog izvora da preuzme:
  //    ne izmisljamo broj, upucujemo na kameru. TomTom OVDE NE PREUZIMA NASLOV.
  if (baOsporen != null && !zvanicniPostoji)
    return {stanje: "proveri", baOsporen, kolona, dugaKolona, ttMin};

  if (cands.length) {
    let best = cands[0];
    cands.forEach(x => { if (x.v > best.v) best = x; });

    // 2. Zvanicni izvor kaze kratko, a prijava kaze dugo -> dva izvora iste
    //    vrste se ne slazu. Ni jedno ni drugo se ne proglasava istinom.
    if (kratkoZvanicno && best.tip === "prijava" && best.v >= BA_PROVERA_MIN)
      return {stanje: "proveri", baOsporen: best.v, kolona, dugaKolona, ttMin};

    // 2b. Izmerena duga kolona obara svaki umirujuci naslov. Gradina 01.08.:
    //     prijava 10 min uz izmerenih 1.478 m kolone - to nije "10 minuta".
    //     Ovde merenje POTVRDJUJE guzvu, sto donja granica sme; ne opovrgava.
    if (dugaKolona && best.v <= NO_QUEUE_MAX)
      return {stanje: "kolona", v: best.v, src: best.src, kolona, dugaKolona, ttMin};

    if (best.v <= NO_QUEUE_MAX && !dugaKolona) {
      // 3. "Bez guzve" trazi POZITIVAN dokaz: zvanican izvor. Jedna prijava od
      //    10 minuta nije dokaz da je prelaz prohodan - 94% dosadasnjih "Bez
      //    guzve" prikaza pocivalo je bas na tome.
      if (best.tip === "zvanicni" || kratkoZvanicno)
        return {stanje: "bez-guzve", src: best.src, kolona, dugaKolona, ttMin};
      return {stanje: "kratko-prijava", v: best.v, src: best.src, kolona, dugaKolona, ttMin};
    }
    // 4. Prijava koja prodje: broj ostaje, ali rec "prijavljeno" ide UZ brojku,
    //    ne sitno ispod. Kolona od 734 m potvrdjuje da guzva postoji, ne da
    //    traje bas 8 sati.
    if (best.tip === "prijava")
      return {stanje: "prijavljeno", v: best.v, src: best.src, kolona, dugaKolona, ttMin};
    return {stanje: "broj", v: best.v, src: best.src, kolona, dugaKolona, ttMin};
  }

  // 5. Nema nijednog izvora ukupnog cekanja. TomTom sme samo da javi kolonu.
  if (dugaKolona) return {stanje: "kolona", kolona, dugaKolona, ttMin};
  if (baOsporen != null) return {stanje: "proveri", baOsporen, kolona, dugaKolona, ttMin};
  return {stanje: "nema", amss30Only: amss30, kolona, dugaKolona, ttMin};
}

// Radi i u browseru (<script src>) i u Node-u (testovi, generator).
if (typeof module !== "undefined" && module.exports) {
  module.exports = { procena, NO_QUEUE_MAX, AMSS_NAJNIZA_MIN, QUEUE_HARD_M, BA_PROVERA_MIN, TT_MIRNO_MIN, SUKOB_ODNOS };
}
if (typeof window !== "undefined") {
  window.GasolinaWait = { procena, NO_QUEUE_MAX, AMSS_NAJNIZA_MIN, QUEUE_HARD_M, BA_PROVERA_MIN, TT_MIRNO_MIN, SUKOB_ODNOS };
}
})();
