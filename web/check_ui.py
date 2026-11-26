"""Browser checks: uv run --with playwright python web/check_ui.py [scenario ...].

Start the fake API first. Uses installed Chrome, or set MECHANIC_BROWSER to a Chromium executable.
"""
import argparse
import json
import os
import re
import wave
from pathlib import Path
from tempfile import TemporaryDirectory

from playwright.sync_api import expect, sync_playwright

BASE = 'http://127.0.0.1:8174'
SIZES = {'width': 390, 'height': 844}


def choose_language(page, lang):
    page.locator('#language').click()
    page.locator(f'[data-lang="{lang}"]').click()
    expect(page.locator('#language-dialog')).not_to_be_visible()
    expect(page.locator('#language')).to_have_text(lang.upper())


def no_overflow(page):
    stray = page.evaluate('''(() => { const w = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT); const out = [];
        while (w.nextNode()) if (/^\\s*(null|undefined|false|NaN|\\[object Object\\])\\s*$/.test(w.currentNode.data)) out.push(w.currentNode.parentElement.className || w.currentNode.parentElement.tagName);
        return out; })()''')
    assert not stray, f'служебный текст на экране: {stray}'
    clipped = page.evaluate('''(() => [...document.querySelectorAll('button, a, input, select, textarea, summary')].filter(n => {
        const r = n.getBoundingClientRect(); if (!r.width || !r.height || getComputedStyle(n).visibility === 'hidden') return false;
        if (r.left < -0.5 || r.right > innerWidth + 0.5) return true;
        for (let p = n.parentElement; p && p !== document.body; p = p.parentElement) {
          const cs = getComputedStyle(p); if (cs.overflowX === 'visible' && cs.overflowY === 'visible') continue;
          if (cs.overflowY !== 'visible' && p.scrollHeight > p.clientHeight) continue;  // прокручиваемая область: кнопка уедет в прокрутку, это нормально
          const q = p.getBoundingClientRect(); if (r.left < q.left - 0.5 || r.right > q.right + 0.5) return true;
        }
        return false; }).map(n => (n.id || n.className || n.tagName) + ':' + (n.textContent || '').trim().slice(0, 20)))()''')
    assert not clipped, f'кнопки обрезаны контейнером: {clipped}'
    assert page.evaluate('document.documentElement.scrollWidth === innerWidth')
    assert page.locator('main').evaluate('e => e.scrollWidth <= e.clientWidth')
    # шапка и каждый элемент страницы – в пределах ширины экрана, заголовок не наезжает на кнопки
    assert page.locator('#top').evaluate('''e => e.getBoundingClientRect().right <= innerWidth
        && [...e.querySelectorAll('.brand, #header-tools, .back-button')].every(n => n.getBoundingClientRect().right <= innerWidth)
        && (!e.querySelector('.brand') || e.querySelector('.brand').getBoundingClientRect().right < e.querySelector('#header-tools').getBoundingClientRect().left)''')
    wide = page.evaluate('''[...document.querySelectorAll('main *, .dock *')].filter(n => { const r = n.getBoundingClientRect();
        return r.width && (r.right > innerWidth + 0.5 || r.left < -0.5); }).map(n => n.tagName + '.' + n.className).slice(0, 5)''')
    assert not wide, f'элементы шире экрана: {wide}'


def last_item_clears_dock(page):
    assert page.locator('main').evaluate('''main => {
        const scroll = main.scrollTop;
        main.scrollTop = main.scrollHeight;
        const end = main.lastElementChild.getBoundingClientRect().bottom;
        const dock = document.querySelector('.dock').getBoundingClientRect().top;
        main.scrollTop = scroll;
        return end <= dock + 1;
    }'''), 'Bottom bar hides the last item'


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
    expect(page.locator('#top h1')).to_have_text('Цифровой механик')
    expect(page.locator('label[for="vehicle-search"]')).to_have_text('Госномер или гаражный номер')
    expect(page.locator('.count')).to_have_text('Показано 8 из 50')
    expect(page.locator('.vehicle-row').first).to_contain_text('Дефектовка до рейса')
    page.get_by_role('button', name='Показать еще 42').click()
    expect(page.locator('.vehicle-row')).to_have_count(50)
    assert page.locator('body').evaluate("el => parseFloat(getComputedStyle(el).fontSize)") >= 18
    assert page.locator('#vehicle-search').bounding_box()['height'] >= 56
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
    assert page.locator('.verdict-head h2').evaluate('el => parseFloat(getComputedStyle(el).fontSize)') >= 26
    expect(page.locator('.verdict-head h2')).to_have_text('Требует внимания')
    expect(page.locator('.verdict-cause')).to_have_text('Возможная причина: клапанный механизм')
    expect(page.locator('.next-action h3')).to_have_text('Что делать')
    expect(page.locator('.verdict-why li')).to_have_count(2)
    expect(page.locator('.verdict-why')).not_to_contain_text('Уверенность модели 0.85')
    expect(page.locator('.context time')).to_have_text('17 ноября 2026, 16:20')
    expect(page.locator('.metric').first).not_to_be_visible()
    page.get_by_text('Цифры проверки', exact=True).click()
    expect(page.locator('.metric')).to_have_count(3)
    expect(page.locator('body')).not_to_contain_text('\u2014')


