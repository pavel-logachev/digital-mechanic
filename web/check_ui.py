"""Browser checks: uv run --with playwright python web/check_ui.py [scenario ...].

Start the fake API first. Uses installed Chrome, or set MECHANIC_BROWSER to a Chromium executable.
"""
import argparse
import os
import re
import wave
from pathlib import Path
from tempfile import TemporaryDirectory

from playwright.sync_api import expect, sync_playwright

BASE = 'http://127.0.0.1:8174'
SIZES = {'width': 390, 'height': 844}


def open_vehicle(page, plate='B418HK98'):
    page.locator('#vehicle-search').fill(plate)
    page.locator('.vehicle-row').first.click()
    expect(page.locator('#diagnose')).to_be_visible()


def open_chat(page, plate='B418HK98'):
    open_vehicle(page, plate)
    page.locator('#diagnose').click()
    expect(page.locator('.verdict-head')).to_be_visible()
    expect(page.locator('#chat-progress-row')).to_be_hidden()


def layout(page):
    expect(page.locator('h1')).to_have_text('Выберите машину')
    assert page.locator('body').evaluate("el => parseFloat(getComputedStyle(el).fontSize)") >= 18
    assert page.locator('#vehicle-search').bounding_box()['height'] >= 56
    page.locator('#search-keyboard').click()
    expect(page.locator('#vehicle-search')).to_have_attribute('inputmode', 'numeric')
    page.locator('#search-keyboard').click()
    expect(page.locator('#vehicle-search')).to_have_attribute('inputmode', 'search')
    page.locator('#vehicle-search').fill('в418нк')
    expect(page.locator('.vehicle-row')).to_have_count(1)
    expect(page.locator('.vehicle-row')).to_contain_text('B418HK98')
    page.locator('#vehicle-search').fill('103')
    expect(page.locator('.vehicle-row')).to_contain_text('B418HK98')
    page.locator('#vehicle-search').fill('000000000000')
    expect(page.locator('.vehicle-row')).to_have_count(0)
    page.locator('#font-size').click()
    page.reload()
    expect(page.locator('#font-size')).to_have_attribute('aria-pressed', 'true')
    assert page.locator('body').evaluate("el => parseFloat(getComputedStyle(el).fontSize)") > 18
    page.locator('#font-size').click()
    open_chat(page)
    assert 22 <= page.locator('.verdict-head h2').evaluate("el => parseFloat(getComputedStyle(el).fontSize)") <= 26
    assert 22 <= page.locator('.next-action h3').evaluate("el => parseFloat(getComputedStyle(el).fontSize)") <= 26
    expect(page.locator('body')).not_to_contain_text('\u2014')


def locales(page):
    picker = page.locator('#language')
    expect(picker.locator('option')).to_have_count(7)
    page.set_viewport_size({'width': 360, 'height': 740})
    page.locator('#font-size').click()
    for lang in ['en', 'uz', 'tg', 'ky', 'kk', 'hi', 'ru', 'hi']:
        picker.select_option(lang)
        expect(page.locator('html')).to_have_attribute('lang', lang)
        assert '\u2014' not in page.locator('body').inner_text()
        assert page.locator('#top').evaluate('e => e.scrollWidth <= e.clientWidth')
        assert page.locator('main').evaluate('e => e.scrollWidth <= e.clientWidth')
    page.reload()
    expect(picker).to_have_value('hi')
    expect(page.locator('h1')).to_have_text('गाड़ी चुनें')
    session = page.context.new_cdp_session(page)
    session.send('DOM.enable')
    session.send('CSS.enable')
    doc = session.send('DOM.getDocument')['root']['nodeId']
    h1 = session.send('DOM.querySelector', {'nodeId': doc, 'selector': 'h1'})['nodeId']
    fonts = session.send('CSS.getPlatformFontsForNode', {'nodeId': h1})['fonts']
    assert fonts and not any(f['isCustomFont'] for f in fonts), fonts
    print('Hindi platform fonts:', ', '.join(f['familyName'] for f in fonts))
    session.detach()
    with page.expect_request(lambda r: r.url.endswith('/api/chat')) as request:
        open_chat(page)
    assert request.value.post_data_json['lang'] == 'hi'
    expect(page.locator('.next-action p')).to_contain_text('Проверьте машину очно')
    expect(page.locator('html')).to_have_attribute('lang', 'hi')


