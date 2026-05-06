from playwright.sync_api import sync_playwright
import os, pathlib

here = pathlib.Path(__file__).parent
html = (here / "mockup.html").resolve().as_uri()
out  = here / "output"
out.mkdir(exist_ok=True)

with sync_playwright() as p:
    browser = p.chromium.launch()

    # 1. Dashboard overview — full width
    page = browser.new_page(viewport={"width": 1440, "height": 860})
    page.goto(html)
    page.wait_for_timeout(1800)
    page.screenshot(path=str(out / "dashboard_overview.png"), full_page=False)

    # 2. Services section (scroll to services table)
    page.evaluate("document.querySelector('.svc-table').scrollIntoView({behavior:'instant',block:'center'})")
    page.wait_for_timeout(400)
    page.screenshot(path=str(out / "dashboard_services.png"), full_page=False)

    # 3. AI panel close-up
    page.evaluate("document.querySelector('.ai-panel').scrollIntoView({behavior:'instant',block:'center'})")
    page.wait_for_timeout(400)
    page.screenshot(path=str(out / "dashboard_ai.png"), full_page=False)

    # 4. Logs section
    page.evaluate("document.querySelector('.log-entry').scrollIntoView({behavior:'instant',block:'center'})")
    page.wait_for_timeout(400)
    page.screenshot(path=str(out / "dashboard_logs.png"), full_page=False)

    # 5. Sidebar close-up (narrow viewport)
    page2 = browser.new_page(viewport={"width": 320, "height": 700})
    page2.goto(html)
    page2.wait_for_timeout(1200)
    page2.evaluate("document.querySelector('.sidebar').style.borderRadius='0'")
    elem = page2.query_selector(".sidebar")
    elem.screenshot(path=str(out / "sidebar.png"))

    browser.close()
    print("Screenshots saved to screenshots/output/")