def locales(page):
    picker = page.locator('#language')
    picker.click()
    expect(page.locator('[data-lang]')).to_have_count(7)
    page.get_by_role('button', name='Закрыть', exact=True).click()
    expect(page.locator('#language-dialog')).to_be_hidden()
    expect(picker).to_be_focused()
    page.set_viewport_size({'width': 360, 'height': 740})
    page.locator('#font-size').click()
    for lang in ['en', 'uz', 'tg', 'ky', 'kk', 'hi', 'ru', 'hi']:
        choose_language(page, lang)
        expect(page.locator('html')).to_have_attribute('lang', lang)
        assert '\u2014' not in page.locator('body').inner_text()
        no_overflow(page)
    page.reload()
    expect(picker).to_have_text('HI')
    expect(page.locator('h1')).to_have_text('डिजिटल मैकेनिक')
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
    expect(page.locator('.next-action p')).to_contain_text('Дефектовка на ближайшем ТО')
    no_overflow(page)
    expect(page.locator('html')).to_have_attribute('lang', 'hi')


def accept_voice_consent(page):
    dialog = page.locator('#data-dialog')
    if dialog.is_visible():
        dialog.get_by_role('checkbox').check()
        dialog.locator('button.primary').click()


def voice(page):
    open_chat(page)
    mic = page.locator('#mic')
    question = page.locator('#question')
    mic.click()
    accept_voice_consent(page)
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
    assert page.locator('.measure').first.inner_text() == '0,25-0,30\xa0мм'


def vehicle_voice(page):
    open_vehicle(page)
    question = page.get_by_role('textbox', name='Вопрос текстом или голосом')
    expect(question).to_be_visible(timeout=1500)
    # Keep the browser upload and fixture validation, substitute only the recognized phrase.
    page.evaluate('''() => {
        const fetch = window.fetch.bind(window);
        window.fetch = async (path, options) => {
            const response = await fetch(path, options);
            if (path !== '/api/transcribe' || !response.ok) return response;
            return Response.json({...await response.json(), text: 'ЧТО С МАШИНОЙ?'});
        };
    }''')
    mic = page.locator('#mic')
    mic.click()
    accept_voice_consent(page)
    expect(mic).to_have_attribute('aria-pressed', 'true')
    expect(page.locator('#mic-timer')).to_have_text('0:01', timeout=4000)
    with page.expect_response(lambda r: r.url.endswith('/api/transcribe')) as upload:
        mic.click()
    assert upload.value.ok, upload.value.text()
    expect(question).to_have_value('ЧТО С МАШИНОЙ?')
    expect(page.locator('main.vehicle')).to_be_visible()
    with page.expect_request(lambda r: r.url.endswith('/api/chat')) as chat:
        page.locator('#send-question').click()
    assert {k: chat.value.post_data_json[k] for k in ('vehicle_id', 'session_id', 'message', 'action')} == {
        'vehicle_id': 'B418HK98', 'session_id': 'S-0009', 'message': 'ЧТО С МАШИНОЙ?', 'action': 'diagnose',
    }
    expect(page.locator('.verdict-head')).to_be_visible()
    expect(page.locator('#chat-progress-row')).to_be_hidden()
    page.go_back()
    expect(question).to_be_editable()
    question.fill('Какой тепловой зазор?')
    with page.expect_request(lambda r: r.url.endswith('/api/chat')) as followup:
        page.locator('#send-question').click()
    assert followup.value.post_data_json['action'] is None
    expect(page.locator('.inline-cite').first).to_be_visible()


def detail_mode(page):
    # переключателя в панели вопроса нет: ответ коротко, «Объяснить подробнее» – кнопкой под ответом,
    # постоянный выбор – в последнем шаге инструкции
    with page.expect_request(lambda r: r.url.endswith('/api/chat')) as request:
        open_chat(page)
    assert request.value.post_data_json.get('detail') == 'brief'
    expect(page.locator('.compose .detail-switch')).to_have_count(0)
    more = page.locator('.more-detail')
    expect(more).to_have_text('Объяснить подробнее')
    with page.expect_request(lambda r: r.url.endswith('/api/chat')) as request:
        more.click()
    assert request.value.post_data_json['detail'] == 'detailed'
    assert request.value.post_data_json['message'] == 'Объясните подробнее, по шагам'
    expect(page.locator('.user-message').last).to_contain_text('Объясните подробнее, по шагам')
    expect(page.locator('#chat-progress-row')).to_be_hidden()
    expect(page.locator('.agent-message').last).to_be_visible()
    expect(more).to_have_count(0)   # подробный ответ уже получен
    page.locator('#question').fill('Какой тепловой зазор?')
    with page.expect_request(lambda r: r.url.endswith('/api/chat')) as request:
        page.locator('#send-question').click()
    assert request.value.post_data_json['detail'] == 'brief'   # разовая просьба не меняет выбор
    expect(page.locator('#chat-progress-row')).to_be_hidden()
    # постоянный выбор в инструкции
    page.goto(page.url.split('#')[0])
    page.locator('#help').click()
    for _ in range(5):
        page.locator('#guide-next').click()
    expect(page.locator('#detail-label')).to_have_text('Как объяснять ответы')
    expect(page.locator('#detail-hint')).to_contain_text('давно работает с двигателями')
    page.get_by_role('button', name='Подробно, по шагам', exact=True).click()
    expect(page.get_by_role('button', name='Подробно, по шагам', exact=True)).to_have_attribute('aria-pressed', 'true')
    expect(page.locator('#detail-hint')).to_contain_text('только начинает')
    page.locator('#guide-next').click()
    assert page.evaluate("localStorage.getItem('mechanic:detail')") == 'detailed'
    page.reload()
    with page.expect_request(lambda r: r.url.endswith('/api/chat')) as request:
        open_chat(page)
    assert request.value.post_data_json['detail'] == 'detailed'
    expect(page.locator('.more-detail')).to_have_count(0)
    with page.expect_request(lambda r: r.url.endswith('/api/chat')) as request:
        page.locator('[data-command="draft"]').click()
    assert request.value.post_data_json['detail'] == 'detailed'
    expect(page.locator('#draft-form')).to_be_visible()


