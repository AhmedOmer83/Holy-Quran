"""Run against the local server: python tests/feature_examples_check.py."""
from pathlib import Path
from playwright.sync_api import sync_playwright

artifacts = Path(__file__).resolve().parents[1] / 'test-artifacts'
artifacts.mkdir(exist_ok=True)

with sync_playwright() as p:
    browser = p.chromium.launch(executable_path='/usr/bin/google-chrome', headless=True, args=['--no-sandbox'])
    page = browser.new_page(viewport={'width': 1440, 'height': 1000})
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

    def complete():
        page.wait_for_function('!busy && !!result')

    complete()
    # Hand-checked cases: word boundaries, overlapping grams, spaces, and
    # missing source coverage (never fabricate extra examples).
    page.evaluate('''() => {
      const check = (condition, message) => { if (!condition) throw new Error(message); };
      const evidenceFixture={feature_names:['من','في'],samples:[{era:'Modern',display_spans:[]},{era:'Modern',display_spans:[]},{era:'Quran'}],feature_matrix:[[.02,0],[.04,0],[.9,.1]]};
      check(JSON.stringify(featureGroupEvidence(evidenceFixture,'من','Modern'))===JSON.stringify({samples:2,present:2,rate:300}), 'Analysis evidence is independent of quotation coverage');
      check(featureGroupEvidence(evidenceFixture,'في','Modern').present===0, 'Actual absent features retain zero frequency');
      const sample = {text:'وقال قال قالوا قال بيت', era:'Quran', chunk:0};
      const positions = [...featureOccurrences(sample, 'قال', 'words')];
      check(JSON.stringify(positions.map(m=>m.start)) === '[5,15]', 'Whole words only');
      check([...featureOccurrences(sample, 'قال بيت', 'wordgrams')].length === 1, 'Word bigrams');
      check([...featureOccurrences({text:'للل'}, 'لل', 'chargrams')].length === 2, 'Overlapping grams');
      check([...featureOccurrences(sample, 'ل ب', 'chargrams')].length === 1, 'Spaces in grams');
      const experiment = {config:{eras:['Quran'], feature:'words'}, samples:[sample]};
      check(featureExamples(experiment, 'قال').length === 1, 'Do not duplicate identical excerpts');
      check(featureExamples(experiment, 'غائب').length === 0, 'No invented matches');
      const longSample = {...sample, text:'قال ' + 'بيت '.repeat(40) + 'قال ' + 'دار '.repeat(40) + 'قال'};
      check(featureExamples({...experiment, samples:[longSample]}, 'قال').length === 1, 'One representative example per group');
      const folded = {...sample, text:'الي بيت'};
      check(featureExamples({...experiment, samples:[folded]}, 'إلى').length === 0, 'Use experiment normalization');
      check(featureExamples({...experiment, samples:[folded]}, 'الي').length === 1, 'Match normalized feature');
      const corrected = {...sample, text:'اوليك علي هدي من ربهم', display_text:'أولئك على هدى من ربهم'};
      const example = featureExamples({...experiment, samples:[corrected]}, 'اوليك')[0];
      check(example.match === 'أولئك' && example.analysisMatch === 'اوليك', 'Correct spelling for display only');
      check(example.after === ' على هدى من ربهم', 'Correct surrounding passage');
      const bigram = featureExamples({...experiment, config:{...experiment.config, feature:'wordgrams'}, samples:[corrected]}, 'اوليك علي')[0];
      check(bigram.match === 'أولئك على', 'Correct bigram across word boundary');
      const gram = featureExamples({...experiment, config:{...experiment.config, feature:'chargrams'}, samples:[corrected]}, 'يك ع')[0];
      check(gram.match === 'ئك ع', 'Character n-gram preserves mapped offsets');
      const poetry = {era:'PreIslamic', chunk:0, text:'قديم اوليك علي هدي مجهول',
        display_text:'قديم أولئك على هدى مجهول', display_spans:[{start:5,end:18,csv_rows:[2]}]};
      const poems = {config:{eras:['PreIslamic'],feature:'words'},samples:[poetry]};
      const quote = featureExamples(poems, 'اوليك')[0];
      check(quote.match === 'أولئك' && quote.after === ' على هدى …', 'Corrected poetry and clipped context');
      check(!quote.before.includes('قديم'), 'Never quote uncovered surrounding text');
      check(featureExamples(poems, 'مجهول').length === 0, 'No unmatched poetry quotations');
      check(featureExamples({...poems,samples:[{...poetry,display_spans:[]}]}, 'اوليك').length === 0, 'Missing source has no corrected examples');
      const cross = {...poems,config:{...poems.config,feature:'wordgrams'}};
      check(featureExamples(cross, 'هدي مجهول').length === 0, 'No feature crossing source coverage');
      const eras = ['Quran','PreIslamic','Mukhadramun','Umayyad','Abbasid','Andalusian','Fatimid','Ayyubid','Mamluk','Ottoman','Modern'];
      const allGroups = {config:{eras,feature:'words'}, samples:eras.flatMap(era=>[
        {era,text:'غائب',chunk:0}, {era,text:'قال بيت',chunk:1}])};
      check(JSON.stringify(featureExamples(allGroups,'قال').map(e=>e.sample.era))===JSON.stringify(eras), 'All eleven groups, even with identical excerpts and an unmatched first sample');
      check(featureExamples({...allGroups,config:{...allGroups.config,eras:['Ottoman','Modern']}},'قال').length===2, 'Only selected groups');
    }''')
    button = page.locator('.feature-example-toggle').first
    button.focus()
    page.keyboard.press('Enter')
    assert button.get_attribute('aria-expanded') == 'true'
    assert page.locator('.feature-examples-row:visible .feature-example-card').count() == page.evaluate('result.config.eras.length')
    assert len(set(page.locator('.feature-examples-row:visible .feature-example-source').all_text_contents())) == page.evaluate('result.config.eras.length')
    assert page.evaluate('''() => {
      const feature = result.features[0].name;
      return featureExamples(result, feature).every(e => e.sample.text.slice(e.start,e.end) === feature);
    }''')
    page.locator('#feature-comparison').screenshot(path=str(artifacts / 'feature-examples-desktop.png'))
    page.select_option('#language', 'ar')
    assert page.locator('.feature-examples-row:visible .feature-example-card').count() == page.evaluate('result.config.eras.length')
    assert page.locator('.feature-example-toggle').first.inner_text() == 'إخفاء الأمثلة'
    page.set_viewport_size({'width': 390, 'height': 844})
    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth + 1')
    assert page.locator('#feature-comparison .table-scroll').evaluate('(el)=>el.scrollWidth <= el.clientWidth + 1')
    assert page.locator('.feature-examples-grid').first.evaluate('(el)=>getComputedStyle(el).gridTemplateColumns.split(" ").length') == 1
    page.locator('.feature-examples-row:visible').screenshot(path=str(artifacts / 'feature-examples-arabic-mobile.png'))
    page.locator('.feature-example-toggle').nth(1).click()
    assert page.locator('.feature-examples-row:visible').count() == 1
    assert page.locator('.feature-example-toggle').first.get_attribute('aria-expanded') == 'false'
    page.locator('.feature-example-toggle').nth(1).click()
    assert page.locator('.feature-examples-row:visible').count() == 0
    page.select_option('#language', 'en')
    page.set_viewport_size({'width': 1440, 'height': 1000})
    # A real feature row keeps the old spelling while quoting the corrected Quran.
    page.locator('#top').fill('1000')
    page.locator('#top').press('Tab')
    complete()
    index = page.evaluate("result.features.findIndex(f=>f.name==='اوليك')")
    assert index >= 0
    page.locator('.feature-example-toggle').nth(index).click()
    quran_cards = page.locator('.feature-examples-row:visible .feature-example-card').filter(has_text='Quran')
    assert quran_cards.count() > 0
    assert quran_cards.first.locator('mark').inner_text() == 'أولئك'
    assert 'اوليك' not in quran_cards.first.locator('.feature-example-passage').inner_text()
    page.select_option('#language', 'ar')
    page.locator('.feature-examples-row:visible').screenshot(path=str(artifacts / 'quran-corrected-example.png'))
    assert page.locator('.feature-examples-note').first.inner_text().startswith('يُبحث عن السمة')
    page.select_option('#language', 'en')
    page.locator('#top').fill('100')
    page.locator('#top').press('Tab')
    complete()
    # Exercise all seven feature sets with real selected corpus text.
    for feature_set in ['words', 'word2', 'char1', 'char2', 'char3', 'char5', 'char7']:
        if page.locator('#feature').input_value() != feature_set:
            page.select_option('#feature', feature_set)
            assert page.locator('.feature-examples-row:visible').count() == 0
            complete()
        index = page.evaluate('''() => {
          const i = result.features.findIndex(f=>f.name.includes(' '));
          return i < 0 ? 0 : i;
        }''')
        page.locator('.feature-example-toggle').nth(index).click()
        assert page.locator('.feature-examples-row:visible .feature-example-card').count() == page.evaluate('result.config.eras.length'), feature_set
        assert page.evaluate('''(i) => {
          const feature = result.features[i].name;
          const examples = featureExamples(result, feature);
          const marks = [...document.querySelectorAll('.feature-examples-row:not([hidden]) mark')];
          const fold = text => text.replace(/[أإآٱىئؤة]/g, c=>({'أ':'ا','إ':'ا','آ':'ا','ٱ':'ا','ى':'ي','ئ':'ي','ؤ':'و','ة':'ه'}[c]));
          return examples.every((e,j)=>e.sample.text.slice(e.start,e.end)===feature &&
            marks[j].textContent===(e.sample.display_text ?? e.sample.text).slice(e.start,e.end) &&
            fold(marks[j].textContent)===fold(feature));
        }''', index), feature_set
        print(f'{feature_set}: all selected groups and authentic highlights verified', flush=True)
    # Confirm a real poetry correction is rendered from a covered CSV passage.
    page.select_option('#feature', 'words')
    complete()
    candidate = page.evaluate("""() => {
      for (let i=0;i<result.features.length;i++) {
        const example = featureExamples(result,result.features[i].name).find(e=>e.sample.era!=='Quran' && e.match!==e.analysisMatch);
        if (example) return {index:i,match:example.match,era:example.sample.era};
      }
      return null;
    }""")
    assert candidate, 'A real corrected poetry example is available'
    page.locator('.feature-example-toggle').nth(candidate['index']).click()
    assert candidate['match'] in page.locator('.feature-examples-row:visible mark').all_text_contents()
    page.locator('.feature-examples-row:visible').screenshot(path=str(artifacts / 'poetry-corrected-example.png'))
    # Recomputing selection discards the old expansion and excluded groups.
    page.locator('[name=era][value=Quran]').uncheck()
    assert page.locator('.feature-examples-row:visible').count() == 0
    complete()
    page.locator('.feature-example-toggle').first.click()
    assert all('Quran' not in text for text in page.locator('.feature-examples-row:visible .feature-example-source').all_text_contents())
    # Every selected era gets its own card and source-based poet attribution.
    page.locator('#select-all').click()
    complete()
    page.locator('.feature-example-toggle').first.click()
    assert page.locator('.feature-examples-row:visible .feature-example-card').count() == 11
    assert page.evaluate("""() => {
      const cards=[...document.querySelectorAll('.feature-examples-row:not([hidden]) .feature-example-card')];
      const examples=featureExamples(result,result.features[0].name);
      return JSON.stringify(cards.map(c=>c.dataset.era))===JSON.stringify(result.config.eras) &&
        examples.every(e=>{
          const card=cards.find(c=>c.dataset.era===e.sample.era);
          return e.sample.era==='Quran' ? !card.querySelector('.feature-example-poet') :
            e.displaySpan.poets.every(poet=>card.querySelector('.feature-example-poet').textContent.includes(poet));
        });
    }""")
    # Explicitly show an unavailable source instead of filling the era with another era's example.
    page.evaluate("""() => {
      window.savedExamplesResult=result;
      result={...result,samples:result.samples.map(s=>s.era==='Modern'?{...s,display_spans:[]}:s)};
      showFeatureExamples(0);
    }""")
    missing=page.locator('.feature-examples-row:visible [data-era="Modern"]')
    assert 'The corrected source does not cover any' in missing.inner_text()
    assert missing.locator('mark').count()==0
    page.select_option('#language','ar')
    assert 'المصدر المصحح لا يغطي' in missing.inner_text()
    assert 'الشاعر:' in page.locator('.feature-examples-row:visible').inner_text()
    page.set_viewport_size({'width':390,'height':844})
    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth + 1')
    page.locator('.feature-examples-row:visible').screenshot(path=str(artifacts / 'all-eras-poet-examples-ar.png'))
    page.evaluate('result=window.savedExamplesResult; showFeatureExamples(0)')
    assert not errors, errors
    browser.close()
    print('Example matching, keyboard controls, language switching, mobile layout, and selection updates passed.', flush=True)
