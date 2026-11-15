"""External offline rendering check, not numerical project infrastructure."""
import json
from pathlib import Path
from playwright.sync_api import sync_playwright

HERE = Path(__file__).resolve().parent
REPORT = HERE.parents[2] / 'examples/numerical-assurance-repeat-2/report.html'
with sync_playwright() as p:
    browser = p.chromium.launch(executable_path='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome', headless=True)
    context = browser.new_context(java_script_enabled=False, offline=True, viewport={'width': 1200, 'height': 1000})
    page = context.new_page()
    errors = []
    page.on('pageerror', lambda error: errors.append(str(error)))
    page.goto(REPORT.as_uri())
    text = page.locator('body').inner_text()
    for expected in ('80 passed', '15/20 (75%)', '85 lines', '162 supporting lines', 'two missing historical'):
        assert expected in text, expected
    links = page.locator('a').evaluate_all('(nodes) => nodes.map(n => n.getAttribute("href"))')
    assert all((REPORT.parent / link).exists() for link in links)
    page.screenshot(path=str(HERE / 'report-desktop.png'))
    page.set_viewport_size({'width': 390, 'height': 844})
    assert not page.evaluate('document.documentElement.scrollWidth > window.innerWidth')
    page.screenshot(path=str(HERE / 'report-mobile.png'))
    page.locator('h2').last.scroll_into_view_if_needed()
    page.screenshot(path=str(HERE / 'report-mobile-bottom.png'))
    page.emulate_media(media='print')
    assert page.locator('body').is_visible()
    assert not errors
    result = {'status': 'PASS', 'offline': True, 'javascript_enabled': False, 'checked_links': links, 'desktop_width': 1200, 'mobile_width': 390, 'mobile_overflow': False, 'page_errors': errors, 'limit': 'Basic rendering and link checks, not a full accessibility audit.'}
    (HERE / 'report-render-check.json').write_text(json.dumps(result, indent=2) + '\n')
    browser.close()
print(json.dumps(result))
