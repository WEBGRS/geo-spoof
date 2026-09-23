// Badge shows whether spoofing is active
async function paint() {
  const { cfg } = await chrome.storage.local.get('cfg');
  const on = !!(cfg && cfg.enabled);
  await chrome.action.setBadgeText({ text: on ? 'ON' : '' });
  await chrome.action.setBadgeBackgroundColor({ color: '#1db954' });
  await chrome.action.setTitle({
    title: on ? `Geo Spoof: ${cfg.lat}, ${cfg.lng}` : 'Geo Spoof: 关闭',
  });
}

chrome.runtime.onInstalled.addListener(paint);
chrome.runtime.onStartup.addListener(paint);
chrome.storage.onChanged.addListener((c, area) => { if (area === 'local' && c.cfg) paint(); });
paint();