def voice(page):
    open_chat(page)
    mic = page.locator('#mic')
    question = page.locator('#question')
    mic.click()
    expect(mic).to_have_attribute('aria-pressed', 'true')
    expect(page.locator('#mic-timer')).to_be_visible()
    expect(page.locator('#mic-timer')).to_have_text('0:01', timeout=3000)
    with page.expect_response(lambda r: r.url.endswith('/api/transcribe')) as upload:
        mic.click()
    assert upload.value.ok, upload.value.text()
    assert 'multipart/form-data; boundary=' in upload.value.request.headers['content-type']
    assert upload.value.json()['lang'] == 'ru'
    expect(question).to_have_value('Как проверить тепловой зазор клапанов?')
    question.fill('Какой тепловой зазор?')
    with page.expect_request(lambda r: r.url.endswith('/api/chat')) as chat:
        page.locator('#send-question').click()
    assert chat.value.post_data_json['message'] == 'Какой тепловой зазор?'
    expect(page.locator('.agent-message').last).to_contain_text('0,25-0,30 мм')


def voice_errors(page):
    open_chat(page)
    page.evaluate("Object.defineProperty(navigator.mediaDevices, 'getUserMedia', {value: () => Promise.reject(new DOMException('', 'NotAllowedError'))})")
    page.locator('#mic').click()
    expect(page.locator('#voice-status')).to_contain_text('Доступ к микрофону закрыт')
    expect(page.locator('#question')).to_be_editable()
    page.evaluate('Object.defineProperty(window, "MediaRecorder", {value: undefined})')
    page.locator('#mic').click()
    expect(page.locator('#voice-status')).to_contain_text('Этот браузер не умеет записывать звук')


def auto_stop(page):
    page.locator('#language').select_option('uz')
    open_chat(page)
    page.clock.install()
    mic = page.locator('#mic')
    mic.click()
    expect(mic).to_have_attribute('aria-pressed', 'true')
    expect(page.locator('#mic-timer')).to_have_text('0:01', timeout=3000)
    with page.expect_response(lambda r: r.url.endswith('/api/transcribe')) as upload:
        page.clock.fast_forward(60_000)
    assert upload.value.ok and upload.value.json()['lang'] == 'uz'
    expect(page.locator('#question')).to_have_value('Klapanlarning issiqlik tirqishini qanday tekshiraman?')
    expect(mic).to_have_attribute('aria-pressed', 'false')
    expect(page.locator('#mic-timer')).to_be_hidden()


