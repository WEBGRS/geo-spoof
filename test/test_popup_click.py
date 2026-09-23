# Click the popup buttons and report errors / resulting storage
import json, shutil, tempfile, pathlib
from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).resolve().parent.parent
tmp = pathlib.Path(tempfile.mkdtemp())
ext = tmp / "ext"
shutil.copytree(ROOT / "extension", ext)
# The extension already ships a service worker; nothing to patch.

with sync_playwright() as p:
    ctx = p.chromium.launch_persistent_context(str(tmp / "profile"), headless=True, channel="chromium",
        args=[f"--disable-extensions-except={ext}", f"--load-extension={ext}"])
    sw = ctx.service_workers[0] if ctx.service_workers else ctx.wait_for_event("serviceworker")
    ext_id = sw.url.split("/")[2]

    pop = ctx.new_page()
    errs, logs = [], []
    pop.on("pageerror", lambda e: errs.append("PAGEERROR: " + str(e)))
    pop.on("console", lambda m: logs.append(f"{m.type}: {m.text}"))
    pop.goto(f"chrome-extension://{ext_id}/popup.html")
    pop.wait_for_timeout(700)

    print("visible/enabled save:", pop.is_visible("#save"), pop.is_enabled("#save"))
    print("box:", pop.locator("#save").bounding_box())
    # What element actually receives the click at that point?
    print("elementFromPoint:", pop.evaluate("""() => {
        const b = document.getElementById('save').getBoundingClientRect();
        const el = document.elementFromPoint(b.x + b.width/2, b.y + b.height/2);
        return el ? el.outerHTML.slice(0,80) : null; }"""))

    pop.fill("#lat", "48.8584"); pop.fill("#lng", "2.2945")
    pop.click("#save")
    pop.wait_for_timeout(500)
    print("state text:", pop.text_content("#state"))
    print("stored cfg:", sw.evaluate("chrome.storage.local.get('cfg')"))

    pop.click(".switch")  # the visible track; the checkbox itself is opacity:0
    pop.wait_for_timeout(400)
    print("after toggle:", pop.text_content("#state"), sw.evaluate("chrome.storage.local.get('cfg')"))

    pop.fill("#q", "Eiffel Tower")
    pop.click("#fav"); pop.wait_for_timeout(400)
    print("favs:", sw.evaluate("chrome.storage.local.get('favs')"))
    print("errors:", errs)
    print("console:", logs)
    ctx.close()
