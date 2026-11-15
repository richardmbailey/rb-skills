import json
from pathlib import Path
from playwright.sync_api import sync_playwright
root=Path(__file__).resolve().parents[3]
report=root/'examples/numerical-assurance-repeat/report.html'
out=root/'docs/rb-build-test-suite-specification/repeat-trial'
with sync_playwright() as p:
 browser=p.chromium.launch(executable_path='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',headless=True)
 context=browser.new_context(java_script_enabled=False,offline=True,viewport={'width':1200,'height':1000})
 page=context.new_page(); errors=[]; page.on('pageerror',lambda err:errors.append(str(err)))
 page.goto(report.as_uri()); page.screenshot(path=str(out/'report-desktop.png'))
 text=page.locator('body').inner_text()
 for value in ('87 pytest','Six predeclared','2.715727','37 independent'):
  assert value in text,value
 links=page.locator('a').evaluate_all('(nodes) => nodes.map(n => n.getAttribute("href"))')
 assert all((report.parent/link).exists() for link in links)
 page.set_viewport_size({'width':390,'height':844})
 page.screenshot(path=str(out/'report-mobile.png'))
 page.locator('section').last.scroll_into_view_if_needed()
 page.screenshot(path=str(out/'report-mobile-bottom.png'))
 overflow=page.evaluate('document.documentElement.scrollWidth > window.innerWidth')
 assert not overflow
 page.emulate_media(media='print'); assert page.locator('body').is_visible()
 assert not errors
 result={'offline':True,'javascript_enabled':False,'desktop_width':1200,'mobile_width':390,'mobile_overflow':overflow,'checked_relative_links':links,'page_errors':errors,'status':'PASS','limits':'Basic rendering, metric presence, links and mobile layout; not a full accessibility audit.'}
 (out/'report-render-check.json').write_text(json.dumps(result,indent=2)+'\n')
 browser.close()
print(json.dumps(result))
