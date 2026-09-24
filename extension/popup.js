const $ = (id) => document.getElementById(id);
const t = (k) => chrome.i18n.getMessage(k) || k;

// Localize static text
document.documentElement.lang = chrome.i18n.getUILanguage();
document.querySelectorAll('[data-i18n]').forEach((el) => (el.textContent = t(el.dataset.i18n)));
document.querySelectorAll('[data-i18n-placeholder]').forEach((el) => (el.placeholder = t(el.dataset.i18nPlaceholder)));
const DEFAULT = { enabled: false, lat: 43.0747, lng: -89.3842, accuracy: 20, altitude: '', jitter: true };

let cfg, favs, marker, map = null;

// Surface any failure in the UI instead of silently killing the script
function showErr(msg) {
  const el = $('err');
  el.textContent = String(msg).slice(0, 300);
  el.hidden = false;
}
window.addEventListener('error', (e) => showErr(e.message));
window.addEventListener('unhandledrejection', (e) => showErr(e.reason));

// Controls work even if the map fails to load
$('save').onclick = save;
$('fav').onclick = addFav;
$('searchForm').onsubmit = search;
$('enabled').onchange = save;
['lat', 'lng', 'accuracy', 'altitude', 'jitter'].forEach((id) => ($(id).onchange = save));

try {
  map = L.map('map', { zoomControl: true });
  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    maxZoom: 19, attribution: '&copy; OpenStreetMap',
  }).addTo(map);
  map.on('click', (e) => { setPoint(e.latlng.lat, e.latlng.lng); save(); });
} catch (e) {
  showErr(t('mapFailed') + ' ' + e.message);
  $('map').style.display = 'none';
}

// Move pin + fields to a point
function setPoint(lat, lng, zoom) {
  lat = +(+lat).toFixed(6); lng = +(+lng).toFixed(6);
  $('lat').value = lat; $('lng').value = lng;
  if (!map) return;
  if (marker) marker.setLatLng([lat, lng]);
  else marker = L.marker([lat, lng], { draggable: true }).addTo(map)
    .on('dragend', (e) => { const p = e.target.getLatLng(); setPoint(p.lat, p.lng); save(); });
  map.setView([lat, lng], zoom || map.getZoom() || 15);
}

function readForm() {
  return {
    enabled: $('enabled').checked,
    lat: +$('lat').value, lng: +$('lng').value,
    accuracy: +$('accuracy').value || 20,
    altitude: $('altitude').value,
    jitter: $('jitter').checked,
  };
}

async function save() {
  cfg = readForm();
  if (!isFinite(cfg.lat) || !isFinite(cfg.lng) || Math.abs(cfg.lat) > 90 || Math.abs(cfg.lng) > 180) {
    $('state').textContent = t('stateInvalid'); return;
  }
  await chrome.storage.local.set({ cfg });
  const base = t(cfg.enabled ? 'stateOn' : 'stateOff');
  $('state').textContent = t('stateSaved');
  clearTimeout(save.t);
  save.t = setTimeout(() => ($('state').textContent = base), 900);
}

// Parse "lat, lng" or Google Maps URL
function parseCoords(s) {
  const m = s.match(/@(-?\d+\.?\d*),(-?\d+\.?\d*)/) || s.match(/!3d(-?\d+\.?\d*)!4d(-?\d+\.?\d*)/)
    || s.match(/^\s*(-?\d+\.?\d*)\s*[, ]\s*(-?\d+\.?\d*)\s*$/);
  return m ? [+m[1], +m[2]] : null;
}

async function search(e) {
  e.preventDefault();
  const q = $('q').value.trim();
  $('results').innerHTML = '';
  if (!q) return;
  const c = parseCoords(q);
  if (c) return setPoint(c[0], c[1], 16);
  const url = 'https://nominatim.openstreetmap.org/search?format=json&limit=6&accept-language=' + chrome.i18n.getUILanguage() + ',en&q=' + encodeURIComponent(q);
  try {
    const list = await (await fetch(url)).json();
    if (!list.length) $('results').innerHTML = `<li><span>${t('noResults')}</span></li>`;
    for (const r of list) {
      const li = document.createElement('li');
      li.innerHTML = '<span></span>';
      li.firstChild.textContent = r.display_name;
      li.onclick = () => { setPoint(r.lat, r.lon, 16); $('results').innerHTML = ''; };
      $('results').append(li);
    }
  } catch { $('results').innerHTML = `<li><span>${t('searchFailed')}</span></li>`; }
}

function renderFavs() {
  $('favs').innerHTML = '';
  favs.forEach((f, i) => {
    const li = document.createElement('li');
    li.innerHTML = `<span></span><b title="${t('remove')}">✕</b>`;
    li.firstChild.textContent = `${f.name}  (${f.lat}, ${f.lng})`;
    li.firstChild.onclick = () => setPoint(f.lat, f.lng, 16);
    li.lastChild.onclick = async () => { favs.splice(i, 1); await chrome.storage.local.set({ favs }); renderFavs(); };
    $('favs').append(li);
  });
}

async function addFav() {
  // Name from search box, fallback to label
  const q = $('q').value.trim();
  const name = q && !parseCoords(q) ? q.split(',')[0].slice(0, 30) : `${t('favorite')} ${favs.length + 1}`;
  favs.unshift({ name, lat: +$('lat').value, lng: +$('lng').value });
  await chrome.storage.local.set({ favs });
  renderFavs();
}

(async () => {
  const s = await chrome.storage.local.get(['cfg', 'favs']).catch((e) => { showErr(t('loadFailed') + ' ' + e.message); return {}; });
  cfg = { ...DEFAULT, ...s.cfg };
  favs = s.favs || [];
  $('enabled').checked = cfg.enabled;
  $('accuracy').value = cfg.accuracy;
  $('altitude').value = cfg.altitude;
  $('jitter').checked = cfg.jitter;
  $('state').textContent = t(cfg.enabled ? 'stateOn' : 'stateOff');
  setPoint(cfg.lat, cfg.lng, 15);
  renderFavs();
})();
