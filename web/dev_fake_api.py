"""Local UI fixture, with in-memory tickets. Run: python web/dev_fake_api.py"""
import asyncio
import json
import os
import sys
from datetime import UTC, datetime
from functools import lru_cache
from pathlib import Path
from typing import Literal
from uuid import uuid4

import pymupdf
import uvicorn
from fastapi import FastAPI, File, Form, HTTPException, Response, UploadFile
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel

WEB = Path(__file__).resolve().parent
ROOT = WEB.parent
MANUALS = {
    'yamz-236_re_2010': ('ЯМЗ-236М2. Руководство по эксплуатации', '236-3902150-Б РЭ', ('ЯМЗ-236М2',)),
    'yamz-236_rk_2014': ('ЯМЗ-236М2. Руководство по ремонту', '236.01.01 РК', ('ЯМЗ-236М2',)),
    'yamz-536_re_2016': ('ЯМЗ-536. Руководство по эксплуатации', '536.3902150 РЭ', ('ЯМЗ-536',)),
    'yamz-536_rk_2013': ('ЯМЗ-536. Руководство по ремонту', '536.01.02 РК', ('ЯМЗ-536',)),
    'zmz-5234_rk_2025': ('ЗМЗ-5234.10. Руководство по ремонту', 'Двигатели ЗМЗ-5234.10 со сцеплением. Руководство по ремонту', ('ЗМЗ-5234.10',)),
    'zmz-40904-40905_rk_2025': ('ЗМЗ-40904.10 / 40905.10. Эксплуатация, ТО и ремонт', 'Двигатели ЗМЗ-40904.10 и ЗМЗ-40905.10. Руководство по эксплуатации, техническому обслуживанию и ремонту', ('ЗМЗ-40904.10', 'ЗМЗ-40905.10')),
}
YAMZ = 'yamz-236_re_2010'
Q31 = (
    'регулируется в пределах 0,25-0,30 мм. При проверке на двигателе из-за биения сопрягае- мых деталей '
    'распределительного механизма тепловые зазоры после проворачивания коленчатого вала должны укладываться в пределы 0,20-0,40 мм.'
)
Q33 = 'При правильно отрегулированном зазоре щуп толщиной 0,25 мм должен входить при легком нажиме, а толщиной 0,30 мм - с усилием.'
# Данные парка – из материалов задачи (python -m tools.fetch_materials), в Git их нет
VEHICLES = {v['vehicle_id']: v for v in json.loads((ROOT / 'mocks/data/vehicles.json').read_text(encoding='utf-8'))['vehicles']}
TICKETS = {
    'B418HK98': [{'ticket_id': 'TKT-0001', 'session_id': 'S-0008', 'anomaly_type': 'F01', 'urgency': 'medium', 'created_at': '2026-10-30T10:10:00+03:00'}],
    'T792HO98': [{'ticket_id': 'TKT-0002', 'session_id': 'S-0043', 'anomaly_type': 'F02', 'urgency': 'high', 'created_at': '2026-11-15T15:20:00+03:00'}],
}
DRAFTS = {}
CONFIRMED = {}
app = FastAPI(title='Цифровой механик — учебный сервер')


Lang = Literal['ru', 'uz', 'tg', 'ky', 'kk', 'hi', 'en']
VOICE_FIXTURES = {
    'ru': 'Как проверить тепловой зазор клапанов?',
    'uz': 'Klapanlarning issiqlik tirqishini qanday tekshiraman?',
    'tg': 'Фосилаи гармии клапанҳоро чӣ тавр санҷам?',
    'ky': 'Клапандардын жылуулук боштугун кантип текшерем?',
    'kk': 'Клапандардың жылу саңылауын қалай тексеремін?',
    'hi': 'वाल्व का क्लीयरेंस कैसे जाँचें?',
    'en': 'How do I check the valve clearance?',
}


class Chat(BaseModel):
    conversation_id: str
    vehicle_id: str
    session_id: str | None = None
    message: str = ''
    action: Literal['diagnose', 'draft_ticket'] | None = None
    lang: Lang = 'ru'
    detail: Literal['brief', 'detailed'] = 'brief'


@app.post('/api/transcribe')
async def transcribe(audio: UploadFile = File(...), lang: Lang = Form('ru')):
    """Exercise the upload contract without running speech recognition."""
    try:
        if not await audio.read(1):
            raise HTTPException(422, 'Пустая запись')
        return {'text': VOICE_FIXTURES[lang], 'lang': lang}
    finally:
        await audio.close()


class Confirm(BaseModel):
    draft_id: str
    conclusion: str | None = None
    urgency: Literal['low', 'medium', 'high'] | None = None
    operations: list[str] | None = None
    spare_parts: list[str] | None = None


