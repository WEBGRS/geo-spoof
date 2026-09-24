# Regenerate README screenshots: popup + a page reading the spoofed location
import shutil, tempfile, threading, http.server, functools, pathlib
from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "docs"
LAT, LNG, ACC = 48.8584, 2.2945, 15

PAGE = """<!doctype html><meta charset="utf-8"><title>Where am I?</title>
<link rel="stylesheet" href="lib/leaflet.css">
<style>body{margin:0;font:15px system-ui,sans-serif}#bar{padding:12px 16px;background:#111;color:#fff}
#bar code{background:#333;padding:2px 6px;border-radius:4px}#map{height:420px}</style>
<div id="bar">navigator.geolocation.getCurrentPosition() &rarr; <code id="out">waiting...</code></div>
<div id="map"></div><script src="lib/leaflet.js"></script><script>
navigator.geolocation.getCurrentPosition(p => {
  const {latitude: a, longitude: o, accuracy: c} = p.coords;
  document.getElementById('out').textContent = `${a.toFixed(4)}, ${o.toFixed(4)} (±${c} m)`;
  const m = L.map('map').setView([a, o], 16);
  L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {attribution: '&copy; OpenStreetMap'}).addTo(m);
  L.marker([a, o]).addTo(m); L.circle([a, o], {radius: c}).addTo(m);
  m.whenReady(() => setTimeout(() => window.done = true, 2500));
});
</script>"""

tmp = pathlib.Path(tempfile.mkdtemp())
ext = tmp / "ext"
shutil.copytree(ROOT / "extension", ext)
site = tmp / "site"
shutil.copytree(ROOT / "extension" / "lib", site / "lib")
(site / "index.html").write_text(PAGE, encoding="utf-8")
srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(site)))
threading.Thread(target=srv.serve_forever, daemon=True).start()

with sync_playwright() as p:
    ctx = p.chromium.launch_persistent_context(str(tmp / "profile"), headless=True, channel="chromium",
        device_scale_factor=2, args=[f"--disable-extensions-except={ext}", f"--load-extension={ext}"])
    sw = ctx.service_workers[0] if ctx.service_workers else ctx.wait_for_event("serviceworker")
    ext_id = sw.url.split("/")[2]
    sw.evaluate(f"chrome.storage.local.set({{cfg:{{enabled:true,lat:{LAT},lng:{LNG},accuracy:{ACC},altitude:'',jitter:false}},"
                "favs:[{name:'Eiffel Tower',lat:48.8584,lng:2.2945},{name:'Tokyo Tower',lat:35.6586,lng:139.7454}]})")

    # Popup
    pop = ctx.new_page()
    pop.set_viewport_size({"width": 380, "height": 200})
    pop.goto(f"chrome-extension://{ext_id}/popup.html")
    pop.wait_for_timeout(3000)
    pop.screenshot(path=str(OUT / "popup.png"), full_page=True)

    # Demo page
    page = ctx.new_page()
    page.set_viewport_size({"width": 800, "height": 470})
    page.goto(f"http://localhost:{srv.server_port}/index.html")
    page.wait_for_function("window.done", timeout=20000)
    page.screenshot(path=str(OUT / "demo-page.png"))
    ctx.close()
print("saved to", OUT)
