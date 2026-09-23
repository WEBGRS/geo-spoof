# Geo Spoof

Chrome (MV3) extension that replaces the location websites get from the Geolocation API with coordinates you choose. It does not block location access. Sites still get a position, just the one you set.

## Install

1. Open `chrome://extensions` and turn on **Developer mode**.
2. Click **Load unpacked** and pick the `extension` folder of this repo.
3. Pin the extension, open it, pick a point, turn the switch on.

## Usage

- Click the map or drag the pin to set a point. The search box accepts place names (OpenStreetMap Nominatim), `lat, lng`, or a Google Maps URL.
- Accuracy is reported in `coords.accuracy`. Jitter adds a small random offset (within accuracy/3) to each fix.
- Favorites keep frequently used points.
- Reload the target page after changing settings. Active `watchPosition` callbacks update live.
- The toolbar badge reads `ON` while spoofing.
- After reloading the extension at `chrome://extensions`, reload open tabs too. Their injected scripts are orphaned by the reload; they stop spoofing and fall back to the real API rather than pinning the page to a stale position.

## What it patches

Runs in the page's main world at `document_start` in every frame:

- `getCurrentPosition`, `watchPosition`, `clearWatch` return spoofed positions. The objects pass `instanceof GeolocationPosition` checks and serialize with `toJSON`.
- `navigator.permissions.query({name: 'geolocation'})` reports `granted` while spoofing.
- Patched functions still print `[native code]` from `toString()`.

When disabled, calls go straight to the real API.

## Limits

- Only covers the browser Geolocation API. IP-based location (what a site infers from your IP address) needs a VPN or proxy.
- Time zone (`Intl`, `Date`) is not changed. A site can compare it against the spoofed point.
- Native Windows apps (Weather, Maps) use the Windows location service instead, which this extension does not touch.

## Test

```
python test/test_extension.py
```

Loads the extension into Playwright Chromium and checks spoofed values, live watch switching, jitter bounds, pass-through when disabled, and that the popup loads without errors.
