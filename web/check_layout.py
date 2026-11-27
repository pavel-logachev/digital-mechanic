"""Верстка на реальных размерах телефонов: от 5" (320–360 px) до больших «лопат» (430–480 px) и планшета.

Для каждого размера, обычного и крупного шрифта проходит все основные экраны механика и главного механика и проверяет:
- нет горизонтальной прокрутки и элементов шире экрана;
- слова не рвутся посередине строки (перенос допустим только для номеров и кодов, которые не помещаются целиком);
- кнопки и надписи не обрезаны контейнером;
- нижняя панель не закрывает последний элемент страницы;
- на экране нет служебного текста (null, undefined, NaN).
Снимки – в MECHANIC_LAYOUT (по умолчанию scratch/layout). Работает с тестовым API: python web/dev_fake_api.py
"""
import os
import sys
from pathlib import Path

from playwright.sync_api import expect, sync_playwright

sys.path.insert(0, str(Path(__file__).parent))
from check_ui import BASE, open_chat, open_vehicle

DEVICES = {   # ширина × высота CSS-пикселей
    'se-320': (320, 568),        # старый iPhone SE, предельно узкий
    'android-360': (360, 640),   # 5–5,5" Android
    'iphone8-375': (375, 667),
    'android-360-tall': (360, 780),
    'iphone-390': (390, 844),
    'pixel-412': (412, 915),
    'promax-430': (430, 932),
    'big-480': (480, 1040),      # крупные Android с низкой плотностью
    'tablet-768': (768, 1024),
}

PROBE = r"""() => {
  const vw = document.documentElement.clientWidth, out = {wide: [], broken: [], clipped: [], stray: []};
  const visible = n => { const r = n.getBoundingClientRect(); const cs = getComputedStyle(n);
    return r.width > 0 && r.height > 0 && cs.visibility !== 'hidden' && cs.display !== 'none'; };
  const root = document.querySelector('dialog[open]') || document.body;
  if (document.documentElement.scrollWidth > vw + 1) out.wide.push('документ ' + document.documentElement.scrollWidth);
  for (const n of root.querySelectorAll('*')) {
    if (!visible(n) || n.closest('.visually-hidden, .manual-image, .zoom-area')) continue;
    const r = n.getBoundingClientRect();
    if (r.right > vw + 0.5 || r.left < -0.5) out.wide.push(`${n.tagName.toLowerCase()}.${[...n.classList].join('.')}`);
    const cs = getComputedStyle(n);
    if (n.matches('button, .source-link, .replica, .pill, .ticket-note') && n.scrollHeight > n.clientHeight + 2 && cs.overflowY === 'visible')
      out.clipped.push(`текст вылезает из ${n.tagName.toLowerCase()}.${[...n.classList].join('.')}: ${n.textContent.trim().slice(0, 30)}`);
    if ((cs.overflowX === 'hidden' || cs.textOverflow === 'ellipsis') && n.scrollWidth > n.clientWidth + 1 && n.textContent.trim()
        && !n.matches('textarea, input, .visually-hidden'))
      out.clipped.push(`${n.tagName.toLowerCase()}.${[...n.classList].join('.')}: ${n.textContent.trim().slice(0, 30)}`);
  }
  const w = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
  while (w.nextNode()) {
    const t = w.currentNode, el = t.parentElement;
    if (!el || !visible(el) || el.closest('.visually-hidden, textarea, .page-text, .manual-body pre')) continue;
    if (/^\s*(null|undefined|false|NaN|\[object Object\])\s*$/.test(t.data)) out.stray.push(el.className || el.tagName);
    for (const m of t.data.matchAll(/[\p{L}\p{N}][\p{L}\p{N}\-‑.,:/«»"()]*[\p{L}\p{N}]/gu)) {
      if (m[0].length < 4) continue;
      const range = document.createRange(); range.setStart(t, m.index); range.setEnd(t, m.index + m[0].length);
      const tops = new Set([...range.getClientRects()].filter(r => r.width > 0).map(r => Math.round(r.top)));
      if (tops.size > 1) out.broken.push(`${m[0]} (${el.tagName.toLowerCase()}.${[...el.classList].join('.')})`);
    }
  }
  const main = document.querySelector('main'), dock = document.querySelector('.dock');
  if (main && dock && visible(dock) && !document.querySelector('dialog[open]')) {
    const keep = main.scrollTop; main.scrollTop = main.scrollHeight;
    const last = [...main.children].filter(visible).at(-1);
    if (last && last.getBoundingClientRect().bottom > dock.getBoundingClientRect().top + 1) out.clipped.push('нижняя панель закрывает конец страницы');
    main.scrollTop = keep;
  }
  return out;
}"""