def inspection_required(page):
    open_chat(page, 'K961TH198')
    notice = page.get_by_text('Сначала осмотрите узел на машине', exact=True)
    expect(notice).to_be_visible(timeout=1500)
    command = page.locator('[data-command="draft"]')
    assert notice.bounding_box()['y'] < command.bounding_box()['y']
    command.click()
    confirm = page.locator('#confirm-ticket')
    check = page.get_by_role('checkbox', name='Признак подтвержден осмотром')
    label = page.locator('label[for="inspection-confirmed"]')
    expect(check).not_to_be_checked()
    assert label.bounding_box()['height'] >= 56
    expect(confirm).to_be_disabled()
    expect(page.get_by_text('Отметьте выше, что осмотр подтвердил признак. После этого заявку можно отправить.')).to_be_visible()
    posts = []
    page.on('request', lambda r: posts.append(r) if r.url.endswith('/api/tickets/confirm') else None)
    page.locator('#draft-form').dispatch_event('submit')
    check.check()
    expect(confirm).to_be_enabled()
    check.uncheck()
    expect(confirm).to_be_disabled()
    assert not posts
    check.check()
    with page.expect_response(lambda r: r.url.endswith('/api/tickets/confirm')) as response:
        confirm.click()
    assert response.value.ok
    expect(page.locator('.receipt-id')).to_be_visible()
    ticket = page.locator('.receipt-id').inner_text()
    card = page.request.get(f'{BASE}/api/vehicles/K961TH198').json()
    assert card['open_ticket'] == ticket


def data_consent(page):
    page.get_by_role('link', name='Как мы обрабатываем данные').click(timeout=1500)
    dialog = page.locator('#data-dialog')
    expect(dialog.get_by_role('listitem')).to_have_count(6)
    dialog.get_by_role('button', name='Закрыть').click()
    open_vehicle(page)
    page.evaluate("""() => {
        const get = navigator.mediaDevices.getUserMedia.bind(navigator.mediaDevices);
        window.micRequests = 0;
        navigator.mediaDevices.getUserMedia = options => { window.micRequests++; return get(options); };
    }""")
    mic = page.locator('#mic')
    mic.click()
    expect(dialog).to_be_visible()
    expect(dialog.get_by_role('button', name='Продолжить')).to_be_disabled()
    assert page.evaluate('window.micRequests') == 0
    dialog.get_by_role('button', name='Отмена').click()
    expect(mic).to_be_focused()
    assert page.evaluate('window.micRequests') == 0
    mic.click()
    consent = dialog.get_by_role('checkbox', name='Согласен на обработку персональных данных')
    expect(consent).not_to_be_checked()
    consent.check()
    dialog.get_by_role('button', name='Продолжить').click()
    expect(dialog).to_be_hidden()
    expect(mic).to_have_attribute('aria-pressed', 'true')
    assert page.evaluate('window.micRequests') == 1
    page.reload()
    open_vehicle(page)
    mic.click()
    expect(mic).to_have_attribute('aria-pressed', 'true')
    expect(dialog).to_be_hidden()


def fleet_tickets(page):
    vehicles = page.request.get(f'{BASE}/api/vehicles').json()
    open_tickets = {v['vehicle_id']: v['open_ticket'] for v in vehicles if v['open_ticket']}
    page.get_by_role('button', name='Сводка парка для главного механика').click()
    counter = page.get_by_role('button', name=re.compile('Заявок в работе'))
    expect(counter.locator('strong')).to_have_text(str(len(open_tickets)), timeout=1500)
    rows = page.locator('.fleet-row')
    counter.click()
    expect(counter).to_have_attribute('aria-pressed', 'true')
    expect(rows).to_have_count(len(open_tickets))
    assert set(rows.evaluate_all('rows => rows.map(row => row.dataset.plate)')) == set(open_tickets)
    assert 'T792HO98' in open_tickets
    page.locator('[data-plate="T792HO98"]').click()
    expect(page.locator('.vehicle-head')).to_contain_text(f"Заявка в ремонт {open_tickets['T792HO98']}")
    page.go_back()
    expect(counter).to_have_attribute('aria-pressed', 'true')
    counter.click()
    expect(rows).to_have_count(sum(v['fleet_status'] != 'ok' for v in vehicles))  # без фильтра – очередь без машин в норме


