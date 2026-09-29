"""Browser regression checks for language switching and RTL layout."""
from pathlib import Path
from playwright.sync_api import sync_playwright

artifacts = Path(__file__).resolve().parents[1] / 'test-artifacts'
artifacts.mkdir(exist_ok=True)

with sync_playwright() as p:
    browser = p.chromium.launch(executable_path='/usr/bin/google-chrome', headless=True, args=['--no-sandbox'])
    page = browser.new_page(viewport={'width': 1440, 'height': 1000})
    page.set_default_timeout(60000)
    errors, requests = [], []
    page.on('pageerror', lambda error: errors.append(str(error)))
    page.on('request', lambda request: requests.append(request.url) if request.url.endswith('/api/experiment') else None)

    def complete():
        page.wait_for_function("!busy && result && $('status').textContent === t('Experiment complete. Results reflect the settings recorded below.')")

    page.goto('http://127.0.0.1:8000')
    complete()
    page.locator('#pca-tab').click()
    page.evaluate('window.savedResult = result')
    before = len(requests)
    page.locator('#language').select_option('ar')
    assert page.locator('html').get_attribute('lang') == 'ar'
    assert page.locator('html').get_attribute('dir') == 'rtl'
    assert len(requests) == before
    assert page.evaluate('result === window.savedResult')
    assert page.locator('#pca-chart').is_visible()
    assert page.locator('#feature-rows .feature-example-toggle').count() == 0
    assert page.locator('#feature-rows .feature-data-row').count() == 100
    assert 'تحليل المكونات الرئيسية (PCA)' in page.locator('#pca-tab').inner_text()
    assert 'أكثر 100 كلمة' in page.locator('#feature-title').inner_text()
    assert page.locator('#feature option').first.inner_text() == 'الكلمات الأكثر تكرارًا'
    assert 'المخضرمون' in page.locator('#era-options').inner_text()
    assert 'المقاطع' in page.locator('#introduction').inner_text()
    page.locator('#methods > summary').click()
    assert 'نقاء الفرع' in page.locator('#methodology').inner_text()
    assert page.locator('#pca-chart svg').get_attribute('aria-label').startswith('مخطط')
    with page.expect_download() as download:
        page.locator('#svg-export').click()
    path = artifacts / 'arabic-pca.svg'
    download.value.save_as(str(path))
    assert 'من التباين' in path.read_text()
    # Switching back restores English without resetting the analysis.
    page.locator('#language').select_option('en')
    assert page.locator('html').get_attribute('dir') == 'ltr'
    assert 'Hierarchical clustering (HC)' in page.locator('#tree-tab').inner_text()
    assert page.evaluate('result === window.savedResult')
    page.locator('#language').select_option('ar')
    page.reload()
    complete()
    assert page.locator('#language').input_value() == 'ar'
    assert page.locator('html').get_attribute('dir') == 'rtl'
    print('Language persistence, unchanged analysis, and Arabic SVG verified.', flush=True)

    page.locator('[name=era][value=Quran]').uncheck()
    complete()
    assert page.locator('#focus-rate').inner_text() == 'معدل الجاهلي'
    page.locator('#feature').select_option('char3')
    complete()
    assert 'ثلاثيات الحروف' in page.locator('#result-caption').inner_text()
    assert all(len(name) == 3 for name in page.locator('#feature-rows .arabic').all_text_contents())

    # Change the language while a feature request is outstanding.
    delayed = []
    def hold(route):
        delayed.append((route, route.fetch()))
        page.evaluate('window.heldReady = true')
    page.route('**/api/experiment', hold, times=1)
    page.locator('#feature').select_option('word2')
    page.wait_for_function('window.heldReady === true')
    page.locator('#language').select_option('en')
    assert 'Extracting' in page.locator('#status').inner_text()
    page.locator('#language').select_option('ar')
    delayed[0][0].fulfill(response=delayed[0][1])
    complete()
    assert 'ثنائيات الكلمات' in page.locator('#result-caption').inner_text()
    assert 'اكتملت' in page.locator('#status').inner_text()

    # Completed cross-feature comparisons translate from retained results.
    page.locator('#compare').click()
    page.wait_for_function("!busy && comparisonResults.length === 7")
    assert page.locator('#comparison tbody tr').count() == 7
    assert page.locator('#comparison td').first.inner_text() == 'الكلمات الأكثر تكرارًا'
    before = len(requests)
    page.locator('#language').select_option('en')
    assert page.locator('#comparison td').first.inner_text() == 'Most frequent words'
    assert len(requests) == before
    page.locator('#language').select_option('ar')

    # Translate an actual server validation message and a client selection error.
    page.route('**/api/experiment', lambda route: route.fulfill(status=400, json={'error':'Ward linkage requires Euclidean distance.'}), times=1)
    page.locator('#feature').select_option('words')
    page.locator('#error').wait_for(state='visible')
    assert 'يتطلب ربط وارد' in page.locator('#error').inner_text()
    page.locator('#language').select_option('en')
    assert page.locator('#error').inner_text() == 'Ward linkage requires Euclidean distance.'
    page.locator('#language').select_option('ar')
    page.evaluate("document.querySelectorAll('[name=era]').forEach(e=>e.checked=e.value==='PreIslamic'); controlsChanged()")
    page.wait_for_function("$('error').textContent === t('Choose at least two distinct corpus groups.') && !$('error').hidden")
    assert 'مجموعتين' in page.locator('#error').inner_text()
    page.locator('[name=era][value=Quran]').check()
    complete()
    print('Arabic poetry comparisons, feature updates, pending requests, comparisons, and errors verified.', flush=True)

    page.locator('#reset').click()
    complete()
    for width in [1440, 390, 320]:
        page.set_viewport_size({'width':width, 'height':900})
        assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth')
        page.locator('#language').scroll_into_view_if_needed()
        page.screenshot(path=str(artifacts / f'arabic-header-{width}.png'))
        page.locator('#experiment-form').scroll_into_view_if_needed()
        page.screenshot(path=str(artifacts / f'arabic-controls-{width}.png'))
        page.locator('#pca-tab').click()
        assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth')
    assert not errors, errors
    browser.close()
    print('Arabic interface checks passed.', flush=True)
