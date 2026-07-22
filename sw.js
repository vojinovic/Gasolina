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
  const opts = event.request.destination === 'document' ? { cache: 'no-cache' } : undefined;
  event.respondWith(
    fetch(event.request, opts)
      .then((res) => {
        const resClone = res.clone();
        caches.open(CACHE_NAME).then((cache) => cache.put(event.request, resClone)).catch(() => {});
        return res;
      })
      .catch(() => caches.match(event.request))
  );
});
