"""Wake / keep awake every Streamlit Community Cloud app listed in apps.txt.

v3 — an app only counts as AWAKE when it has really loaded:
  * positive check: Streamlit's app container is on screen and shows content
    (v2 reported AWAKE as soon as no error text was visible — a blank, half-started
    page passed)
  * catches Streamlit's error pages (redirect to share.streamlit.io/errors/...,
    "You do not have access to this app or it does not exist", source-download and
    resource-limit failures) that v2 did not recognise
  * after a wake-up, waits up to ~3 minutes for the app to boot instead of ~60 s
  * one retry a minute later before reporting FAIL, so a single slow response does
    not trigger a failure e-mail
  * writes a results table to the GitHub Actions run page
"""
import os
import sys
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

WAKE_TEXT = "Yes, get this app back up"
BOOT_WAIT_S = 180        # max wait for an app to finish loading after the visit / wake-up
POLL_S = 5
STAY_S = 15              # stay connected after it loads, so the visit counts
RETRY_PAUSE_S = 60

# Text that means the app is NOT healthy
ERROR_MARKERS = {
    "You do not have access to this app or it does not exist": "app not found / no access",
    "Failed to download the sources": "Streamlit could not download the repo (private? renamed?)",
    "has gone over its resource limits": "app went over its memory/CPU limit",
    "This app has encountered an error": "app crashed",
    "Error running app": "app crashed while running",
    "Oh no.": "app crashed while running",
    "Traceback (most recent call last)": "Python error on screen",
    "ModuleNotFoundError": "missing package in requirements.txt",
    "ImportError": "import failed (check requirements.txt)",
    "is having trouble loading": "app failed to load",
    "Something went wrong": "platform error",
}
STILL_STARTING = ("Your app is in the oven", "Please wait", "Spinning up", "is booting")

urls = [u.strip() for u in Path(__file__).with_name("apps.txt").read_text().splitlines()
        if u.strip() and not u.strip().startswith("#")]


def page_text(page) -> str:
    """Visible text of the page plus every frame (the app itself runs in an inner frame)."""
    parts = []
    for frame in page.frames:
        try:
            parts.append(frame.locator("body").inner_text(timeout=3_000))
        except Exception:  # noqa: BLE001
            pass
    return "\n".join(parts)


def app_loaded(page) -> bool:
    """True when Streamlit's app container is rendered with real content in any frame."""
    for frame in page.frames:
        try:
            app = frame.locator('[data-testid="stApp"]')
            if app.count() and len(app.first.inner_text(timeout=3_000).strip()) > 40:
                return True
        except Exception:  # noqa: BLE001
            pass
    return False


def check(page) -> tuple[str, str]:
    """('ok' | 'error' | 'pending', detail)."""
    if "/errors/" in page.url:
        return "error", f"Streamlit error page ({page.url})"
    text = page_text(page)
    for marker, meaning in ERROR_MARKERS.items():
        if marker in text:
            return "error", f"{meaning} [saw: '{marker}']"
    if app_loaded(page):
        return "ok", ""
    if any(s in text for s in STILL_STARTING):
        return "pending", "still starting"
    return "pending", "page not rendered yet"


def visit(browser, url: str) -> tuple[str, str]:
    """One attempt. Returns (status, detail) with status AWAKE / WOKE / FAIL."""
    page = browser.new_page()
    try:
        page.goto(url, wait_until="domcontentloaded", timeout=60_000)
        page.wait_for_timeout(5_000)
        woke = False
        btn = page.get_by_role("button", name=WAKE_TEXT)
        if btn.count() > 0:
            btn.first.click()
            woke = True
            try:
                btn.first.wait_for(state="detached", timeout=BOOT_WAIT_S * 1_000)
            except Exception:  # noqa: BLE001
                return "FAIL", "wake button clicked but the app never started"
        deadline = time.time() + BOOT_WAIT_S
        state, detail = check(page)
        while state == "pending" and time.time() < deadline:
            page.wait_for_timeout(POLL_S * 1_000)
            state, detail = check(page)
        if state == "ok":
            page.wait_for_timeout(STAY_S * 1_000)
            return ("WOKE" if woke else "AWAKE"), ""
        if state == "pending":
            return "FAIL", f"did not finish loading within {BOOT_WAIT_S}s ({detail})"
        return "FAIL", detail
    except Exception as e:  # noqa: BLE001
        return "FAIL", f"{type(e).__name__}: {str(e).splitlines()[0][:150]}"
    finally:
        page.close()


def main() -> int:
    results = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        for url in urls:
            status, detail = visit(browser, url)
            if status == "FAIL":
                print(f"RETRY  {url} -> {detail}", flush=True)
                time.sleep(RETRY_PAUSE_S)
                status, detail = visit(browser, url)
            line = f"{status:<6} {url}" + (f" -> {detail}" if detail else "")
            print(line, flush=True)
            results.append((status, url, detail))
        browser.close()

    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        icon = {"AWAKE": "✅", "WOKE": "⏰", "FAIL": "❌"}
        rows = "\n".join(f"| {icon[s]} {s} | {u} | {d} |" for s, u, d in results)
        with open(summary, "a", encoding="utf-8") as fh:
            fh.write("### Streamlit apps\n\n| Status | App | Detail |\n|---|---|---|\n" + rows + "\n")

    failed = [r for r in results if r[0] == "FAIL"]
    print(f"\n{len(results) - len(failed)}/{len(results)} apps OK")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