def screenshot(page, name):
    page.evaluate('document.fonts.ready')
    assert page.evaluate('document.documentElement.scrollWidth === innerWidth'), name
    assert page.locator('main').evaluate('e => e.scrollWidth <= e.clientWidth'), name
    measurements = page.locator('button:visible, select:visible, textarea:visible, input:not([type=radio]):visible, summary:visible, .check-row:visible, a:visible').evaluate_all('''nodes => nodes.map(node => {
        const r = node.getBoundingClientRect();
        return [node.id || node.tagName, r.width, r.height, node.tagName === 'A' ? 48 : 56];
    })''')
    assert all(w >= 48 and h >= min_h for _, w, h, min_h in measurements), (name, measurements)
    contrasts = page.evaluate('''() => {
        const values = [];
        const lum = color => color.slice(0, 3).map(x => {
            const c = x / 255;
            return c <= .04045 ? c / 12.92 : ((c + .055) / 1.055) ** 2.4;
        }).reduce((s, v, i) => s + v * [.2126, .7152, .0722][i], 0);
        const rgb = css => css.match(/[\\d.]+/g).map(Number);
        const root = document.querySelector('dialog[open]') || document.querySelector('#shell');
        for (const el of root.querySelectorAll('*')) {
            if (!el.getClientRects().length || el instanceof SVGElement || el.matches('option, select, .visually-hidden')) continue;
            const directText = [...el.childNodes].filter(n => n.nodeType === 3).map(n => n.textContent).join('').trim();
            if (!directText && !el.matches('input:not([type=radio]), textarea')) continue;
            let parent = el, bg;
            while (parent) {
                bg = rgb(getComputedStyle(parent).backgroundColor);
                if (bg.length === 3 || bg[3] === 1) break;
                parent = parent.parentElement;
            }
            if (!parent) continue;
            const fg = rgb(getComputedStyle(el, el.matches(':placeholder-shown') ? '::placeholder' : null).color);
            const [a, b] = [lum(fg), lum(bg)].sort((x, y) => y-x);
            values.push([(a + .05) / (b + .05), directText || el.placeholder]);
        }
        return values.sort((a, b) => a[0]-b[0]);
    }''')
    assert not contrasts or contrasts[0][0] >= 4.5, (name, contrasts[:5])
    page.screenshot(path=Path(__file__).resolve().parents[1] / 'docs' / 'screens' / f'{name}.png', animations='disabled')


def screens(page):
    expect(page.locator('.vehicle-row').first).to_be_visible()
    screenshot(page, '01-park')
    open_vehicle(page)
    screenshot(page, '02-vehicle')
    page.locator('#diagnose').click()
    expect(page.locator('#chat-progress-row')).to_be_visible()
    expect(page.locator('#send-question')).to_be_hidden()
    screenshot(page, '12-agent-working')
    expect(page.locator('#chat-progress-row')).to_be_hidden()
    screenshot(page, '03-anomaly')
    page.locator('#question').fill('Какой тепловой зазор?')
    page.locator('#send-question').click()
    expect(page.locator('.inline-cite').first).to_be_visible()
    expect(page.locator('#chat-progress-row')).to_be_hidden()
    screenshot(page, '06-chat-citation')
    page.locator('.inline-cite').first.click()
    expect(page.locator('#manual-image')).to_be_visible()
    expect(page.locator('#manual blockquote')).to_contain_text('0,20-0,40 мм')
    expect(page.locator('#manual .page-text')).to_be_hidden()
    screenshot(page, '07-manual-page')
    page.locator('#zoom-in').click()
    assert page.locator('#manual-image').bounding_box()['width'] > page.locator('.page-frame').bounding_box()['width']
    page.locator('#manual-next').click()
    expect(page.locator('.manual-controls strong')).to_contain_text('32')
    page.locator('#close-manual').click()
    page.locator('[data-command="draft"]').click()
    expect(page.locator('#confirm-ticket')).to_be_enabled()
    screenshot(page, '08-draft')
    page.locator('select[name="urgency"]').select_option('low')
    page.locator('[name="urgency_reason"]').fill('Проверка на учебном стенде')
    page.locator('#confirm-ticket').click()
    expect(page.locator('.receipt-id')).to_contain_text('TKT-')
    ticket_id = page.locator('.receipt-id').inner_text()
    card = page.request.get(f'{BASE}/api/vehicles/B418HK98').json()
    assert any(ticket['ticket_id'] == ticket_id and ticket['urgency'] == 'low' for ticket in card['tickets'])
    screenshot(page, '09-receipt')
    page.get_by_role('button', name='К списку машин').click()
    page.locator('.wide-link').click()
    expect(page.locator('.fleet-count')).to_have_count(3)
    screenshot(page, '10-fleet')
    page.goto(BASE)
    open_chat(page, 'M333YK47')
    screenshot(page, '04-normal')
    page.goto(BASE)
    open_chat(page, 'P456AT178')
    page.set_viewport_size({'width': 360, 'height': 740})
    screenshot(page, '05-check-failed')
    page.set_viewport_size(SIZES)
    page.goto(BASE)
    page.locator('#language').select_option('uz')
    screenshot(page, '13-uz-park')
    page.locator('#language').select_option('hi')
    screenshot(page, '14-hi-park')


