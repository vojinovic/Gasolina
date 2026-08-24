const CACHE_NAME = 'gasolina-v1';
const APP_SHELL = [
  '/index.html', '/granice.html', '/istorija.html', '/vodici.html',
  '/borders-data.js', '/manifest.json',
  '/icons/icon-192.png', '/icons/icon-512.png',
];

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => cache.addAll(APP_SHELL)).catch(() => {})
  );
  self.skipWaiting();
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((k) => k !== CACHE_NAME).map((k) => caches.delete(k)))
    )
  );
  self.clients.claim();
});

// Network-first za SVE - nikad ne zelimo da prikazemo zastarelu cenu goriva ili
// pogresno stanje granice kao da je "uzivo" dok smo zapravo offline. Kes je
// SAMO rezerva kad mreze uopste nema, ne primarni izvor podataka. Ovo je
// namerno drugacije od tipicnog PWA "cache-first radi brzine" pristupa - ovde
// je iskrenost podataka vaznija od brzine.
self.addEventListener('fetch', (event) => {
  if (event.request.method !== 'GET') return;
  // Za HTML dokumente: 'no-cache' tera browser da UVEK proveri server (ETag),
  // inace navigacija sluzi i do 10 min staru kopiju iz HTTP kesa (GitHub Pages
  // salje max-age=600) - pa korisnik posle naseg update-a vidi staru stranicu
  // na klik, a novu tek na refresh. Provera je jeftina (304 ako nema izmene).
  const jeDokument = event.request.destination === 'document';
  const opts = jeDokument ? { cache: 'no-cache' } : undefined;
  event.respondWith(
    fetch(event.request, opts)
      .then((res) => {
        const resClone = res.clone();
        caches.open(CACHE_NAME).then((cache) => cache.put(event.request, resClone)).catch(() => {});
        return res;
      })
      .catch(() => rezerva(event.request, jeDokument))
  );
});

// REZERVA KAD MREZE NEMA (ispravljeno 24.08.2026)
//
// Do danas je ovde stajalo `.catch(() => caches.match(event.request))`.
// `caches.match` se razresava u `undefined` kad pogotka nema, a `respondWith`
// trazi Response - pa je svaki promasaj postajao
//     TypeError: Failed to convert value to 'Response'
// i navigacija bi pukla sa "network error response". To se videlo u konzoli na
// SVAKOM ucitavanju stranice sa upitom, npr. granica-horgos.html?play=1&feed=1.
//
// Dve stvari se popravljaju:
//
// 1. Uvek se vraca Response. Ako ni kesa nema, ide poruka koja POSTENO kaze da
//    veze nema - umesto pucanja koje covek vidi kao "stranica ne radi".
//
// 2. `ignoreSearch` SAMO za dokumente. Stranice se otvaraju sa ?play=1&feed=1
//    iz granice.html, pa bez toga kesirana kopija nikad ne bi bila pogodjena.
//    Za sve ostalo poredjenje ostaje TACNO, namerno: granice.json i pumpe.json
//    se povlace sa ?cb=<vreme>, i kad bi se upit zanemario, offline bismo
//    servirali STARI podatak pod istom adresom - a to je tacno ono sto ovaj
//    sajt ne sme da radi. Bolje nista nego stara brojka bez oznake starosti.
function rezerva(request, jeDokument) {
  return caches.match(request, jeDokument ? { ignoreSearch: true } : undefined)
    .then((hit) => {
      if (hit) return hit;
      if (!jeDokument) return new Response('', { status: 504, statusText: 'Nema veze' });
      return new Response(
        '<!doctype html><meta charset="utf-8">' +
        '<meta name="viewport" content="width=device-width,initial-scale=1">' +
        '<title>Nema veze sa internetom &middot; Gasolina</title>' +
        '<style>body{margin:0;background:#0d1620;color:#e9eff5;' +
        'font-family:"JetBrains Mono",ui-monospace,monospace;line-height:1.6;' +
        'display:flex;align-items:center;justify-content:center;min-height:100vh;padding:24px}' +
        'div{max-width:420px}a{color:#f5a623}</style>' +
        '<div><b>Nema veze sa internetom.</b><br>' +
        'Stanje na granici se ne moze proveriti bez mreze, a stara brojka ' +
        'ovde ne bi znacila nista. Pokusaj ponovo kad se veza vrati.<br><br>' +
        '<a href="/">gasolina.rs</a></div>',
        { status: 503, headers: { 'Content-Type': 'text/html; charset=utf-8' } }
      );
    });
}
