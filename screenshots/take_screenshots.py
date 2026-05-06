from playwright.sync_api import sync_playwright
import pathlib

here = pathlib.Path(__file__).parent
out  = here / "output"
out.mkdir(exist_ok=True)

pages_config = [
    ("mockup.html",          "dashboard_overview.png",  ".svc-table"),
    ("mockup_services.html", "dashboard_services.png",  ".svc-grid"),
    ("mockup_logs.html",     "dashboard_logs.png",      ".log-table"),
    ("mockup_ai.html",       "dashboard_ai.png",        ".anomaly-card"),
    ("mockup_sdk.html",      "dashboard_sdk.png",       ".feat-card"),
]

with sync_playwright() as p:
    browser = p.chromium.launch()

    for html_file, out_file, scroll_selector in pages_config:
        html_path = (here / html_file).resolve().as_uri()
        page = browser.new_page(viewport={"width": 1440, "height": 860})
        page.goto(html_path)
        page.wait_for_timeout(1800)
        page.screenshot(path=str(out / out_file), full_page=False)
        print(f"  Saved: {out_file}")
        page.close()

    browser.close()
    print("\nAll screenshots saved to screenshots/output/")