def vehicle(vehicle_id):
    if vehicle_id not in VEHICLES:
        raise HTTPException(404, 'Машина не найдена')
    return VEHICLES[vehicle_id]


def diagnosis(v, s):
    # тексты повторяют формулировки настоящих правил (app/priority.py), чтобы снимки экрана совпадали с продуктом
    urgency, reasons = None, []
    if s['status'] == 'anomaly':
        repeats = sum(x['status'] == 'anomaly' and x['anomaly_type'] == s['anomaly_type'] and x['checked_at'] <= s['checked_at'] for x in v['sessions'])
        if v['vehicle_id'] == 'T792HO98' or (s['anomaly_score'] >= .92 and s['confidence'] >= .85 and s['signal_quality'] == 'good'):
            urgency = 'high'
            reasons.append('Неисправность серьезная, и сигнал сильный и программа в нем уверена.')
        elif repeats > 1 or s['anomaly_score'] >= .65:
            urgency = 'medium'
            reasons.append('Отклонение есть, но признаков, требующих дефектовки до выпуска, нет.' if repeats < 2
                           else ('Такое же отклонение уже было в прошлой проверке.' if repeats == 2 else f'Такое же отклонение уже было в {repeats - 1} прошлых проверках.'))
        else:
            urgency = 'low'
            reasons.append('Неисправность несерьезная: отклонение умеренное и пока разовое.')
        reasons.insert(0, f"Оценка отклонения {s['anomaly_score']:.2f} из 1, уверенность программы {s['confidence']:.2f}.")
        reasons.append('Это вывод по одной записи звука, а не осмотр машины.')
    action = {
        'anomaly': {'medium': 'Дефектовка на ближайшем ТО, машина работает под наблюдением.',
                    'low': 'Машина работает, узел проверить на следующей проверке.'}.get(urgency, ''),
        'normal': 'По звуку двигателя отклонений нет. Работайте по обычному графику ТО.',
        'check_failed': 'Запишите звук двигателя еще раз: по этой записи судить нельзя. Не запускайте двигатель ради записи при аварийном сигнале или сильном стуке.',
    }[s['status']]
    if urgency == 'high':
        action = 'Рекомендация: дефектовка до выпуска в рейс. Если машина уже в рейсе – остановитесь в безопасном месте и заглушите двигатель.'
    result = {**s, 'verdict': s['status'], 'urgency': urgency, 'urgency_reasons': reasons, 'action': action,
              'severity': 'C' if urgency == 'high' else None, 'rule': 'R4-critical' if urgency == 'high' else '',
              'inspect_first': s['session_id'] == 'S-0039', 'conf_threshold': 0.6}
    if s['session_id'] == 'S-0021':
        result.update(rule='R3-not-applicable', ticket_allowed=False, urgency=None,
                      warnings=['Программа указала F14 «Цепь ГРМ, гидронатяжитель», но у двигателя ЯМЗ-236М2 такого узла нет. '
                                'Данные машины верны – это ошибка программы оценки звука, а не диагноз: неисправность по ней не ставится.'],
                      action='Программа назвала узел, которого нет у этого двигателя, – это ошибка модели оценки звука, а не неисправность. '
                             'Повторите проверку или проведите дефектовку; заявку по этой проверке не создаем.',
                      defect_note=f"Рекомендация на дефектовку. Машина {s['vehicle_id']}, двигатель ЯМЗ-236М2, проверка {s['session_id']}: "
                                  f"программа оценки звука указала {s['anomaly_type']} «{s['anomaly_title']}». Такого узла у двигателя ЯМЗ-236М2 нет, "
                                  "инструкции по нему в руководстве нет. Нужна повторная проверка или дефектовка двигателя.")
    return result


def summary(v):
    latest = v['sessions'][-1] if v['sessions'] else None
    status = 'attention'
    if latest and latest['status'] == 'normal':
        status = 'ok'
    elif latest and latest['status'] == 'anomaly' and diagnosis(v, latest)['urgency'] == 'high':
        status = 'quarantine'
    rows = TICKETS.get(v['vehicle_id'], [])
    return {**{k: value for k, value in v.items() if k != 'sessions'}, 'last_check': latest, 'last_urgency': diagnosis(v, latest)['urgency'] if latest else None, 'last_severity': diagnosis(v, latest)['severity'] if latest else None, 'fleet_status': status, 'open_ticket': rows[-1]['ticket_id'] if rows and rows[-1]['session_id'] == (latest or {}).get('session_id') else None}


