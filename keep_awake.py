"""Wake / keep awake every Streamlit Community Cloud app listed in apps.txt.

v2: besides clicking "Yes, get this app back up!", it now reads the page
(including the app's inner frame) and reports FAIL when the app shows an
error or never finishes starting, instead of wrongly reporting AWAKE.
"""
import sys
from pathlib import Path
from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

WAKE_TEXT = "Yes, get this app back up"

# Text that means the app is NOT healthy, even though no sleep button is shown
ERROR_MARKERS = {
    "Error running app": "app crashed while running",
    "Oh no.": "app crashed while running",
    "Traceback (most recent call last)": "Python error on screen",
    "ModuleNotFoundError": "missing package in requirements.txt",
    "ImportError": "import failed (check requirements.txt)",
    "Your app is in the oven": "still building / starting",
    "is having trouble loading": "app failed to load",
    "Something went wrong": "platform error",
}

urls = [u.strip() for u in Path("apps.txt").read_text().splitlines()
        if u.strip() and not u.strip().startswith("#")]


def page_text(page):
    """Visible text of the page plus every frame (the app runs in an iframe)."""
    parts = []
    for frame in page.frames:
        try:
            parts.append(frame.locator("body").inner_text(timeout=5_000))
        except Exception:
            pass
    return "\n".join(parts)


def find_problem(page):
    text = page_text(page)
    for marker, meaning in ERROR_MARKERS.items():
        if marker in text:
            return f"{meaning} [saw: '{marker}']"
    return None


failed = []
with sync_playwright() as p:
    browser = p.chromium.launch()
    for url in urls:
        page = browser.new_page()
        status = "AWAKE"
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=60_000)
            page.wait_for_timeout(8_000)
            btn = page.get_by_role("button", name=WAKE_TEXT)
            if btn.count() > 0:
                btn.first.click()
                btn.first.wait_for(state="detached", timeout=180_000)
                status = "WOKE"
            # give the app time to boot / render, checking for errors as we go
            problem = None
            for _ in range(6):            # up to ~60 s
                page.wait_for_timeout(10_000)
                problem = find_problem(page)
                if problem and "still building" not in problem:
                    break                 # real error: stop waiting
                if not problem:
                    break                 # healthy
            if problem:
                print(f"FAIL   {url} -> {problem}")
                failed.append(url)
            else:
                print(f"{status:<6} {url}")
        except PWTimeout:
            print(f"FAIL   {url} -> timeout (app did not respond)")
            failed.append(url)
        except Exception as e:
            print(f"FAIL   {url} -> {e}")
            failed.append(url)
        finally:
            page.close()
    browser.close()

sys.exit(1 if failed else 0)
