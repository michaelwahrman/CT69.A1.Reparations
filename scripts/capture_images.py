"""Regenerate images/*.png from index.html with a headless Chromium-family browser (Edge on Windows, chromium on Linux).
Runs in the background; it never drives the user's desktop.  Usage: python scripts/capture_images.py"""
import os, shutil, subprocess, tempfile, pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
CANDIDATES = [r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe", r"C:\Program Files\Google\Chrome\Application\chrome.exe",
              shutil.which("chromium") or "", shutil.which("chromium-browser") or "", shutil.which("google-chrome") or ""]
BROWSER = next((c for c in CANDIDATES if c and os.path.exists(c)), None)
SHOTS = [("map_pct_r1.png", "rate=0.01", 900), ("map_cost_r1_info.png", "rate=0.01&metric=cost&info=1", 1300),
         ("map_value_r3_log.png", "rate=0.03&metric=value", 900), ("map_national_r0_info.png", "rate=0&mode=national_spread&info=1", 1300)]

if not BROWSER:
    raise SystemExit("No headless Chromium/Edge found; images not regenerated.")
(ROOT / "images").mkdir(exist_ok=True)
url = (ROOT / "index.html").as_uri()
for name, q, h in SHOTS:
    with tempfile.TemporaryDirectory() as prof:
        subprocess.run([BROWSER, "--headless=new", "--enable-unsafe-swiftshader", "--use-angle=swiftshader", "--hide-scrollbars",
                        f"--window-size=1400,{h}", f"--user-data-dir={prof}", f"--screenshot={ROOT / 'images' / name}", f"{url}?{q}"],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=120)
    print(name, (ROOT / "images" / name).stat().st_size, "bytes")