def manual_info(mid):
    if mid not in MANUALS or not (ROOT / 'data/manuals' / (mid + '.pdf')).is_file():
        raise HTTPException(404, 'Руководство не найдено')
    title, designation, _ = MANUALS[mid]
    return {'id': mid, 'title': title, 'designation': designation}


def open_page(mid, page):
    manual_info(mid)
    doc = pymupdf.open(ROOT / 'data/manuals' / (mid + '.pdf'))
    if not 1 <= page <= len(doc):
        doc.close()
        raise HTTPException(404, 'Такой страницы нет')
    return doc


@app.get('/api/health')
def health():
    return {'status': 'ok', 'mode': 'demo'}


@app.get('/api/vehicles')
def vehicles():
    return [summary(v) for v in VEHICLES.values()]


@app.get('/api/vehicles/{vehicle_id}')
def vehicle_card(vehicle_id: str):
    v = vehicle(vehicle_id)
    return {**summary(v), 'sessions': v['sessions'], 'tickets': TICKETS.get(vehicle_id, []), 'manuals': [manual_info(mid) for mid, (_, _, engines) in MANUALS.items() if v['engine_model'] in engines]}


@app.get('/api/fleet')
def fleet():
    summaries = vehicles()
    def rank(row):
        s = row['last_check'] or {}
        level = diagnosis(row | {'sessions': VEHICLES[row['vehicle_id']]['sessions']}, s)['urgency'] if s else None
        return ({'high': 3, 'medium': 2, 'low': 1}.get(level or '', 0), s.get('checked_at', ''))
    return {'counts': {status: sum(s['fleet_status'] == status for s in summaries) for status in ('ok', 'attention', 'quarantine')}, 'priority': sorted((s for s in summaries if s['fleet_status'] != 'ok'), key=rank, reverse=True)}


@app.get('/api/manuals/{manual_id}/pages/{page}.png')
@lru_cache(maxsize=12)
def page_png(manual_id: str, page: int):
    with open_page(manual_id, page) as doc:
        sheet = doc[page - 1]
        if manual_id == YAMZ and page == 31:
            for term in ('0,25-0,30 мм', '0,20-0,40 мм', 'Тепловые зазоры регулировать на холодном двигателе или менее чем через 15 минут после его остановки.'):
                matches = sheet.search_for(term)
                if matches:
                    sheet.add_highlight_annot(matches)
        return Response(sheet.get_pixmap(matrix=pymupdf.Matrix(1.55, 1.55)).tobytes('png'), media_type='image/png')


@app.get('/api/manuals/{manual_id}/pages/{page}')
def page_metadata(manual_id: str, page: int):
    info = manual_info(manual_id)
    with open_page(manual_id, page) as doc:
        return {'manual_id': manual_id, 'title': info['title'], 'designation': info['designation'], 'page': page, 'pages_total': len(doc), 'text': doc[page - 1].get_text()}


def step(tool, title, status, detail=''):
    return {'type': 'step', 'tool': tool, 'title': title, 'status': status, 'detail': detail}


def message(text, citations=()):
    return {'type': 'message', 'text': text, 'citations': list(citations)}


def reference(page, n, quote):
    info = manual_info(YAMZ)
    return {'n': n, 'manual_id': YAMZ, 'title': info['title'], 'designation': info['designation'], 'page': page, 'quote': quote}


def draft(v, s, result):
    specific = v['engine_model'] == 'ЯМЗ-236М2' and s['anomaly_type'] == 'F01'
    return {'draft_id': str(uuid4()), 'vehicle_id': v['vehicle_id'], 'session_id': s['session_id'], 'anomaly_type': s['anomaly_type'], 'conclusion': f"Возможная причина: {s['anomaly_title'][0].lower() + s['anomaly_title'][1:]}. Подтвердить при осмотре.", 'urgency': result['urgency'], 'urgency_reasons': result['urgency_reasons'], 'operations': ['Осмотреть клапанный механизм', 'Измерить зазоры и сверить с руководством'] if specific else ['Провести очный осмотр и подтвердить источник звука'], 'spare_parts': [], 'references': [{'manual': MANUALS[YAMZ][1], 'pdf_page': 31, 'manual_id': YAMZ, 'title': MANUALS[YAMZ][0]}] if specific else []}