def voice_errors(page):
    open_chat(page)
    page.evaluate("Object.defineProperty(navigator.mediaDevices, 'getUserMedia', {value: () => Promise.reject(new DOMException('', 'NotAllowedError'))})")
    page.locator('#mic').click()
    accept_voice_consent(page)
    expect(page.locator('#voice-status')).to_contain_text('Доступ к микрофону закрыт')
    expect(page.locator('#question')).to_be_editable()
    page.evaluate('Object.defineProperty(window, "MediaRecorder", {value: undefined})')
    page.locator('#mic').click()
    expect(page.locator('#voice-status')).to_contain_text('Этот браузер не умеет записывать звук')


def auto_stop(page):
    choose_language(page, 'uz')
    open_chat(page)
    page.clock.install()
    mic = page.locator('#mic')
    mic.click()
    accept_voice_consent(page)
    expect(mic).to_have_attribute('aria-pressed', 'true')
    expect(page.locator('#mic-timer')).to_have_text('0:01', timeout=3000)
    with page.expect_response(lambda r: r.url.endswith('/api/transcribe')) as upload:
        page.clock.fast_forward(60_000)
    assert upload.value.ok and upload.value.json()['lang'] == 'uz'
    expect(page.locator('#question')).to_have_value('Klapanlarning issiqlik tirqishini qanday tekshiraman?')
    expect(mic).to_have_attribute('aria-pressed', 'false')
    expect(mic).to_be_hidden()
    expect(page.locator('#send-question')).to_be_visible()
    expect(page.locator('#mic-timer')).to_be_hidden()


def onboarding(page):
    # первый запуск: инструкция открыта сама, шаги листаются, закрытие запоминается, «?» открывает ее снова
    guide = page.locator('#guide')
    expect(guide).to_be_visible()
    expect(page.locator('#guide-heading')).to_have_text('Цифровой механик – помощник у машины')
    expect(page.locator('.guide-count')).to_have_text('Шаг 1 из 6')
    expect(page.locator('#guide-prev')).to_have_count(0)
    expect(page.locator('#guide-next')).to_be_focused()
    for step in range(2, 7):
        page.locator('#guide-next').click()
        expect(page.locator('.guide-count')).to_have_text(f'Шаг {step} из 6')
        assert guide.evaluate('d => d.scrollWidth <= d.clientWidth && d.getBoundingClientRect().right <= innerWidth')
    expect(page.locator('#guide-skip')).to_have_count(0)
    expect(page.locator('#guide-next')).to_have_text('Начать работу')
    page.locator('#guide-prev').click()
    expect(page.locator('.guide-count')).to_have_text('Шаг 5 из 6')
    expect(page.locator('.guide-legend, .guide-flow').first).to_contain_text('Помощник заполнит черновик')
    page.locator('#guide-next').click()
    page.locator('#guide-next').click()
    expect(guide).to_be_hidden()
    assert page.evaluate("localStorage.getItem('mechanic:onboarded')") == '1'
    page.reload()
    expect(page.locator('#vehicle-search')).to_be_visible()
    expect(guide).to_be_hidden()
    no_overflow(page)
    # повторный вход кнопкой «?», Escape закрывает
    page.get_by_role('button', name='Как пользоваться').click()  # ссылка над списком машин
    expect(page.locator('.guide-count')).to_have_text('Шаг 1 из 6')
    page.keyboard.press('Escape')
    expect(guide).to_be_hidden()
    # узкий экран и крупный шрифт: кнопки внизу окна видны на каждом шаге, текст листается внутри
    page.set_viewport_size({'width': 360, 'height': 640})
    page.locator('#font-size').click()
    page.locator('#help').click()
    for step in range(1, 7):
        box = page.locator('#guide-next').bounding_box()
        assert box and box['y'] + box['height'] <= 640 and box['x'] + box['width'] <= 360, (step, box)
        assert guide.evaluate('d => d.scrollWidth <= d.clientWidth')
        assert page.locator('.guide-body').evaluate('b => b.scrollWidth <= b.clientWidth')
        if step < 6:
            page.locator('#guide-next').click()
    page.locator('#guide-next').click()
    expect(guide).to_be_hidden()
    # ссылка на инструкцию – только на главном экране
    page.locator('#vehicle-search').fill('B418HK98')
    page.locator('.vehicle-row').first.click()
    expect(page.locator('#diagnose')).to_be_visible()
    expect(page.locator('#help')).to_be_hidden()
    no_overflow(page)


