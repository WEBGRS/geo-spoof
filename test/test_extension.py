# End-to-end check: load extension in Chromium, verify spoofed geolocation
import json, shutil, tempfile, threading, http.server, functools, pathlib
from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).resolve().parent.parent
PAGE = """<!doctype html><script>
window.results = {};
navigator.geolocation.getCurrentPosition(p => results.get = {lat:p.coords.latitude, lng:p.coords.longitude,
  acc:p.coords.accuracy, inst: p instanceof GeolocationPosition && p.coords instanceof GeolocationCoordinates,
  json: JSON.stringify(p)}, e => results.get = {err:e.code});
const id = navigator.geolocation.watchPosition(p => (results.watch = results.watch || []).push([p.coords.latitude, p.coords.longitude]));
navigator.permissions.query({name:'geolocation'}).then(s => results.perm = s.state);
results.native = navigator.geolocation.getCurrentPosition.toString();
</script>"""

# Test copy with a service worker for storage access
tmp = pathlib.Path(tempfile.mkdtemp())
ext = tmp / "ext"
shutil.copytree(ROOT / "extension", ext)
# The extension already ships a service worker; nothing to patch.

# Serve test page on localhost (secure context)
site = tmp / "site"; site.mkdir()
(site / "index.html").write_text(PAGE)
srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(site)))
threading.Thread(target=srv.serve_forever, daemon=True).start()
url = f"http://localhost:{srv.server_port}/index.html"

def run(page):
    page.goto(url)
    page.wait_for_function("results.get && results.perm && results.watch", timeout=8000)
    return page.evaluate("results")

with sync_playwright() as p:
    ctx = p.chromium.launch_persistent_context(str(tmp / "profile"), headless=True, channel="chromium",
        args=[f"--disable-extensions-except={ext}", f"--load-extension={ext}"])
    sw = ctx.service_workers[0] if ctx.service_workers else ctx.wait_for_event("serviceworker")
    ext_id = sw.url.split("/")[2]

    sw.evaluate("chrome.storage.local.set({cfg:{enabled:true,lat:35.6586,lng:139.7454,accuracy:15,altitude:'',jitter:false}})")
    page = ctx.new_page()
    r = run(page)
    print("ON :", r)
    assert abs(r["get"]["lat"] - 35.6586) < 1e-9 and abs(r["get"]["lng"] - 139.7454) < 1e-9
    assert r["get"]["inst"] and "35.6586" in r["get"]["json"] and r["perm"] == "granted"
    assert "[native code]" in r["native"]

    # Live switch of an active watch
    sw.evaluate("chrome.storage.local.set({cfg:{enabled:true,lat:48.8584,lng:2.2945,accuracy:15,altitude:'',jitter:false}})")
    page.wait_for_function("results.watch.some(w => Math.abs(w[0]-48.8584) < 1e-6)", timeout=5000)
    print("watch switched:", page.evaluate("results.watch"))

    # Jitter stays within accuracy
    sw.evaluate("chrome.storage.local.set({cfg:{enabled:true,lat:10,lng:10,accuracy:30,altitude:'',jitter:true}})")
    r = run(page)
    d = ((r["get"]["lat"] - 10) ** 2 + (r["get"]["lng"] - 10) ** 2) ** 0.5 * 111320
    print(f"jitter offset {d:.1f} m"); assert 0 < d < 30

    # Disabled: falls through to real API (headless has no position -> error or real coords)
    sw.evaluate("chrome.storage.local.set({cfg:{enabled:false,lat:1,lng:1}})")
    page.goto(url); page.wait_for_timeout(1500)
    r = page.evaluate("results")
    print("OFF:", r); assert not (r.get("get") or {}).get("lat") == 1

    # Popup renders without errors
    errs = []
    pop = ctx.new_page(); pop.on("pageerror", lambda e: errs.append(str(e)))
    pop.goto(f"chrome-extension://{ext_id}/popup.html"); pop.wait_for_timeout(800)
    print("popup lat field:", pop.input_value("#lat"), "errors:", errs); assert not errs
    pop.screenshot(path=str(ROOT / "test" / "popup.png"))
    ctx.close()
print("ALL PASS")
