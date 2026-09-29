"""Exercise Select all and recover from an empty hosting error response."""
import json
import os
import tempfile
from pathlib import Path
from playwright.sync_api import sync_playwright

base = os.environ.get('STYLOMETRY_TEST_URL', 'http://127.0.0.1:8000')
with sync_playwright() as p:
    browser = p.chromium.launch(executable_path='/usr/bin/google-chrome', headless=True, args=['--no-sandbox'])
    page = browser.new_page()
    page.set_default_timeout(120000)
    errors = []
    page.on('pageerror', lambda error: errors.append(str(error)))

    def complete(eras):
        page.wait_for_function("""expected => !busy && result &&
            JSON.stringify(result.config.eras) === JSON.stringify(expected) &&
            $('status').textContent === t('Experiment complete. Results reflect the settings recorded below.')""", arg=eras)
        assert page.locator('#error').is_hidden()
        assert page.locator('.tree-leaf').count() == len(eras) * 10
        assert page.locator('.pca-sample').count() == len(eras) * 10

    page.goto(base, wait_until='domcontentloaded')
    complete(['Quran', 'PreIslamic', 'Modern'])
    all_eras = page.locator('[name=era]').evaluate_all('(items) => items.map(e => e.value)')
    page.locator('#language').select_option('ar')
    assert page.locator('#select-all').inner_text() == 'تحديد الكل'
    page.locator('#select-all').click()
    complete(all_eras)
    page.locator('#pca-tab').click()
    assert page.locator('#pca-chart').is_visible()
    with tempfile.TemporaryDirectory() as directory:
        with page.expect_download() as info:
            page.locator('#download').click()
        path = Path(directory) / 'all-groups.json'
        info.value.save_as(str(path))
        exported = json.loads(path.read_text())
        assert exported['config']['eras'] == all_eras
        assert len(exported['samples']) == len(exported['feature_matrix']) == 110
        assert all(sample['text'] and sample['raw_text'] for sample in exported['samples'])
    print('Arabic Select all: 110 samples in both charts and complete JSON export.', flush=True)

    for eras in [['Quran', 'PreIslamic', 'Umayyad', 'Abbasid', 'Andalusian', 'Fatimid', 'Modern'],
                 ['PreIslamic', 'Modern'], all_eras]:
        page.evaluate("""eras => {
            document.querySelectorAll('[name=era]').forEach(el => el.checked = eras.includes(el.value));
            controlsChanged();
        }""", eras)
        complete(eras)
    print('Seven-group, poetry-only, and all-group selection changes passed.', flush=True)

    # Simulate the empty HTTP 500 response previously returned by Cloud Run.
    page.route('**/api/experiment', lambda route: route.fulfill(status=500, body='', content_type='text/html'), times=1)
    page.locator('[name=era][value=Modern]').uncheck()
    page.locator('#error').wait_for(state='visible')
    assert 'تعذّر على الخادم إرسال النتائج كاملة (500)' in page.locator('#error').inner_text()
    page.locator('[name=era][value=Modern]').check()
    complete(all_eras)
    assert not errors, errors
    browser.close()
    print('Empty server responses show a readable message; changing selection recovers.', flush=True)
