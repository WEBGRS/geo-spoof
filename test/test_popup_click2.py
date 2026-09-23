import json, shutil, tempfile, pathlib
from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).resolve().parent.parent
tmp = pathlib.Path(tempfile.mkdtemp()); ext = tmp / "ext"
shutil.copytree(ROOT / "extension", ext)
# The extension already ships a service worker; nothing to patch.

with sync_playwright() as p:
    ctx = p.chromium.launch_persistent_context(str(tmp / "profile"), headless=True, channel="chromium",
        args=[f"--disable-extensions-except={ext}", f"--load-extension={ext}"])
    sw = ctx.service_workers[0] if ctx.service_workers else ctx.wait_for_event("serviceworker")
    pop = ctx.new_page()
    pop.goto(f"chrome-extension://{sw.url.split('/')[2]}/popup.html")
    pop.wait_for_timeout(700)

    print("content height:", pop.evaluate("document.body.scrollHeight"))
    pop.click(".switch")   # click the visible track, not the hidden input
    pop.wait_for_timeout(400)
    print("after switch click:", pop.text_content("#state"), sw.evaluate("chrome.storage.local.get('cfg')"))

    # Does wheel over the map scroll the popup or zoom the map?
    pop.set_viewport_size({"width": 380, "height": 400})
    pop.wait_for_timeout(300)
    box = pop.locator("#map").bounding_box()
    pop.mouse.move(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)
    before_zoom = pop.evaluate("document.scrollingElement.scrollTop")
    pop.mouse.wheel(0, 300); pop.wait_for_timeout(600)
    print("scrollTop before/after wheel over map:", before_zoom, pop.evaluate("document.scrollingElement.scrollTop"))
    ctx.close()
