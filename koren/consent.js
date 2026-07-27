/* Gasolina - pristanak na kolacice (Google Consent Mode v2)
 *
 * VAZNO: ovaj fajl se ucitava SINHRONO u <head>, NEPOSREDNO PRE gtag/js skripta.
 * Nema ni async ni defer. Redosled je obavezan - "consent default" mora da
 * stigne u dataLayer pre nego GA posalje prvi zahtev, inace se kolacici
 * postave pre nego korisnik bilo sta izabere i ceo mehanizam nema smisla.
 *
 * Podrazumevano stanje je ODBIJENO za sve signale i sve regione. Srbija nije
 * u EEA, ali Zakon o zastiti podataka o licnosti vazi za nas kao rukovaoca
 * bez obzira odakle je posetilac, pa nema razloga za dva rezima.
 *
 * U odbijenom stanju GA4 i dalje salje pingove bez kolacica (Consent Mode),
 * tako da zbirni saobracaj ostaje vidljiv - gubi se razlikovanje posetilaca.
 */
(function () {
  'use strict';

  var KEY = 'gasolina_consent';
  var SIGNALS = ['ad_storage', 'ad_user_data', 'ad_personalization', 'analytics_storage'];

  window.dataLayer = window.dataLayer || [];
  function gtag() { window.dataLayer.push(arguments); }
  if (typeof window.gtag !== 'function') window.gtag = gtag;

  function signals(value) {
    var o = {}, i;
    for (i = 0; i < SIGNALS.length; i++) o[SIGNALS[i]] = value;
    return o;
  }

  /* 1. Podrazumevano stanje - pre svega ostalog. */
  var def = signals('denied');
  def.wait_for_update = 500;
  gtag('consent', 'default', def);
  gtag('set', 'ads_data_redaction', true);
  gtag('set', 'url_passthrough', true);

  /* 2. Sacuvan izbor. */
  function read() {
    try {
      var raw = window.localStorage.getItem(KEY);
      if (!raw) return null;
      var o = JSON.parse(raw);
      return (o && typeof o.granted === 'boolean') ? o : null;
    } catch (e) { return null; }
  }

  function save(granted) {
    try {
      window.localStorage.setItem(KEY, JSON.stringify({
        v: 1, granted: granted, ts: new Date().toISOString()
      }));
    } catch (e) {}
  }

  function apply(granted) {
    gtag('consent', 'update', signals(granted ? 'granted' : 'denied'));
  }

  var saved = read();
  if (saved) apply(saved.granted);

  /* 3. Tekstovi. Jezik se cita iz <html lang>, isto kao svuda na sajtu. */
  var EN = (document.documentElement.getAttribute('lang') || 'sr').toLowerCase().indexOf('en') === 0;
  var T = EN ? {
    title: 'Cookie consent',
    body: 'Gasolina uses cookies for traffic statistics and, once ads are active, for showing ads. There are no accounts on this site and nothing is tied to your name.',
    accept: 'Accept',
    reject: 'Reject',
    policy: 'Privacy policy',
    policyHref: '/en/privacy-policy.html',
    manage: 'Cookies'
  } : {
    title: 'Pristanak na kolačiće',
    body: 'Gasolina koristi kolačiće za statistiku posećenosti i, kada oglasi budu aktivni, za prikaz oglasa. Sajt nema naloge i ništa se ne vezuje za tvoje ime.',
    accept: 'Prihvatam',
    reject: 'Odbijam',
    policy: 'Politika privatnosti',
    policyHref: '/politika-privatnosti.html',
    manage: 'Kolačići'
  };

  var MONO = '"JetBrains Mono",ui-monospace,SFMono-Regular,Menlo,monospace';
  var COND = '"Barlow Condensed",system-ui,sans-serif';

  /* 4. Baner. Oba dugmeta su iste velicine i iste tezine - odbijanje mora da
     bude jednako lako kao prihvatanje, to je uslov, ne stil. */
  var box = null;

  function close() {
    if (!box) return;
    if (box.parentNode) box.parentNode.removeChild(box);
    box = null;
  }

  function button(label, primary) {
    var b = document.createElement('button');
    b.type = 'button';
    b.textContent = label;
    b.style.cssText =
      'font-family:' + COND + ';font-weight:600;text-transform:uppercase;' +
      'letter-spacing:.05em;font-size:14px;line-height:1;padding:11px 20px;' +
      'min-width:132px;border-radius:8px;cursor:pointer;' +
      (primary
        ? 'background:var(--fuel,#f5a623);color:var(--ink,#0d1620);border:1px solid var(--fuel,#f5a623)'
        : 'background:transparent;color:var(--text,#e9eff5);border:1px solid var(--line-2,#324658)');
    return b;
  }

  function decide(granted) {
    save(granted);
    apply(granted);
    close();
    if (granted) {
      try { window.gtag('event', 'consent_granted', { izvor: 'baner' }); } catch (e) {}
    }
  }

  function show() {
    if (box) return;

    box = document.createElement('div');
    box.id = 'gsl-consent';
    box.setAttribute('role', 'dialog');
    box.setAttribute('aria-modal', 'false');
    box.setAttribute('aria-label', T.title);
    box.style.cssText =
      'position:fixed;left:0;right:0;bottom:0;z-index:9999;' +
      'background:var(--panel,#15212e);border-top:1px solid var(--line,#26384a);' +
      'box-shadow:0 -10px 28px rgba(0,0,0,.4);' +
      'padding:14px 18px;padding-bottom:calc(14px + env(safe-area-inset-bottom,0px));' +
      'display:flex;flex-wrap:wrap;gap:14px;align-items:center;justify-content:center;' +
      'font-family:' + MONO + ';font-size:12.5px;line-height:1.6;color:var(--dim,#8aa0b2)';

    var text = document.createElement('span');
    text.style.cssText = 'max-width:620px;flex:1 1 320px';
    text.appendChild(document.createTextNode(T.body + ' '));

    var link = document.createElement('a');
    link.href = T.policyHref;
    link.textContent = T.policy;
    link.style.cssText = 'color:var(--text,#e9eff5);text-decoration:underline';
    text.appendChild(link);

    var row = document.createElement('div');
    row.style.cssText = 'display:flex;gap:10px;flex-wrap:wrap;flex:0 0 auto';

    var no = button(T.reject, false);
    var yes = button(T.accept, true);
    no.addEventListener('click', function () { decide(false); });
    yes.addEventListener('click', function () { decide(true); });
    row.appendChild(no);
    row.appendChild(yes);

    box.appendChild(text);
    box.appendChild(row);
    document.body.appendChild(box);
    /* Fokus ide na sam baner, ne na "Prihvatam" - fokusiranjem jednog dugmeta
       navodio bi se izbor, a to je upravo ono sto se ne sme. */
    box.tabIndex = -1;
    box.focus();
  }

  /* 5. Link u podnozju za promenu izbora - politika obecava da se pristanak
     moze povuci u svakom trenutku, ovo je to mesto. Ubacuje se pored linka na
     politiku privatnosti, bez izmene HTML-a stranica. */
  function footerLink() {
    var f = document.querySelector('footer');
    if (!f || f.querySelector('.gsl-consent-link')) return;

    var a = document.createElement('a');
    a.href = '#';
    a.className = 'gsl-consent-link';
    a.textContent = T.manage;
    a.style.cssText = 'color:var(--faint,#5d7387);text-decoration:underline';
    a.addEventListener('click', function (e) { e.preventDefault(); show(); });

    var copy = f.querySelector('span[style*="opacity"]');
    if (copy) {
      f.insertBefore(a, copy);
      f.insertBefore(document.createElement('br'), copy);
    } else {
      f.appendChild(document.createElement('br'));
      f.appendChild(a);
    }
  }

  function init() {
    footerLink();
    if (!read()) show();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

  window.gasolinaConsent = {
    open: show,
    state: read,
    reset: function () { try { window.localStorage.removeItem(KEY); } catch (e) {} }
  };
})();
