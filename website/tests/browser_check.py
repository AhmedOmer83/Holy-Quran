"""End-to-end check: pip install playwright; requires Google Chrome."""
from pathlib import Path
import csv
import io
import json
from playwright.sync_api import sync_playwright

artifacts=Path(__file__).resolve().parents[1]/'test-artifacts'
artifacts.mkdir(exist_ok=True)
with sync_playwright() as p:
    browser=p.chromium.launch(executable_path='/usr/bin/google-chrome',headless=True,args=['--no-sandbox'])
    page=browser.new_page(viewport={'width':1440,'height':1000},device_scale_factor=1)
    page.set_default_timeout(60000)
    errors=[]
    page.on('pageerror',lambda error: errors.append(str(error)))
    def complete():
        try:
            page.wait_for_function("!busy && result !== null && document.querySelector('#status').textContent.startsWith('Experiment complete')")
        except Exception:
            print(page.evaluate('({busy,revision,pendingRun,status:$("status").textContent,error:$("error").textContent,config:config()})'),flush=True)
            raise
    page.goto('http://127.0.0.1:8000')
    complete()
    assert page.locator('#context, #questions, [data-preset], #dataset').count()==0
    assert page.locator('a[href*=thesis]').count()==0
    assert all(term not in page.locator('body').inner_text().lower() for term in ['taha','margoliouth','husayn','historical debate'])
    assert page.locator('#feature').input_value()=='words'
    assert page.locator('#top').input_value()=='100'
    assert page.evaluate('result.config.eras')==['Quran','PreIslamic','Modern']
    assert page.evaluate('result.config.top')==100
    assert page.locator('#words').input_value()=='7000'
    assert page.locator('#samples').input_value()=='10'
    assert page.locator('#samples').get_attribute('max')=='10'
    assert page.locator('#tree-chart svg').count()==1
    assert page.locator('#feature-rows tr').count()>0
    assert page.locator('.feature-example-toggle, .feature-examples-row').count()==0
    assert page.locator('#examples-heading').is_hidden()
    assert page.locator('.analysis-method').count()==2
    assert page.locator('#pca-tab').is_visible()
    assert 'Principal component analysis (PCA)' in page.locator('#pca-tab').inner_text()
    assert page.locator('#pca-tab').bounding_box()['width']==page.locator('#tree-tab').bounding_box()['width']
    assert page.locator('#metrics strong').first.inner_text()=='30'
    assert 'Vertical' in page.locator('#tree-chart svg').get_attribute('aria-label')
    assert page.evaluate("new Set([...document.querySelectorAll('.tree-leaf circle')].map(e=>e.getAttribute('cy'))).size") == 1
    
    page.screenshot(path=str(artifacts/'quran-poetry-desktop.png'),full_page=True)
    page.locator('#tree-chart').screenshot(path=str(artifacts/'vertical-tree.png'))
    page.locator('#tree-tab').focus()
    page.keyboard.press('ArrowRight')
    assert page.locator('#pca-tab').get_attribute('aria-selected')=='true'
    assert page.locator('#pca-tab').get_attribute('tabindex')=='0'
    assert page.locator('#chart-title').inner_text()=='Principal component analysis (PCA)'
    assert page.locator('.pca-feature').count()==20
    assert page.locator('.pca-sample').count()==30
    page.locator('#pca-chart').screenshot(path=str(artifacts/'pca-features.png'))

    print('Default plots verified',flush=True)
    # Unchecking the focus group refreshes both charts and exports without Run.
    page.locator('[name=era][value=Quran]').uncheck()
    complete()
    assert page.locator('.tree-leaf[data-era=Quran]').count()==0
    assert page.locator('.pca-sample[data-era=Quran]').count()==0
    assert page.evaluate("result.config.target === 'PreIslamic' && result.branch.purity !== null && result.silhouette !== null")
    assert page.locator('#feature-rows .arabic').count()>0
    assert 'Pre-Islamic' in page.locator('#feature-title').inner_text()
    assert 'Select Quran' not in page.locator('#finding').inner_text()
    assert page.evaluate("result.samples.every(s=>s.era!=='Quran')")
    page.locator('[name=era][value=Quran]').check()
    complete()
    assert page.locator('.pca-sample[data-era=Quran]').count()==10
    assert page.evaluate('result.config.target')=='Quran'

    # Hold an old response, change selection again, and ensure it cannot be rendered.
    delayed=[]
    def hold(route):
        delayed.append((route,route.fetch()))
        page.evaluate('window.heldResponseReady = true')
    page.route('**/api/experiment',hold,times=1)
    page.locator('[name=era][value=Quran]').uncheck()
    page.wait_for_function('busy')
    page.locator('[name=era][value=Abbasid]').check()
    assert page.locator('.pca-sample').count()==0
    page.wait_for_function('window.heldResponseReady === true')
    delayed[0][0].fulfill(response=delayed[0][1])
    complete()
    assert page.evaluate("result.samples.every(s=>s.era!=='Quran') && result.samples.some(s=>s.era==='Abbasid')")

    # Invalid selection clears the old plots; selecting a second category recovers.
    page.evaluate("document.querySelectorAll('[name=era]').forEach(e=>e.checked=e.value==='PreIslamic'); document.querySelector('[name=era]').dispatchEvent(new Event('change',{bubbles:true}))")
    page.locator('#error').wait_for(state='visible')
    assert 'at least two' in page.locator('#error').inner_text()
    assert page.locator('.tree-leaf').count()==0
    page.locator('[name=era][value=Quran]').check()
    complete()

    print('Selection and stale-response checks passed',flush=True)
    expected_sets=[
        ('words','Most frequent words','words',1),
        ('word2','Word bigram','wordgrams',2),
        ('char1','Character 1 gram','chargrams',1),
        ('char2','Character bigram','chargrams',2),
        ('char3','Character trigram','chargrams',3),
        ('char5','Character 5 grams','chargrams',5),
        ('char7','Character 7 grams','chargrams',7),
    ]
    assert page.locator('#feature option').all_text_contents()==[item[1] for item in expected_sets]
    assert page.locator('#ngram').count()==0
    for option,label,feature,n in expected_sets:
        page.locator('#feature').select_option(option)
        complete()
        assert page.evaluate('result.config.feature')==feature
        assert page.evaluate('result.config.ngram')==n
        assert label.upper() in page.locator('#result-caption').inner_text()
        assert all('·' not in text for text in page.locator('#feature-rows .arabic').all_text_contents())
        feature_names=page.evaluate('result.feature_names')
        if feature=='chargrams': assert all(len(name)==n for name in feature_names)
        else: assert all(len(name.split())==n for name in feature_names)
        raw_labels=page.evaluate('result.features.map(f=>f.name)')
        displayed_labels=page.locator('#feature-rows .arabic').all_text_contents()
        assert displayed_labels==[name.replace(' ', '␣') for name in raw_labels]
        assert page.locator('#feature-space-note').is_visible()==any(' ' in name for name in raw_labels)
        assert page.locator('.pca-feature text').all_text_contents()==[
            name.replace(' ', '␣') for name in page.evaluate('result.pca_features.map(f=>f.name)')]
        if option=='char3':
            # Features that looked identical must retain distinct visible boundaries.
            pairs=[(i,j) for i,a in enumerate(raw_labels) for j,b in enumerate(raw_labels)
                   if i<j and a.strip()==b.strip() and a!=b]
            assert pairs, 'Exercise real features differing only by space position'
            assert all(displayed_labels[i]!=displayed_labels[j] for i,j in pairs)
            for button in ['download','csv-export','svg-export']:
                with page.expect_download() as info: page.locator('#'+button).click()
                text=Path(info.value.path()).read_text(encoding='utf-8-sig')
                if button=='download': assert json.loads(text)['feature_names']==feature_names
                elif button=='csv-export': assert next(csv.reader(io.StringIO(text)))[2:]==feature_names
                else: assert '␣' in text
        assert page.locator('.pca-feature').count()>0
    print('All seven feature sets verified',flush=True)

    # A delayed feature result cannot overwrite a newer feature selection.
    delayed.clear()
    page.evaluate('window.heldResponseReady = false')
    page.route('**/api/experiment',hold,times=1)
    page.locator('#feature').select_option('word2')
    page.wait_for_function('busy')
    page.locator('#feature').select_option('char3')
    page.wait_for_function('window.heldResponseReady === true')
    delayed[0][0].fulfill(response=delayed[0][1])
    complete()
    assert page.evaluate("result.config.feature === 'chargrams' && result.config.ngram === 3")
    assert 'CHARACTER TRIGRAM' in page.locator('#result-caption').inner_text()

    page.locator('#reset').click()
    complete()
    assert page.evaluate('result.config.target')=='Quran'
    page.locator('#compare').click()
    page.wait_for_function("document.querySelector('#status').textContent.startsWith('Feature comparison complete')")
    assert page.locator('#comparison tbody tr').count()==len(expected_sets)
    assert page.locator('#comparison tbody tr td:first-child').all_text_contents()==[item[1] for item in expected_sets]
    assert page.locator('#comparison td[colspan]').count()==0
    for button,filename in [('download','experiment.json'),('csv-export','features.csv'),('svg-export','pca.svg')]:
        with page.expect_download() as info:page.locator('#'+button).click()
        info.value.save_as(str(artifacts/filename))
    page.locator('#view').select_option('centroids')
    complete()
    assert 'Centroid view' in page.locator('#finding').inner_text()
    page.locator('#distance').select_option('euclidean')
    complete()
    page.locator('#linkage').select_option('ward')
    complete()
    page.locator('#select-all').click()
    complete()
    assert page.evaluate('result.config.eras.length')==11
    assert page.evaluate('result.sample_count')==110
    page.set_viewport_size({'width':390,'height':844})
    page.goto('http://127.0.0.1:8000')
    complete()
    assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth')
    page.locator('#pca-tab').click()
    assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth')
    page.screenshot(path=str(artifacts/'mobile.png'),full_page=True)
    assert not errors,errors
    print('Browser checks passed: defaults, checkbox updates, stale responses, seven feature sets, vertical tree, PCA feature labels, comparisons, exports, centroids, Ward, all groups and mobile.')
    browser.close()