@app.post('/api/chat')
def chat(req: Chat):
    v = vehicle(req.vehicle_id)
    sessions = v['sessions']
    s = next((x for x in sessions if x['session_id'] == req.session_id), None) if req.session_id else (sessions[-1] if sessions else None)
    if not s:
        raise HTTPException(404, 'Проверка не найдена у этой машины')
    result = diagnosis(v, s)

    async def events():
        if req.action == 'diagnose':
            title = 'Запрос результата проверки в ML-сервис'
            yield step('get_diagnosis', title, 'running', 'Ищем выбранную запись.')
            yield step('get_diagnosis', title, 'done', 'Запись найдена и результат получен.')
            yield {'type': 'diagnosis', 'data': result}
            await asyncio.sleep(float(os.environ.get('FAKE_EXPLAIN_DELAY', '0')))  # для проверки экрана ожидания объяснения
            yield message({'normal': 'По этой записи отклонений не видно. Если появятся стук, шум или лампа на панели – осмотрите машину.', 'anomaly': 'Тип отклонения указывает на возможную причину. Ее нужно подтвердить при осмотре. Можно обсудить результат или подготовить заявку на осмотр.', 'check_failed': 'Запись не подошла для анализа. О состоянии двигателя по ней судить нельзя.'}[s['status']])
        elif req.action == 'draft_ticket':
            title = 'Подготовка черновика заявки'
            yield step('draft_ticket', title, 'running', 'Собираем данные проверки.')
            if s['status'] != 'anomaly':
                yield step('draft_ticket', title, 'error', 'В этой проверке нет отклонения.')
                yield {'type': 'error', 'text': 'Черновик доступен только после обнаружения отклонения.'}
            else:
                d = draft(v, s, result)
                DRAFTS[d['draft_id']] = d
                yield step('draft_ticket', title, 'done', 'Черновик готов, ничего не отправлено.')
                yield {'type': 'draft', 'draft': d}
        else:
            title = 'Поиск и сверка в руководстве'
            yield step('search_manuals', title, 'running', f"Ищем по двигателю {v['engine_model']}.")
            question = req.message.casefold()
            if v['engine_model'] == 'ЯМЗ-236М2' and any(w in question for w in ('зазор', 'клапан', 'цокот', 'норматив')):
                yield step('search_manuals', title, 'done', 'Сверены PDF-страницы 31 и 33.')
                yield message('### Тепловые зазоры ЯМЗ-236М2\n- На холодном двигателе: **0,25-0,30 мм** для регулировки. После проворачивания вала при проверке: **0,20-0,40 мм**. [1]\n- Щуп **0,25 мм** проходит при лёгком нажиме, **0,30 мм** — с усилием. [2]\n\nНорматив из руководства не подтверждает неисправность вашей машины.', [reference(31, 1, Q31), reference(33, 2, Q33)])
            else:
                yield step('search_manuals', title, 'done', 'В тестовом сценарии подходящий фрагмент не найден.')
                yield message('В тестовом режиме нет проверенного ответа на этот вопрос. Не буду подставлять норматив от другого двигателя.')
        yield {'type': 'done'}

    async def stream():
        async for event in events():
            frame = ('data: ' + json.dumps(event, ensure_ascii=False) + '\n\n').encode('utf-8')
            # Split bytes, not characters, to exercise the client's streaming UTF-8 decoder.
            middle = len(frame) // 2
            yield frame[:middle]
            await asyncio.sleep(.035)
            yield frame[middle:]
            await asyncio.sleep(.12)

    return StreamingResponse(stream(), media_type='text/event-stream', headers={'Cache-Control': 'no-cache', 'X-Accel-Buffering': 'no'})


@app.post('/api/tickets/confirm')
async def confirm(req: Confirm):
    if req.draft_id not in DRAFTS:
        raise HTTPException(404, 'Черновик не найден')
    if req.draft_id in CONFIRMED:
        return CONFIRMED[req.draft_id]
    data = DRAFTS[req.draft_id] | req.model_dump(exclude_none=True)
    if not data['conclusion'].strip():
        raise HTTPException(422, 'Введите заключение')
    ticket_id = f"TKT-{sum(map(len, TICKETS.values())) + 1:04d}"
    TICKETS.setdefault(data['vehicle_id'], []).append({'ticket_id': ticket_id, 'session_id': data['session_id'], 'anomaly_type': data['anomaly_type'], 'urgency': data['urgency'], 'created_at': datetime.now(UTC).isoformat()})
    result = {'ticket_id': ticket_id, 'status': 'created'}
    CONFIRMED[req.draft_id] = result
    return result


@app.get('/', include_in_schema=False)
def index():
    return FileResponse(WEB / 'index.html')


@app.get('/{asset}', include_in_schema=False)
def static(asset: str):
    if asset not in {'app.js', 'styles.css', 'i18n.js', 'manifest.json', 'icon-192.png', 'icon-512.png', 'icon-maskable-512.png', 'apple-touch-icon.png'}:
        raise HTTPException(404)
    return FileResponse(WEB / asset)


if __name__ == '__main__':
    uvicorn.run(app, host='127.0.0.1', port=int(sys.argv[1]) if len(sys.argv) > 1 else 8174)
