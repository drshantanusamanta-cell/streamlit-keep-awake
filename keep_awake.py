"""Wake / keep awake every Streamlit Community Cloud app listed in apps.txt.
Opens each app in headless Chromium (a real visit with JS + WebSocket),
clicks the "Yes, get this app back up!" button if the app is asleep,
and exits non-zero if any app fails so GitHub emails you.
"""
import sys
from pathlib import Path
from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

WAKE_TEXT = "Yes, get this app back up"
urls = [u.strip() for u in Path("apps.txt").read_text().splitlines()
        if u.strip() and not u.strip().startswith("#")]

failed = []
with sync_playwright() as p:
    browser = p.chromium.launch()
    for url in urls:
        page = browser.new_page()
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=60_000)
            page.wait_for_timeout(8_000)  # let the shell render
            btn = page.get_by_role("button", name=WAKE_TEXT)
            if btn.count() > 0:
                btn.first.click()
                # wait until the sleep screen is gone
                btn.first.wait_for(state="detached", timeout=180_000)
                print(f"WOKE   {url}")
            else:
                print(f"AWAKE  {url}")
            page.wait_for_timeout(15_000)  # stay connected long enough to count as a visit
        except PWTimeout:
            print(f"FAIL   {url} (timeout)")
            failed.append(url)
        except Exception as e:
            print(f"FAIL   {url} ({e})")
            failed.append(url)
        finally:
            page.close()
    browser.close()

sys.exit(1 if failed else 0)
