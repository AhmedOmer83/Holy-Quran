"""Check actual WebVTT decoding, seeking, language switching and visible cues."""
from pathlib import Path
import os
from playwright.sync_api import sync_playwright

site_url = os.environ.get('SITE_URL', 'http://127.0.0.1:8000').rstrip('/')
artifacts = Path(__file__).resolve().parents[1] / 'test-artifacts'
artifacts.mkdir(exist_ok=True)
with sync_playwright() as p:
    browser = p.chromium.launch(executable_path='/usr/bin/google-chrome',
                                headless=True, args=['--no-sandbox'])
    page = browser.new_page(viewport={'width': 1440, 'height': 1000})
    page.set_default_timeout(60000)
    errors = []
    page.on('pageerror', lambda error: errors.append(str(error)))
    page.goto(site_url)
    page.wait_for_function("document.querySelector('#explainer-english').readyState === 2")
    page.wait_for_function("document.querySelector('video').readyState >= 2")
    assert page.evaluate("document.querySelector('#explainer-english').track.mode") == 'showing'
    assert page.locator('#explainer-open').get_attribute('href').endswith('/media/explainer.en.mp4')
    cues = page.evaluate("Array.from(document.querySelector('#explainer-english').track.cues, c => ({start:c.startTime,end:c.endTime,text:c.text}))")
    assert len(cues) > 100, 'The complete explanation must be captioned.'
    for index in [0, len(cues) // 2, len(cues) - 1]:
        cue = cues[index]
        at = (cue['start'] + cue['end']) / 2
        page.evaluate('(at) => { document.querySelector("video").currentTime = at; }', at)
        page.wait_for_function("!document.querySelector('video').seeking")
        page.wait_for_function("document.querySelector('#explainer-english').track.activeCues.length > 0")
        assert cue['text'] in page.evaluate("Array.from(document.querySelector('#explainer-english').track.activeCues, c => c.text)")
    page.evaluate('(at) => { document.querySelector("video").currentTime = at; }',
                  (cues[4]['start'] + cues[4]['end']) / 2)
    page.wait_for_function("!document.querySelector('video').seeking")
    page.locator('video').screenshot(path=str(artifacts / 'english-video-captions.png'))
    before = page.evaluate('document.querySelector("video").currentTime')
    page.locator('#language').select_option('ar')
    assert page.evaluate("document.querySelector('#explainer-english').track.mode") == 'showing'
    assert page.locator('#explainer-open').get_attribute('href').endswith('/media/explainer.en.mp4')
    assert page.evaluate("document.querySelector('#explainer-english').track.activeCues.length") > 0
    page.locator('video').screenshot(path=str(artifacts / 'arabic-interface-english-captions.png'))
    page.reload()
    page.wait_for_function("document.querySelector('video').readyState >= 1 && document.querySelector('#explainer-english').readyState === 2")
    assert page.locator('#language').input_value() == 'ar'
    assert page.evaluate("document.querySelector('#explainer-english').track.mode") == 'showing'
    page.locator('#language').select_option('en')
    assert page.evaluate("document.querySelector('#explainer-english').track.mode") == 'showing'
    page.evaluate('(at) => { document.querySelector("video").currentTime = at; }', before)
    page.wait_for_function("!document.querySelector('video').seeking")
    page.locator('#language').select_option('ar')
    page.locator('#language').select_option('en')
    assert abs(page.evaluate('document.querySelector("video").currentTime') - before) < .1
    assert page.request.get(f'{site_url}/media/explainer.en.mp4',
                            headers={'Range': 'bytes=0-1023'}).status == 206
    assert page.request.get(f'{site_url}/static/captions/explainer.en.srt').status == 200
    assert not errors, errors
    print(f'{len(cues)} English captions decoded; seeking, visible cues, downloads and saved languages passed.')
    browser.close()
