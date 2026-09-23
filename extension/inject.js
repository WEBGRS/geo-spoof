// Runs in the page world: patch Geolocation + Permissions
(() => {
  if (!window.Geolocation) return;
  const EVT = '__geo_spoof_cfg__';
  const G = Geolocation.prototype;
  const real = { get: G.getCurrentPosition, watch: G.watchPosition, clear: G.clearWatch };
  const realQuery = window.Permissions && Permissions.prototype.query;

  let cfg = null;
  const waiters = [];
  const watches = new Map();
  let nextId = 1;

  const ready = () => (cfg ? Promise.resolve() : new Promise((r) => waiters.push(r)));
  const on = () => !!(cfg && cfg.enabled);

  // Build a position object that passes instanceof checks
  function makePosition() {
    const acc = Math.max(1, +cfg.accuracy || 20);
    let lat = +cfg.lat, lng = +cfg.lng;
    if (cfg.jitter) {
      const r = (Math.random() * acc) / 3, t = Math.random() * 2 * Math.PI;
      lat += (r * Math.cos(t)) / 111320;
      lng += (r * Math.sin(t)) / (111320 * Math.cos((lat * Math.PI) / 180));
    }
    const c = {
      latitude: lat, longitude: lng, accuracy: acc,
      altitude: cfg.altitude === '' || cfg.altitude == null ? null : +cfg.altitude,
      altitudeAccuracy: null, heading: null, speed: null,
    };
    const coords = Object.create(GeolocationCoordinates.prototype);
    for (const k in c) Object.defineProperty(coords, k, { value: c[k], enumerable: true });
    Object.defineProperty(coords, 'toJSON', { value: () => ({ ...c }) });
    const ts = Date.now();
    const pos = Object.create(GeolocationPosition.prototype);
    Object.defineProperty(pos, 'coords', { value: coords, enumerable: true });
    Object.defineProperty(pos, 'timestamp', { value: ts, enumerable: true });
    Object.defineProperty(pos, 'toJSON', { value: () => ({ coords: { ...c }, timestamp: ts }) });
    return pos;
  }

  const deliver = (cb) => setTimeout(() => cb && cb(makePosition()), 30 + Math.random() * 120);

  // Switch a watch between fake and real source
  function sync(w) {
    if (on()) {
      if (w.realId != null) { real.clear.call(w.geo, w.realId); w.realId = null; }
      deliver(w.ok);
    } else if (w.realId == null) {
      w.realId = real.watch.call(w.geo, w.ok, w.err, w.opts);
    }
  }

  document.addEventListener(EVT, (e) => {
    try { cfg = JSON.parse(e.detail); } catch { return; }
    waiters.splice(0).forEach((f) => f());
    watches.forEach(sync);
  });

  // Wrap while keeping native toString/name
  const wrap = (fn, apply) => new Proxy(fn, { apply: (t, self, args) => apply(self, args) });

  G.getCurrentPosition = wrap(real.get, (self, [ok, err, opts]) => {
    ready().then(() => (on() ? deliver(ok) : real.get.call(self, ok, err, opts)));
  });

  G.watchPosition = wrap(real.watch, (self, [ok, err, opts]) => {
    const id = nextId++;
    const w = { geo: self, ok, err, opts, realId: null };
    watches.set(id, w);
    ready().then(() => watches.has(id) && sync(w));
    return id;
  });

  G.clearWatch = wrap(real.clear, (self, [id]) => {
    const w = watches.get(id);
    if (!w) return real.clear.call(self, id);
    if (w.realId != null) real.clear.call(w.geo, w.realId);
    watches.delete(id);
  });

  // Report geolocation permission as granted while spoofing
  if (realQuery) {
    Permissions.prototype.query = wrap(realQuery, (self, args) => {
      const p = realQuery.apply(self, args);
      if (!args[0] || args[0].name !== 'geolocation') return p;
      return Promise.all([p, ready()]).then(([status]) => {
        if (on()) Object.defineProperty(status, 'state', { value: 'granted', configurable: true });
        return status;
      });
    });
  }
})();