def screenshot(page, name):
    page.evaluate('document.fonts.ready')
    stray = page.evaluate('''(() => { const w = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT); const out = [];
        while (w.nextNode()) if (/^\\s*(null|undefined|false|NaN|\\[object Object\\])\\s*$/.test(w.currentNode.data)) out.push(w.currentNode.parentElement.className || w.currentNode.parentElement.tagName);
        return out; })()''')
    assert not stray, f'служебный текст на экране: {stray}'
    clipped = page.evaluate('''(() => [...document.querySelectorAll('button, a, input, select, textarea, summary')].filter(n => {
        const r = n.getBoundingClientRect(); if (!r.width || !r.height || getComputedStyle(n).visibility === 'hidden') return false;
        if (r.left < -0.5 || r.right > innerWidth + 0.5) return true;
        for (let p = n.parentElement; p && p !== document.body; p = p.parentElement) {
          const cs = getComputedStyle(p); if (cs.overflowX === 'visible' && cs.overflowY === 'visible') continue;
          if (cs.overflowY !== 'visible' && p.scrollHeight > p.clientHeight) continue;  // прокручиваемая область: кнопка уедет в прокрутку, это нормально
          const q = p.getBoundingClientRect(); if (r.left < q.left - 0.5 || r.right > q.right + 0.5) return true;
        }
        return false; }).map(n => (n.id || n.className || n.tagName) + ':' + (n.textContent || '').trim().slice(0, 20)))()''')
    assert not clipped, f'кнопки обрезаны контейнером: {clipped}'
    assert page.evaluate('document.documentElement.scrollWidth === innerWidth'), name
    assert page.locator('main').evaluate('e => e.scrollWidth <= e.clientWidth'), name
    measurements = page.locator('button:visible, select:visible, textarea:visible, input:not([type=radio],[type=checkbox]):visible, .check-label:visible, summary:visible, .check-row:visible, a:visible:not(.inline-cite)').evaluate_all('''nodes => nodes.map(node => {
        const r = node.getBoundingClientRect();
        const target = node.matches('.top button, .excerpt-toggle, a') ? 44 : 56;
        return [node.id || node.tagName, r.width, r.height, target];
    })''')
    # элемент мог скрыться между поиском и замером (указатель на объяснение прячется при прокрутке) – нулевой размер не считаем
    measurements = [m for m in measurements if m[1] and m[2]]
    assert all(w >= min_h and h >= min_h for _, w, h, min_h in measurements), (name, measurements)
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
    default_screens = Path(__file__).resolve().parents[1] / 'docs' / 'screens'
    page.screenshot(path=Path(os.getenv('MECHANIC_SCREENS') or default_screens) / f'{name}.png', animations='disabled')


def screens(page):
    expect(page.locator('.vehicle-row').first).to_be_visible()
    screenshot(page, '01-park')
    page.locator('#help').click()
    screenshot(page, '00-guide-start')
    page.locator('#guide-next').click()
    screenshot(page, '00-guide-labels')
    page.keyboard.press('Escape')
    expect(page.locator('#guide')).to_be_hidden()
    page.get_by_role('link', name='Как мы обрабатываем данные').click()
    screenshot(page, '19-data-policy')
    page.locator('#data-dialog').get_by_role('button', name='Закрыть').click()
    open_vehicle(page)
    screenshot(page, '02-vehicle')
    page.locator('#mic').click()
    screenshot(page, '20-voice-consent')
    page.locator('#data-dialog').get_by_role('button', name='Отмена').click()
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
    expect(page.locator('.more-detail')).to_be_visible()
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
    expect(page.locator('.tile')).to_have_count(3)
    screenshot(page, '10-fleet')
    page.locator('[data-filter="open_ticket"]').click()
    page.locator('[data-plate="T792HO98"]').click()
    screenshot(page, '21-vehicle-ticket')
    page.goto(BASE)
    open_chat(page, 'M333YK47')
    screenshot(page, '04-normal')
    page.goto(BASE)
    open_chat(page, 'P456AT178')
    page.set_viewport_size({'width': 360, 'height': 740})
    screenshot(page, '05-check-failed')
    page.set_viewport_size(SIZES)
    page.goto(BASE)
    choose_language(page, 'uz')
    screenshot(page, '13-uz-park')
    choose_language(page, 'hi')
    screenshot(page, '14-hi-park')
    page.goto(BASE)
    choose_language(page, 'ru')
    open_vehicle(page, 'P854BT78')
    page.get_by_text('Прошлые проверки', exact=True).click()
    page.locator('[data-session="S-0021"]').click()
    expect(page.locator('#chat-progress-row')).to_be_hidden()
    expect(page.locator('.verdict-head')).to_contain_text('Программа ошиблась')
    expect(page.locator('.defect-note')).to_contain_text('Заявку по этой проверке не создаем')
    expect(page.locator('[data-command="draft"]')).to_have_count(0)
    page.context.grant_permissions(['clipboard-read', 'clipboard-write'])
    page.locator('[data-command="copy-defect-note"]').click()
    expect(page.locator('[data-command="copy-defect-note"]')).to_have_text('Текст скопирован')
    page.locator('.defect-note').scroll_into_view_if_needed()
    screenshot(page, '11-not-applicable')
    page.locator('#mic').click()
    accept_voice_consent(page)
    expect(page.locator('#mic-timer')).to_have_text('0:01', timeout=4000)
    screenshot(page, '15-ru-recording')
    page.locator('#mic').click()
    expect(page.locator('#question')).to_have_value('Как проверить тепловой зазор клапанов?')
    screenshot(page, '16-ru-transcript')
    page.goto(BASE)
    open_chat(page, 'T792HO98')
    expect(page.locator('.verdict-head h2')).to_have_text('Дефектовка до выпуска в рейс')
    screenshot(page, '17-quarantine')
    page.locator('#language').click()
    screenshot(page, '18-language')
    page.goto(BASE)
    open_chat(page, 'K961TH198')
    page.locator('.inspection-notice').scroll_into_view_if_needed()
    screenshot(page, '22-inspection-verdict')
    page.locator('[data-command="draft"]').click()
    expect(page.locator('#confirm-ticket')).to_be_disabled()
    screenshot(page, '23-inspection-draft')


