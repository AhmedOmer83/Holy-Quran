"""Local browser regression: Modern references never become analysis samples."""
from pathlib import Path
from playwright.sync_api import sync_playwright

artifacts = Path(__file__).resolve().parents[1] / 'test-artifacts'

with sync_playwright() as p:
    browser = p.chromium.launch(executable_path='/usr/bin/google-chrome', headless=True, args=['--no-sandbox'])
    page = browser.new_page(viewport={'width':1440, 'height':1000})
    page.set_default_timeout(60000)
    errors = []
    page.on('pageerror', lambda error: errors.append(str(error)))
    page.goto('http://127.0.0.1:8000')
    page.wait_for_function('typeof FEATURE_EXAMPLES_ENABLED !== \"undefined\"')
    if not page.evaluate('FEATURE_EXAMPLES_ENABLED'):
        assert page.locator('.feature-example-toggle').count() == 0
        browser.close()
        print('Quotation UI checks skipped: examples are temporarily disabled.')
        raise SystemExit(0)
    page.wait_for_function('!busy && !!result')
    page.evaluate("document.querySelectorAll('[name=era]').forEach(e=>e.checked=['Quran','Modern'].includes(e.value)); controlsChanged()")
    page.wait_for_function('!busy && !!result')
    index = page.evaluate("result.features.findIndex(f=>f.name==='من')")
    assert index >= 0
    page.locator('.feature-example-toggle').nth(index).click()
    modern = page.locator('.feature-examples-row:visible [data-era="Modern"]')
    assert 'The corrected source does not cover any' in modern.inner_text()
    assert 'This feature is counted in the clustering' in modern.inner_text()
    assert '289.86' in modern.locator('.feature-analysis-evidence').inner_text()
    assert '10 of 10' in modern.locator('.feature-analysis-evidence').inner_text()
    page.evaluate('window.savedSnapshot=JSON.stringify(result); window.savedExperiment=result')
    modern.locator('[data-reference-era]').click()
    modern.locator('.feature-reference-example').wait_for()
    assert 'outside the analysis samples' in modern.inner_text()
    assert modern.locator('.feature-example-poet bdi').inner_text().strip()
    assert modern.locator('mark').inner_text() == 'من'
    assert page.evaluate('result===window.savedExperiment && JSON.stringify(result)===window.savedSnapshot')
    page.locator('.feature-examples-row:visible').screenshot(path=str(artifacts / 'modern-reference-example.png'))
    page.select_option('#language', 'ar')
    assert 'خارج عينات التحليل' in modern.inner_text()
    assert 'الشاعر:' in modern.inner_text() or 'ينسب المصدر' in modern.inner_text()
    page.set_viewport_size({'width':390, 'height':844})
    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth + 1')
    modern.screenshot(path=str(artifacts / 'modern-reference-example-ar.png'))
    with page.expect_download() as download:
        page.locator('#download').click()
    assert download.value.path().read_text() == page.evaluate('JSON.stringify(result,null,2)')
    assert page.evaluate('JSON.stringify(result)===window.savedSnapshot')
    print('Modern reference, poet, scope label, Arabic/mobile, and unchanged export verified.', flush=True)

    # A reference response from previous settings cannot enter a new experiment.
    delayed = []
    def hold(route):
        delayed.append((route, route.fetch()))
        page.evaluate('window.referenceHeld=true')
    page.route('**/api/reference-example', hold, times=1)
    second = page.evaluate("result.features.findIndex(f=>f.name==='في')")
    page.locator('.feature-example-toggle').nth(second).click()
    page.locator('.feature-examples-row:visible [data-reference-era="Modern"]').click()
    page.wait_for_function('window.referenceHeld===true')
    page.evaluate("$('seed').value='43'; controlsChanged()")
    delayed[0][0].fulfill(response=delayed[0][1])
    page.wait_for_function('!busy && !!result && result.config.seed===43')
    assert page.evaluate('referenceExamples.size===0')
    assert page.locator('.feature-reference-example').count() == 0
    assert not errors, errors
    browser.close()
    print('Old reference responses are discarded after settings change.', flush=True)