problems = []


def check(page, device, large, name):
    page.wait_for_timeout(250)
    page.evaluate('document.fonts.ready')
    r = page.evaluate(PROBE)
    bad = {k: sorted(set(v))[:8] for k, v in r.items() if v}
    tag = f"{device}{' крупный' if large else ''} {name}"
    if bad:
        problems.append((tag, bad))
        print('FAIL', tag, bad)
    out = Path(os.getenv('MECHANIC_LAYOUT') or Path(os.getenv('TMPDIR', '.')) / 'layout')
    out.mkdir(parents=True, exist_ok=True)
    page.screenshot(path=out / f"{device}{'-L' if large else ''}-{name}.png", full_page=False, animations='disabled')


def walk(page, device, large):
    c = lambda name: check(page, device, large, name)  # noqa: E731
    expect(page.locator('#guide')).to_be_visible()
    for step in range(1, 7):
        page.locator('.guide-body').evaluate('b => b.scrollTop = b.scrollHeight')
        c(f'guide{step}')
        page.locator('#guide-next').click()
    expect(page.locator('.vehicle-row').first).to_be_visible()
    c('park')
    page.locator('#vehicle-search').fill('Г-1')
    c('search')
    page.locator('#vehicle-search').fill('')
    open_vehicle(page, 'T792HO98')
    c('vehicle')
    page.locator('main').evaluate('m => m.scrollTop = m.scrollHeight')
    c('vehicle-end')
    page.locator('#mic').click()
    c('voice-consent')
    page.locator('#data-dialog').get_by_role('button', name='Отмена').click()
    page.locator('#diagnose').click()
    expect(page.locator('.verdict-head')).to_be_visible()
    expect(page.locator('#chat-progress-row')).to_be_hidden()
    c('verdict')
    page.locator('main').evaluate('m => m.scrollTop = m.scrollHeight')
    c('answer-end')
    if page.locator('.inline-cite').count():
        page.locator('.inline-cite').first.click()
        expect(page.locator('#manual')).to_be_visible()
        c('manual')
        page.locator('#manual').get_by_role('button', name='Закрыть руководство').first.click()
    page.locator('[data-command="draft"], button:has-text("Создать заявку")').first.click()
    expect(page.locator('#confirm-ticket, button:has-text("Отправить заявку")').first).to_be_visible(timeout=15000)
    c('draft')
    page.locator('main').evaluate('m => m.scrollTop = m.scrollHeight')
    c('draft-end')
    page.goto(BASE)
    expect(page.locator('.vehicle-row').first).to_be_visible()
    open_chat(page, 'P456AT178')
    c('check-failed')
    page.goto(BASE)
    expect(page.locator('.vehicle-row').first).to_be_visible()
    open_chat(page, 'K961TH198')
    c('inspection')
    page.goto(BASE)
    page.locator('.wide-link').first.click()
    expect(page.locator('.tiles')).to_be_visible()
    c('fleet')
    if True:
        page.locator('main').evaluate('m => m.scrollTop = m.scrollHeight')
        c('fleet-end')


def main():
    only = set(sys.argv[1:])
    with sync_playwright() as pw:
        browser = pw.chromium.launch(channel='chrome')
        for device, (w, h) in DEVICES.items():
            if only and device not in only:
                continue
            for large in (False, True):
                ctx = browser.new_context(viewport={'width': w, 'height': h}, is_mobile=w < 700, has_touch=True, device_scale_factor=2)
                if large:
                    ctx.add_init_script("try { localStorage.setItem('mechanic:large', 'true'); } catch {}")
                page = ctx.new_page()
                page.set_default_timeout(10000)
                errors = []
                page.on('pageerror', lambda e, errors=errors: errors.append(str(e)))
                page.goto(BASE)
                try:
                    walk(page, device, large)
                except Exception as e:   # noqa: BLE001 – фиксируем и идем к следующему размеру
                    problems.append((f'{device} {large}', {'сценарий': [f'{type(e).__name__}: {str(e)[:200]}']}))
                    print('ERROR', device, large, type(e).__name__, str(e)[:300])
                if errors:
                    problems.append((f'{device} {large}', {'js': errors[:3]}))
                ctx.close()
        browser.close()
    print(f'итого проблем: {len(problems)}')
    sys.exit(1 if problems else 0)


if __name__ == '__main__':
    main()