def real_voice(page):
    open_vehicle(page, 'P854BT78')
    page.get_by_text('Прошлые проверки', exact=True).click()
    with page.expect_request(lambda r: r.url.endswith('/api/chat')) as chat:
        page.locator('[data-session="S-0021"]').click()
    assert chat.value.post_data_json['lang'] == 'ru'
    expect(page.locator('.verdict-head')).to_contain_text('Программа ошиблась', timeout=30000)
    expect(page.locator('#chat-progress-row')).to_be_hidden(timeout=45000)
    warning = page.locator('.warnings')
    expect(warning).to_contain_text('не подходит к двигателю')
    warning.scroll_into_view_if_needed()
    expect(warning).to_be_in_viewport(ratio=.95)
    page.locator('main').evaluate('e => {e.scrollTop = 0}')
    screenshot(page, '11-not-applicable')
    mic = page.locator('#mic')
    mic.click()
    accept_voice_consent(page)
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


def interactions(page):
    search = page.locator('#vehicle-search')
    search.fill('г-103')
    expect(page.locator('.count')).to_have_text('Показано 1 из 1')
    page.get_by_role('button', name='Очистить поиск').click()
    expect(search).to_have_value('')
    expect(search).to_be_focused()
    page.locator('.wide-link').click()
    # B3/С4: сводка норма / требует внимания / карантин, очередь без машин в норме, карантин первым
    rows = page.locator('.fleet-row')
    group = {'quarantine': 'quarantine', 'anomaly': 'attention', 'check_failed': 'attention', 'normal': 'normal'}
    entries = rows.evaluate_all('els => els.map(e => e.dataset.stage)')
    tiles = {k: int(page.locator(f'[data-filter="{k}"] .tile-number').inner_text()) for k in ('quarantine', 'attention', 'normal')}
    assert sum(tiles.values()) == 50, tiles
    assert len(entries) == tiles['quarantine'] + tiles['attention'] and 'normal' not in entries, entries
    assert entries[:tiles['quarantine']] == ['quarantine'] * tiles['quarantine'], entries
    assert rows.evaluate_all('rows => rows.every((row, i) => row.querySelector(".rank").textContent === String(i + 1))')
    for key in ('quarantine', 'attention', 'normal'):
        button = page.locator(f'[data-filter="{key}"]')
        button.click()
        expect(button).to_have_attribute('aria-pressed', 'true')
        expect(rows).to_have_count(tiles[key])
        assert all(group[x] == key for x in rows.evaluate_all('els => els.map(e => e.dataset.stage)'))
        button.click()
    failed = page.locator('[data-filter="check_failed"]')
    failed.click()
    assert set(rows.evaluate_all('els => els.map(e => e.dataset.stage)')) == {'check_failed'}
    failed.click()
    page.get_by_role('button', name=re.compile('Показать машины в норме')).click()
    expect(rows).to_have_count(50)
    page.locator('.back-button').click()
    expect(search).to_be_visible()
    open_vehicle(page)
    expect(page.locator('.selection #diagnose')).to_be_visible()
    expect(page.locator('.selection time')).to_have_text('17 ноября 2026, 16:20')
    expect(page.locator('.selection .pill')).to_have_count(1)
    page.get_by_text('Заявки по машине', exact=True).click()
    expect(page.locator('.ticket-entry').first).to_be_visible()
    page.get_by_text('Прошлые проверки', exact=True).click()
    expect(page.locator('.check-row')).to_have_count(2)
    with page.expect_request(lambda r: r.url.endswith('/api/chat')) as request:
        page.locator('[data-session="S-0008"]').click()
    assert request.value.post_data_json['session_id'] == 'S-0008'
    expect(page.locator('#chat-progress-row')).to_be_hidden()
    page.go_back()
    expect(page.locator('#diagnose')).to_be_visible()
    page.go_forward()
    expect(page.locator('.verdict-head')).to_be_visible()
    page.go_back()
    page.locator('#diagnose').click()
    expect(page.locator('#chat-progress-row')).to_be_hidden()
    expect(page.get_by_role('button', name='Вопрос голосом')).to_be_visible()
    expect(page.locator('#send-question')).to_be_hidden()
    page.get_by_text('Объяснение помощника', exact=True).click()
    expect(page.locator('.agent-message').first).to_be_visible()
    page.get_by_text('Как помощник искал ответ', exact=True).click()
    expect(page.locator('.trace li')).to_have_count(1)
    q = page.locator('#question')
    q.fill('1\n2\n3\n4\n5\n6')
    assert 100 < q.bounding_box()['height'] < 132
    q.fill('Какой тепловой зазор?')
    expect(page.locator('#mic')).to_be_hidden()
    page.locator('#send-question').click()
    expect(page.locator('#chat-progress-row')).to_be_hidden()
    expect(page.locator('.trace')).to_have_count(1)
    expect(page.locator('.citation-row').first).to_have_text('[1] ЯМЗ-236М2. Руководство по эксплуатации, стр. 31')
    first_quote = page.locator('.citation-excerpt').first
    preview = first_quote.inner_text()
    assert preview.endswith('…') and 'сопрягае- мых' not in preview, preview
    more = page.locator('.excerpt-toggle').first
    more.click()
    expect(more).to_have_attribute('aria-expanded', 'true')
    full_quote = first_quote.inner_text()
    assert full_quote.startswith(preview.removesuffix('…') + ' ') and 'сопрягаемых' in full_quote, full_quote
    more.click()
    expect(more).to_have_attribute('aria-expanded', 'false')
    page.locator('.citation-row').first.click()
    expect(page.locator('#manual-image')).to_be_visible()
    expect(page.locator('.manual-controls strong')).to_contain_text('31 из ')
    page.get_by_text('Текст страницы', exact=True).click()
    expect(page.locator('.page-text')).to_be_visible()
    page.locator('#manual-image').dblclick()
    expect(page.locator('.zoom-group output')).to_have_text('200%')
    page.locator('#zoom-out').click()
    expect(page.locator('.zoom-group output')).to_have_text('150%')
    page.locator('.page-frame').scroll_into_view_if_needed()
    frame = page.locator('.page-frame').bounding_box()
    for _ in range(2):
        page.touchscreen.tap(frame['x'] + 40, max(75, frame['y'] + 20))
    expect(page.locator('.zoom-group output')).to_have_text('100%')
    page.locator('#manual-next').click()
    expect(page.locator('.manual-controls strong')).to_contain_text('32 из ')
    page.locator('#manual-prev').click()
    expect(page.locator('.manual-controls strong')).to_contain_text('31 из ')
    page.go_back()
    expect(page.locator('#manual')).to_be_hidden()
    page.go_forward()
    expect(page.locator('#manual-image')).to_be_visible()
    page.keyboard.press('Escape')
    expect(page.locator('#manual')).to_be_hidden()
    page.locator('[data-command="draft"]').click()
    expect(page.locator('#draft-form')).to_be_visible()
    page.locator('[name="conclusion"]').fill(' ')
    page.locator('#confirm-ticket').click()
    expect(page.locator('#ticket-error')).to_have_text('Введите заключение.')
    page.locator('[name="conclusion"]').fill('Проверить машину.')
    page.locator('[name="operations"]').fill('Проверить клапаны')
    page.locator('[name="spare_parts"]').fill('Прокладка')
    page.locator('select[name="urgency"]').select_option('low')
    expect(page.locator('[name="urgency_reason"]')).to_have_attribute('required', '')
    page.locator('[name="urgency_reason"]').fill('Очный осмотр')
    page.get_by_text('Почему такой приоритет', exact=True).click()
    page.locator('.page-chip').first.click()
    expect(page.locator('#manual-image')).to_be_visible()
    page.locator('#close-manual').click()
    page.go_back()
    page.locator('[data-command="draft"]').click()
    expect(page.locator('[name="spare_parts"]')).to_have_value('Прокладка')
    page.locator('#confirm-ticket').click()
    expect(page.locator('.receipt-id')).to_be_visible()
    expect(page.locator('.receipt-fields')).to_contain_text('17 ноября 2026, 16:20')
    page.go_back()
    page.get_by_text('Открыть квитанцию', exact=True).click()
    expect(page.locator('.receipt-id')).to_be_visible()


