// Relay stored config into the page world
(() => {
  const EVT = '__geo_spoof_cfg__';
  const send = (cfg) =>
    document.dispatchEvent(new CustomEvent(EVT, { detail: JSON.stringify(cfg || { enabled: false }) }));

  // After the extension is reloaded, this script is orphaned: stop spoofing
  // instead of pinning the page to a stale config forever.
  const alive = () => {
    try { return !!chrome.runtime?.id; } catch { return false; }
  };
  const giveUp = () => { clearInterval(timer); send({ enabled: false, stale: true }); };

  const pull = () => {
    if (!alive()) return giveUp();
    try {
      chrome.storage.local.get('cfg').then((r) => send(r.cfg), giveUp);
    } catch { giveUp(); }
  };

  const timer = setInterval(() => { if (!alive()) giveUp(); }, 2000);
  pull();

  try {
    chrome.storage.onChanged.addListener((changes, area) => {
      if (area === 'local' && changes.cfg) send(changes.cfg.newValue);
    });
  } catch { giveUp(); }
})();