def real_voice(page):
    open_vehicle(page, 'P854BT78')
    page.get_by_text('История проверок', exact=True).click()
    page.locator('input[value="S-0021"]').check()
    with page.expect_request(lambda r: r.url.endswith('/api/chat')) as chat:
        page.locator('#diagnose').click()
    assert chat.value.post_data_json['lang'] == 'ru'
    expect(page.locator('.verdict-head h2')).to_contain_text('Тип отклонения не подтвержден', timeout=30000)
    expect(page.locator('#chat-progress-row')).to_be_hidden(timeout=45000)
    warning = page.locator('.warnings')
    expect(warning).to_contain_text('не подходит к двигателю')
    warning.scroll_into_view_if_needed()
    expect(warning).to_be_in_viewport(ratio=.95)
    page.locator('main').evaluate('e => {e.scrollTop = 0}')
    screenshot(page, '11-not-applicable')
    mic = page.locator('#mic')
    mic.click()
    expect(page.locator('#mic-timer')).to_have_text('0:01', timeout=4000)
    screenshot(page, '15-ru-recording')
    expect(page.locator('#mic-timer')).to_have_text('0:04', timeout=5000)
    with page.expect_response(lambda r: r.url.endswith('/api/transcribe'), timeout=45000) as upload:
        mic.click()
    assert upload.value.ok, upload.value.text()
    data = upload.value.json()
    assert data['lang'] == 'ru', data
    expect(page.locator('#question')).to_have_value(re.compile('зазор.*клапан', re.IGNORECASE), timeout=8000)
    expect(page.locator('#question')).to_be_editable()
    expect(page.locator('#send-question')).to_be_enabled()
    screenshot(page, '16-ru-transcript')
    print('Real transcript:', data['text'])


def main():
    scenarios = {'layout': layout, 'locales': locales, 'voice': voice, 'voice_errors': voice_errors, 'auto_stop': auto_stop, 'screens': screens, 'real_voice': real_voice}
    parser = argparse.ArgumentParser()
    parser.add_argument('scenarios', nargs='*')
    parser.add_argument('--real-wav', type=Path, help='Russian speech WAV for the real_voice scenario (one paid diagnostic request)')
    args = parser.parse_args()
    selected = args.scenarios or ['layout', 'locales', 'voice', 'voice_errors', 'auto_stop']
    if 'real_voice' in selected and (selected != ['real_voice'] or not args.real_wav or not args.real_wav.is_file()):
        parser.error('Run real_voice separately with --real-wav pointing to a WAV file.')
    with TemporaryDirectory(prefix='mechanic-', dir=os.getenv('MECHANIC_SCRATCH')) as temp, sync_playwright() as pw:
        wav = args.real_wav.resolve() if args.real_wav else Path(temp) / 'mic.wav'
        if not args.real_wav:
            with wave.open(str(wav), 'wb') as audio:
                audio.setparams((1, 2, 16000, 0, 'NONE', 'not compressed'))
                audio.writeframes(b'\0\0' * 16000)
        exe = os.getenv('MECHANIC_BROWSER')
        browser = pw.chromium.launch(executable_path=exe, channel=None if exe else 'chrome', args=[
            '--use-fake-device-for-media-stream', '--use-fake-ui-for-media-stream',
            f'--use-file-for-fake-audio-capture={wav}',
        ])
        for name in selected:
            context = browser.new_context(viewport=SIZES, is_mobile=True, has_touch=True, permissions=['microphone'])
            page = context.new_page()
            page.set_default_timeout(7000)
            errors = []
            page.on('pageerror', lambda error: errors.append(str(error)))
            page.goto('http://127.0.0.1:8000' if name == 'real_voice' else BASE)
            scenarios[name](page)
            assert not errors, errors
            print(f'{name}: pass')
            context.close()
        browser.close()


if __name__ == '__main__':
    main()