def network_errors(page):
    page.route('**/api/vehicles', lambda route: route.abort())
    page.reload()
    expect(page.get_by_role('alert')).to_contain_text('Нет связи')
    page.unroute('**/api/vehicles')
    page.get_by_role('button', name='Повторить').click()
    open_vehicle(page)
    page.route('**/api/chat', lambda route: route.abort())
    page.locator('#diagnose').click()
    expect(page.get_by_role('alert')).to_contain_text('Нет связи')
    page.unroute('**/api/chat')
    page.get_by_role('button', name='Повторить').click()
    expect(page.locator('.verdict-head')).to_be_visible()
    expect(page.locator('#chat-progress-row')).to_be_hidden()
    page.route('**/api/chat', lambda route: route.abort())
    page.locator('#question').fill('Какой тепловой зазор?')
    page.locator('#send-question').click()
    expect(page.locator('#question')).to_have_value('Какой тепловой зазор?')
    page.unroute('**/api/chat')
    page.locator('#send-question').click()
    expect(page.locator('#chat-progress-row')).to_be_hidden()
    page.route('**/api/manuals/*/pages/*', lambda route: route.abort())
    page.locator('.inline-cite').first.click()
    expect(page.locator('#manual [role=alert]')).to_contain_text('Нет связи')
    page.unroute('**/api/manuals/*/pages/*')
    page.locator('#manual').get_by_role('button', name='Повторить').click()
    expect(page.locator('#manual-image')).to_be_visible()


def large_routes(page):
    page.set_viewport_size({'width': 360, 'height': 740})
    page.locator('#font-size').click()
    for lang in ('tg', 'ky'):
        page.goto(BASE)
        choose_language(page, lang)
        no_overflow(page)
        page.locator('.wide-link').click()
        no_overflow(page)
        page.go_back()
        open_vehicle(page)
        no_overflow(page)
        page.locator('#diagnose').click()
        expect(page.locator('#chat-progress-row')).to_be_hidden()
        no_overflow(page)
        page.locator('#question').fill('Какой тепловой зазор?')
        page.locator('#send-question').click()
        expect(page.locator('#chat-progress-row')).to_be_hidden()
        no_overflow(page)
        last_item_clears_dock(page)
        page.locator('.inline-cite').first.click()
        expect(page.locator('#manual-image')).to_be_visible()
        assert page.locator('#manual').evaluate('e => e.scrollWidth <= e.clientWidth')
        page.locator('#close-manual').click()
        page.locator('[data-command="draft"]').click()
        expect(page.locator('#draft-form')).to_be_visible()
        no_overflow(page)
        last_item_clears_dock(page)
        page.locator('#confirm-ticket').click()
        expect(page.locator('.receipt-id')).to_be_visible()
        no_overflow(page)


def real_kickoff(page):
    """Two paid requests maximum; no live ticket or speech writes."""
    sent = []
    expected = [
        {'message': 'что с машиной?', 'action': 'diagnose', 'detail': 'brief'},
        {'message': 'Какой тепловой зазор клапанов для этого двигателя?', 'action': None, 'detail': 'detailed'},
    ]

    def cap_chat(route):
        payload = route.request.post_data_json
        index = len(sent)
        if (route.request.method != 'POST' or index >= len(expected)
                or {key: payload.get(key) for key in expected[index]} != expected[index]
                or payload['vehicle_id'] != 'B418HK98' or payload['session_id'] != 'S-0009'):
            route.abort()
            return
        sent.append(payload)
        route.continue_()

    page.route('**/api/chat', cap_chat)
    for path in ('/api/transcribe', '/api/tickets/confirm'):
        page.route(f'**{path}', lambda route: route.abort())
    open_vehicle(page)
    for index, payload in enumerate(expected):
        if index == 1:   # подробный режим выбирается в инструкции и хранится в браузере
            page.evaluate("localStorage.setItem('mechanic:detail', 'detailed')")
            page.reload()
            expect(page.locator('#question')).to_be_visible()
        page.locator('#question').fill(payload['message'])
        with page.expect_response(lambda r: r.url.endswith('/api/chat'), timeout=30_000) as response:
            page.locator('#send-question').click()
        res = response.value
        assert res.ok and 'text/event-stream' in res.headers['content-type'], res.status
        expect(page.locator('#chat-progress-row')).to_be_hidden(timeout=90_000)
        events = [json.loads(line[6:]) for line in res.text().splitlines() if line.startswith('data: ')]
        assert events[-1]['type'] == 'done' and not any(e['type'] == 'error' for e in events), [e for e in events if e['type'] == 'error']
        assert any(e['type'] == 'message' and e.get('text', '').strip() for e in events)
        expect(page.locator('.user-message').last).to_contain_text(payload['message'])
        expect(page.get_by_role('alert')).to_have_count(0)
        if not index:
            assert sum(e['type'] == 'diagnosis' for e in events) == 1
            expect(page.locator('.verdict-head')).to_be_visible()
        else:
            expect(page.locator('.agent-message').last).to_have_text(re.compile(r'\S'))
        print(f"live {payload['action'] or 'question'} / {payload['detail']}: HTTP {res.status}, SSE done")
    assert len(sent) == len(expected)
    assert sent[0]['conversation_id'] == sent[1]['conversation_id']


def main():
    fake = (onboarding, layout, locales, voice, voice_errors, auto_stop, interactions, network_errors, large_routes,
            vehicle_voice, detail_mode, inspection_required, data_consent, fleet_tickets)
    scenarios = {test.__name__: test for test in (*fake, screens, real_voice, real_kickoff)}
    parser = argparse.ArgumentParser()
    parser.add_argument('scenarios', nargs='*')
    parser.add_argument('--real-wav', type=Path, help='Russian speech WAV for the real_voice scenario (one paid diagnostic request)')
    args = parser.parse_args()
    selected = args.scenarios or [test.__name__ for test in fake]
    if 'real_kickoff' in selected and selected != ['real_kickoff']:
        parser.error('Run real_kickoff separately (two paid chat requests).')
    if 'real_voice' in selected and (selected != ['real_voice'] or not args.real_wav or not args.real_wav.is_file()):
        parser.error('Run real_voice separately with --real-wav pointing to a WAV file.')
    with TemporaryDirectory(prefix='mechanic-', dir=os.getenv('MECHANIC_SCRATCH') or os.getenv('TMPDIR')) as temp, sync_playwright() as pw:
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
            if name != 'onboarding':   # инструкция первого запуска проверяется отдельным сценарием
                context.add_init_script("try { localStorage.setItem('mechanic:onboarded', '1'); } catch {}")
            page = context.new_page()
            page.set_default_timeout(7000)
            errors = []
            page.on('pageerror', lambda error: errors.append(str(error)))
            page.goto('http://127.0.0.1:8000' if name in {'real_voice', 'real_kickoff'} else BASE)
            scenarios[name](page)
            assert not errors, errors
            print(f'{name}: pass')
            context.close()
        browser.close()


if __name__ == '__main__':
    main()
