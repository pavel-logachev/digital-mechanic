'use strict';

const $ = (selector, root = document) => root.querySelector(selector);
const main = $('#main'), dock = $('#dock'), topbar = $('#top'), manual = $('#manual');
const api = '/api';
const state = {route: {page: 'park'}, vehicles: null, fleet: null, cards: new Map(), sessions: new Map(), chats: new Map(), query: '', all: false, demo: false};
const fleetLabels = {ok: 'Норма', attention: 'Требует внимания', quarantine: 'Карантин'};
const stages = {normal: ['Норма', 'green', 'check'], anomaly: ['Отклонение', 'amber', 'warn'], check_failed: ['Плохая запись', 'red', 'cross']};
const priority = {low: 'Низкий', medium: 'Средний', high: 'Высокий'};
const quality = {good: 'Хорошее', warning: 'С помехами', bad: 'Плохое'};
const fleetTones = {ok: 'green', attention: 'amber', quarantine: 'red'};
const moscow = new Intl.DateTimeFormat('ru-RU', {timeZone: 'Europe/Moscow', day: '2-digit', month: '2-digit', year: '2-digit'});
const moscowTime = new Intl.DateTimeFormat('ru-RU', {timeZone: 'Europe/Moscow', hour: '2-digit', minute: '2-digit'});
const shortDate = new Intl.DateTimeFormat('ru-RU', {timeZone: 'Europe/Moscow', day: '2-digit', month: '2-digit'});
const number = new Intl.NumberFormat('ru-RU', {minimumFractionDigits: 2, maximumFractionDigits: 2});
const svgNS = 'http://www.w3.org/2000/svg';
const paths = {
  wave: 'M2 12h4l3-7 4 14 3-7h6', back: 'm14 6-6 6 6 6M8 12h13', next: 'm9 6 6 6-6 6', prev: 'm15 6-6 6 6 6',
  search: 'M15.5 15.5 21 21M17 11a6 6 0 1 1-12 0 6 6 0 0 1 12 0Z', truck: 'M6 18H3V6h12v12H9m6 0h3m3 0h1v-6l-3-4h-4m0 5h7M9 18a1.5 1.5 0 1 1-3 0 1.5 1.5 0 0 1 3 0Zm12 0a1.5 1.5 0 1 1-3 0 1.5 1.5 0 0 1 3 0Z',
  check: 'm5 12 4 4L19 6', cross: 'm8 8 8 8m0-8-8 8', warn: 'M12 8v5m0 3v.1M3 20l9-17 9 17Z',
  book: 'M4 4h11l4 4v12H4Zm10 0v5h5M8 12h7m-7 4h7', send: 'm3 3 18 9-18 9 4-9Zm4 9h14', chart: 'M4 4v16h16M7 15l4-5 4 2 5-6',
  clock: 'M12 7v5l3 2m6-2a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z', plus: 'M6 12h12m-6-6v12', minus: 'M6 12h12',
};

function el(tag, attrs = {}, ...children) {
  const node = document.createElement(tag);
  Object.entries(attrs).forEach(([key, value]) => {
    if (value == null || value === false) return;
    if (key.startsWith('on') && typeof value === 'function') node.addEventListener(key.slice(2), value);
    else node.setAttribute(key, value === true ? '' : value);
  });
  for (const child of children.flat(Infinity)) {
    if (child != null && child !== false) node.append(child);
  }
  return node;
}
function svg(tag, attrs) {
  const node = document.createElementNS(svgNS, tag);
  Object.entries(attrs).forEach(([key, val]) => node.setAttribute(key, val));
  return node;
}
function icon(name) {
  const node = svg('svg', {viewBox: '0 0 24 24', class: 'icon', 'aria-hidden': 'true', fill: 'none', stroke: 'currentColor', 'stroke-width': '1.75', 'stroke-linecap': 'round', 'stroke-linejoin': 'round'});
  node.append(svg('path', {d: paths[name]}));
  return node;
}
const mark = () => el('span', {class: 'mark'}, icon('wave'));
const action = (label, run, attrs = {}, ...extra) => el('button', {type: 'button', onclick: run, ...attrs}, label, ...extra);
const primary = (label, run, attrs = {}, ...extra) => action(label, run, {class: 'primary full', ...attrs}, ...extra);
const iconButton = (label, name, run, attrs = {}) => action(icon(name), run, {class: 'icon-button', 'aria-label': label, title: label, ...attrs});
const pill = (label, tone = '', symbol) => el('span', {class: `pill ${tone}`}, symbol && icon(symbol), label);
const stagePill = status => stages[status] ? pill(...stages[status]) : pill('Нет проверки');
const box = (...children) => el('section', {class: 'box'}, children);
const hint = (text, attrs = {}) => el('p', {class: 'muted', ...attrs}, text);
const mono = text => el('span', {class: 'mono'}, text);
const score = x => typeof x === 'number' && Number.isFinite(x) && x >= 0 && x <= 1;
const scoreText = x => score(x) ? number.format(x) : '—';
const stageOf = d => d?.verdict || d?.status;
const dateFor = (value, fmt) => {
  const date = new Date(value);
  return value && !isNaN(date) ? fmt ? fmt.format(date) : `${moscow.format(date)} ${moscowTime.format(date)}` : '—';
};
const endpoint = id => `${api}/vehicles/${encodeURIComponent(id)}`;
const manualPath = (id, page) => `${api}/manuals/${encodeURIComponent(id)}/pages/${page}`;
const jsonPost = body => ({method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(body)});

async function json(path, options) {
  const response = await fetch(path, options);
  const body = await response.json().catch(() => null);
  if (!response.ok || body == null) {
    const error = new Error(typeof body?.detail === 'string' ? body.detail : `Сервис вернул ошибку (${response.status}).`);
    error.status = response.status;
    throw error;
  }
  return body;
}
const titles = {park: 'Цифровой механик', fleet: 'Главный механик', vehicle: 'Карточка машины', draft: 'Черновик заявки', receipt: 'Заявка создана'};
function header() {
  const {page, vid} = state.route;
  const isPark = page === 'park', isChat = page === 'chat';
  topbar.replaceChildren(isPark ? mark() : iconButton('Назад', 'back', back), el('div', {class: 'brand'}, el('strong', {class: isChat ? 'plate' : null}, isChat ? vid : titles[page]), isPark && el('span', {}, 'Акустический пост')), state.demo ? el('span', {class: 'demo'}, 'ДЕМО') : '');
}
function navigate(route, replace = false) {
  history[replace ? 'replaceState' : 'pushState'](route, '', location.pathname);
  showRoute(route, true);
}
function back() { history.back(); }
window.addEventListener('popstate', e => showRoute(e.state?.page ? e.state : {page: 'park'}, true));
async function showRoute(route, focus = false) {
  state.route = route;
  header();
  dock.replaceChildren();
  main.className = route.page;
  main.scrollTop = 0;
  const load = route.page === 'park' && !state.vehicles ? async () => { state.vehicles = await json(`${api}/vehicles`); }
    : route.page === 'fleet' ? async () => { state.fleet = await json(`${api}/fleet`); }
    : route.vid && !state.cards.has(route.vid) ? async () => { state.cards.set(route.vid, await json(endpoint(route.vid))); }
    : null;
  if (load) {
    main.setAttribute('aria-busy', 'true');
    main.replaceChildren(hint('Загружаем данные…', {role: 'status'}));
    try { await load(); }
    catch (error) {
      if (state.route !== route) return;
      main.removeAttribute('aria-busy');
      main.replaceChildren(el('h1', {}, 'Не удалось загрузить данные'), hint(error.message, {role: 'alert'}), action('Повторить', () => showRoute(route, true)));
      return;
    }
    if (state.route !== route) return;
  }
  main.removeAttribute('aria-busy');
  render();
  if (focus) $('h1', main)?.focus({preventScroll: true});
}

function title(text) { return el('h1', {tabindex: '-1'}, text); }
function searchKey(value) {
  const alphabet = {'А':'A', 'В':'B', 'Е':'E', 'К':'K', 'М':'M', 'Н':'H', 'О':'O', 'Р':'P', 'С':'C', 'Т':'T', 'У':'Y', 'Х':'X'};
  return String(value ?? '').toUpperCase().replace(/[АВЕКМНОРСТУХ]/g, s => alphabet[s]).replace(/[^\p{L}\p{N}]/gu, '');
}
function vehicleRow(v, fromFleet = false) {
  const s = v.last_check;
  return action(el('span', {class: 'row-copy'},
    el('strong', {class: 'plate mono'}, v.vehicle_id),
    el('span', {class: 'muted row-model'}, [v.model, v.garage_no, v.engine_model].filter(Boolean).join(' / ')),
    el('span', {class: 'row-meta'}, fromFleet ? pill(fleetLabels[v.fleet_status], fleetTones[v.fleet_status], v.fleet_status === 'quarantine' ? 'warn' : null) : stagePill(s?.status), el('time', {class: 'mono muted', datetime: s?.checked_at}, dateFor(s?.checked_at))),
    fromFleet && s?.status === 'check_failed' ? el('span', {class: 'muted'}, 'Нужно повторить запись') : fromFleet && s?.anomaly_title ? el('span', {class: 'muted'}, s.anomaly_title) : null,
  ), () => navigate({page: 'vehicle', vid: v.vehicle_id}), {class: 'vehicle-row'}, icon('next'));
}
function renderPark() {
  const list = el('div', {class: 'vehicle-list'});
  const count = el('span', {class: 'muted mono', 'aria-live': 'polite'});
  const input = el('input', {id: 'vehicle-search', type: 'search', autocomplete: 'off', placeholder: 'Госномер или гаражный №', 'aria-label': 'Госномер или гаражный номер', oninput: e => { state.query = e.target.value; state.all = false; update(); }});
  const update = () => {
    const key = searchKey(state.query);
    const ordered = [...state.vehicles].sort((a, b) => (b.last_check?.checked_at || '').localeCompare(a.last_check?.checked_at || ''));
    const found = key ? ordered.filter(v => [v.vehicle_id, v.garage_no].some(x => searchKey(x).includes(key))) : ordered;
    const visible = state.all ? found : found.slice(0, 8);
    count.textContent = `${found.length} из ${ordered.length}`;
    list.replaceChildren(...visible.map(v => vehicleRow(v)));
    if (!found.length) list.append(box(el('strong', {}, 'Ничего не найдено'), hint('Проверьте госномер или введите только цифры гаражного номера.')));
    if (visible.length < found.length) list.append(action(`Показать все (${found.length})`, () => { state.all = true; update(); list.children[8]?.focus(); }));
  };
  input.value = state.query;
  update();
  main.replaceChildren(el('div', {class: 'intro'}, title('Выберите машину'), hint('Откройте запись для акустической проверки.')), el('label', {class: 'search'}, icon('search'), input), action('Главный механик', () => navigate({page: 'fleet'}), {class: 'wide-link'}, icon('chart')), el('div', {class: 'between'}, el('h2', {}, 'Последние проверки'), count), list, el('p', {class: 'time-note muted'}, icon('clock'), 'Время проверок указано по Москве'));
}
function renderFleet() {
  const items = state.fleet.priority ?? [];
  main.replaceChildren(
    el('div', {class: 'intro'}, title('Сводка парка'), hint('Статусы машин по данным парка.')),
    el('div', {class: 'fleet-counts'}, Object.entries(fleetLabels).map(([key, label]) => el('div', {class: `fleet-count ${fleetTones[key]}`}, el('strong', {class: 'mono'}, String(state.fleet.counts?.[key] ?? '—')), el('span', {}, label)))),
    el('h2', {}, 'Приоритетный список'),
    items.length ? el('div', {class: 'vehicle-list'}, items.map(v => vehicleRow(v, true))) : box(hint('Нет машин, которым нужно внимание.')),
  );
}
function context(v, s, chat = false) {
  const label = chat ? v.garage_no && `Гаражный № ${v.garage_no}` : [v.vehicle_id, v.garage_no].filter(Boolean).join(' / ');
  return el('div', {class: chat ? 'context chat-context' : 'context'}, icon('truck'),
    el('div', {class: 'context-copy'}, label && el('strong', {class: chat ? null : 'mono'}, label), el('span', {class: 'muted'}, [v.model, v.engine_model].filter(Boolean).join(' / '))),
    el('time', {class: 'mono', datetime: s?.checked_at}, el('span', {}, dateFor(s?.checked_at, moscow)), s?.checked_at ? el('span', {}, dateFor(s.checked_at, moscowTime)) : null));
}
function graph(sessions) {
  const recent = sessions.slice(-5);
  if (!recent.length) return null;
  const x = i => recent.length === 1 ? 168 : 40 + i * 254 / (recent.length - 1);
  const y = d => 58 - 42 * d;
  const desc = recent.map(s => `${dateFor(s.checked_at, shortDate)}: ${s.status === 'check_failed' ? 'сбой проверки' : score(s.anomaly_score) ? scoreText(s.anomaly_score) : 'нет оценки'}`).join('; ');
  const canvas = svg('svg', {viewBox: '0 0 336 100', class: 'spark', role: 'img', 'aria-label': desc});
  for (const [value, label] of [[1, '1'], [0.5, ''], [0, '0']]) {
    canvas.append(svg('line', {x1: 30, x2: 306, y1: y(value), y2: y(value), class: 'gridline'}));
    const text = svg('text', {x: 17, y: y(value) + 4, 'text-anchor': 'middle'});
    text.textContent = label;
    canvas.append(text);
  }
  recent.forEach((s, i) => {
    const real = d => d && d.status !== 'check_failed' && score(d.anomaly_score);
    if (real(s) && real(recent[i - 1])) canvas.append(svg('line', {x1: x(i-1), y1: y(recent[i-1].anomaly_score), x2: x(i), y2: y(s.anomaly_score), class: 'sparkline'}));
  });
  recent.forEach((s, i) => {
    if (s.status === 'check_failed') canvas.append(svg('path', {d: `M${x(i)-4} 71l8 8m0-8-8 8`, class: 'failed-mark'}));
    else if (score(s.anomaly_score)) canvas.append(svg('circle', {cx: x(i), cy: y(s.anomaly_score), r: 4, class: s.status === 'anomaly' ? 'point-anomaly' : 'point-normal'}));
    const date = svg('text', {x: x(i), y: 95, 'text-anchor': 'middle'});
    date.textContent = dateFor(s.checked_at, shortDate);
    canvas.append(date);
  });
  return el('figure', {class: 'box trend'}, el('figcaption', {}, el('strong', {}, 'Оценка отклонения'), el('span', {class: 'muted'}, `Последние проверки: ${recent.length}`)), canvas, hint('× — сбой, оценки нет. Шкала от 0 до 1. Без сравнения условий записи рост не доказывает ухудшение.'));
}
function renderVehicle(v) {
  const sessions = v.sessions ?? [];
  const current = state.sessions.get(v.vehicle_id) ?? sessions.at(-1)?.session_id;
  const historyRows = [...sessions].reverse().map(s => el('label', {class: 'check-row'},
    el('input', {type: 'radio', name: 'check', value: s.session_id, checked: current === s.session_id, onchange: () => { state.sessions.set(v.vehicle_id, s.session_id); }}),
    el('span', {class: 'check-copy'}, el('time', {class: 'mono', datetime: s.checked_at}, dateFor(s.checked_at)), stagePill(s.status)),
    el('span', {class: 'mono check-score', 'aria-label': s.status === 'check_failed' ? 'Нет оценки' : `Оценка отклонения ${scoreText(s.anomaly_score)}`}, s.status === 'check_failed' ? '×' : scoreText(s.anomaly_score)),
  ));
  const tickets = [...(v.tickets ?? [])].reverse();
  main.replaceChildren(
    el('section', {class: 'box vehicle-head'}, el('div', {class: 'between'}, hint(v.model || v.make), icon('truck')), title(v.vehicle_id), el('div', {class: 'between'}, mono(v.garage_no || 'Гаражный номер не указан'), v.fleet_status ? pill(fleetLabels[v.fleet_status], fleetTones[v.fleet_status]) : null), el('div', {class: 'engine muted'}, 'Двигатель: ', el('strong', {}, v.engine_model || 'не указан'), v.fuel ? ` / ${v.fuel}` : '')),
    el('fieldset', {class: 'history'}, el('legend', {}, 'История проверок'), sessions.length ? el('div', {class: 'checks'}, historyRows) : box(hint('Проверок пока нет.'))),
    graph(sessions),
    el('section', {class: 'stack'}, el('h2', {}, 'Прошлые заявки'), tickets.length ? el('div', {class: 'box tickets'}, tickets.map(t => el('div', {class: 'between'}, el('span', {}, el('strong', {class: 'mono'}, t.ticket_id), el('span', {class: 'muted ticket-meta'}, [t.anomaly_type, dateFor(t.created_at)].filter(Boolean).join(' / '))), priority[t.urgency] ? pill(priority[t.urgency], t.urgency === 'high' ? 'red' : 'amber') : null))) : box(hint('Заявок пока нет.'))),
  );
  dock.replaceChildren(el('div', {class: 'dock'}, primary('Получить результат диагностики', () => {
    const sid = state.sessions.get(v.vehicle_id) ?? current;
    if (!sid) return;
    const conversation = conversationFor(v.vehicle_id, sid);
    navigate({page: 'chat', vid: v.vehicle_id, sid});
    if (!conversation.busy) sendChat(conversation, 'diagnose');
  }, {id: 'diagnose', disabled: !sessions.length}, icon('next')), sessions.length ? hint('Откроется результат выбранной записи.') : null));
}

function conversationFor(vid, sid) {
  const key = JSON.stringify([vid, sid]);
  if (!state.chats.has(key)) {
    let id;
    try { id = sessionStorage.getItem(`mechanic:${key}`); } catch { /* private storage disabled */ }
    if (!id) {
      id = globalThis.crypto?.randomUUID?.() ?? Array.from(globalThis.crypto.getRandomValues(new Uint8Array(16)), n => n.toString(16).padStart(2, '0')).join('');
      try { sessionStorage.setItem(`mechanic:${key}`, id); } catch { /* keep in memory */ }
    }
    state.chats.set(key, {id, vid, sid, turns: [], verdict: null, draft: null, receipt: null, busy: false, question: ''});
  }
  return state.chats.get(key);
}
function isCurrent(c, page = 'chat') {
  return state.route.page === page && state.route.vid === c.vid && state.route.sid === c.sid;
}
function reasons(values) {
  const entries = Array.isArray(values) ? values.filter(Boolean) : [];
  return entries.length ? el('ul', {class: 'reasons'}, entries.map(line => el('li', {}, line))) : hint('Сервис не указал основания.');
}
function warnings(values) {
  const entries = Array.isArray(values) ? values.filter(Boolean) : [];
  return entries.length ? el('section', {class: 'box warnings'}, icon('warn'), el('div', {}, el('h3', {}, 'Важно'), reasons(entries))) : null;
}
function metric(label, value, low, high) {
  const band = score(value) ? value >= high ? 'высокая' : value >= low ? 'средняя' : 'низкая' : null;
  return el('div', {class: 'metric'}, el('dt', {}, label), el('dd', {}, band ? el('strong', {}, `${scoreText(value)} из 1 — ${band}`) : 'Нет данных'));
}
function verdict(d, id, opens) {
  const status = stageOf(d);
  const fail = status === 'check_failed', normal = status === 'normal';
  const incompatible = d.rule === 'R3-not-applicable';
  const hypothesis = d.anomaly_title?.replace(/^\p{Lu}(?=\p{Ll})/u, first => first.toLocaleLowerCase('ru-RU'));
  const vTitle = normal ? 'Отклонений не выявлено' : fail ? 'Сбой записи' : incompatible ? 'Тип отклонения не подтверждён' : hypothesis ? `Гипотеза: ${hypothesis}` : 'Есть признаки отклонения';
  const flag = normal ? ['Норма', 'green', 'check'] : fail ? ['Запись непригодна', 'red', 'cross'] : ['Отклонение по записи', 'amber', 'warn'];
  const urgency = priority[d.urgency];
  const next = el('div', {class: 'next-action'}, el('h3', {}, 'Что делать'), el('p', {}, d.action || (fail ? 'Запишите звук заново.' : normal ? 'Следуйте правилам вашего парка.' : 'Проверьте машину очно.')));
  const note = fail ? 'Заявка по этой проверке не создаётся.' : normal ? null : incompatible ? `${d.anomaly_type ? `Код ${d.anomaly_type} · ` : ''}модель определила класс по звуку` : `${d.anomaly_type ? `Код ${d.anomaly_type} · ` : ''}вывод по звуку, подтвердите при осмотре`;
  const top = el('div', {class: `verdict-head ${flag[1]}`}, pill(...flag), el('h2', {}, vTitle), next,
    el('span', {class: `pill priority-badge${urgency ? ` priority-${d.urgency}` : ''}`}, `Приоритет: ${urgency ? urgency.toLowerCase() : 'не назначен'}`),
    note && el('p', {class: 'verdict-note'}, note));
  const metrics = !fail && el('dl', {class: 'box metrics'}, metric('Оценка отклонения', d.anomaly_score, .4, .7), metric('Уверенность модели', d.confidence, .6, .8), el('div', {class: 'metric'}, el('dt', {}, 'Качество записи'), el('dd', {}, el('strong', {}, quality[d.signal_quality] ?? 'Нет данных'))));
  const key = `priority-${id}`;
  const why = Array.isArray(d.urgency_reasons) && d.urgency_reasons.length > 0 && el('details', {class: 'priority-reasons', open: opens.has(key), 'data-trace': key},
    el('summary', {}, urgency ? 'Основание приоритета' : 'Основание результата'), reasons(d.urgency_reasons));
  return el('article', {class: `verdict ${status}`}, top, warnings(d.warnings), metrics, why);
}

function citationLink(cite, label, attrs = {}) {
  return el('a', {href: manualPath(cite.manual_id, cite.page), ...attrs, onclick: e => {
    if (e.button !== 0 || e.metaKey || e.ctrlKey || e.altKey || e.shiftKey) return;
    e.preventDefault();
    openManual(cite);
  }}, label);
}
function markdown(text, citations) {
  const rendered = el('div', {class: 'markdown'});
  const sources = new Map((citations ?? []).filter(c => c.manual_id && Number.isInteger(c.page) && c.page > 0).map(c => [Number(c.n), c]));
  const inline = (value, allowBold = true) => {
    const nodes = [], pattern = allowBold ? /\*\*([^*]+)\*\*|\[(\d+)\]/g : /\[(\d+)\]/g;
    let start = 0;
    for (const match of value.matchAll(pattern)) {
      nodes.push(value.slice(start, match.index));
      if (allowBold && match[1]) nodes.push(el('strong', {}, inline(match[1], false)));
      else {
        const n = Number(match[allowBold ? 2 : 1]);
        const cite = sources.get(n);
        if (cite) {
          nodes.push(citationLink(cite, match[0], {class: 'citation-chip inline-cite', 'aria-label': `Источник ${n}: ${cite.designation || cite.title}, страница ${cite.page}`}));
        } else nodes.push(match[0]);
      }
      start = match.index + match[0].length;
    }
    nodes.push(value.slice(start));
    return nodes;
  };
  let paragraph = null, list = null;
  for (const line of String(text ?? '').split(/\r?\n/)) {
    const heading = /^#{1,6}\s+(.+)$/.exec(line);
    const item = /^(?:([-+*])|(\d+)[.)])\s+(.+)$/.exec(line.trim());
    if (heading || item || !line.trim()) paragraph = null;
    if (heading) {
      list = null;
      rendered.append(el('h3', {}, inline(heading[1])));
    } else if (item) {
      const tag = item[1] ? 'UL' : 'OL';
      if (list?.tagName !== tag) { list = el(tag.toLowerCase()); rendered.append(list); }
      list.append(el('li', {}, inline(item[3])));
    } else if (line.trim()) {
      list = null;
      if (!paragraph) { paragraph = el('p'); rendered.append(paragraph); }
      else paragraph.append(el('br'));
      paragraph.append(...inline(line));
    } else list = null;
  }
  const references = [...sources].sort(([a], [b]) => a - b);
  const footer = references.length ? el('footer', {class: 'message-sources'}, el('strong', {}, 'Источники:'), el('ul', {}, references.map(([n, cite]) =>
    el('li', {}, citationLink(cite, [el('span', {class: 'citation-chip'}, `[${n}]`), el('span', {class: 'citation-excerpt'},
      el('strong', {}, `${cite.designation || cite.title}, стр. ${cite.page}`), cite.quote && ` — «${cite.quote}»`)], {class: 'citation-row'}))))) : null;
  return [rendered, footer];
}
function trace(turn, open) {
  if (!turn.steps.length) return null;
  const last = turn.steps.at(-1);
  const current = last.status === 'running';
  const localized = value => String(value ?? '').replaceAll('ML-сервис', 'сервис диагностики');
  return el('details', {class: 'trace', open, 'data-trace': turn.id}, el('summary', {}, el('span', {}, el('strong', {}, 'Журнал шагов'), el('span', {class: 'muted trace-last'}, current ? `${localized(last.title)}…` : localized(last.title))), pill(String(turn.steps.length), '', null)),
    el('ol', {}, turn.steps.map(s => el('li', {}, el('div', {class: 'between'}, el('strong', {}, localized(s.title)), pill(s.status === 'running' ? 'В работе' : s.status === 'error' ? 'Ошибка' : 'Готово', s.status === 'error' ? 'red' : s.status === 'done' ? 'green' : 'amber')), s.detail ? hint(s.detail) : null))),
  );
}
function renderTurn(turn, latest, opens, receipt) {
  const block = el('section', {class: 'turn'});
  if (turn.question) block.append(el('div', {class: 'user-message'}, el('strong', {}, 'Механик'), el('p', {}, turn.question)));
  const answers = () => turn.messages.map(m => el('article', {class: 'box agent-message'}, el('div', {class: 'byline'}, mark(), el('strong', {}, 'Цифровой механик')), markdown(m.text, m.citations)));
  const log = trace(turn, opens.has(String(turn.id)));
  if (turn.diagnosis && !latest) {
    block.append(el('details', {class: 'previous', open: opens.has(`verdict-${turn.id}`), 'data-trace': `verdict-${turn.id}`}, el('summary', {}, el('strong', {}, 'Результат диагностики'), stagePill(stageOf(turn.diagnosis))), verdict(turn.diagnosis, turn.id, opens), log, answers()));
  } else {
    if (turn.diagnosis) block.append(verdict(turn.diagnosis, turn.id, opens));
    if (log) block.append(log);
    block.append(...answers());
  }
  for (const error of turn.errors) block.append(el('p', {class: 'notice red', role: 'alert'}, error));
  if (turn.draft && !receipt && !turn.pending) block.append(action('Открыть черновик заявки', () => navigate({page: 'draft', vid: turn.draft.vehicle_id, sid: turn.draft.session_id}), {class: 'full'}, icon('next')));
  return block;
}
const spinner = () => el('span', {class: 'spinner', 'aria-hidden': 'true'});
const runningSteps = {
  get_diagnosis: 'Получаю результат проверки', get_vehicle_history: 'Сверяю историю машины', search_manual: 'Ищу в руководстве', search_manuals: 'Ищу в руководстве',
  read_page: 'Читаю страницу руководства', get_fault_reference: 'Уточняю класс неисправности', prepare_ticket: 'Готовлю черновик заявки', draft_ticket: 'Готовлю черновик заявки',
};
function pendingText(turn) {
  const step = turn?.steps.at(-1);
  if (!step) return 'Агент готовит ответ…';
  if (step.status !== 'running') {
    if (step.status === 'done' && ['search_manual', 'search_manuals'].includes(step.tool)) return 'Сверяю найденные страницы руководства…';
    return 'Агент готовит ответ…';
  }
  const label = runningSteps[step.tool] ?? step.title ?? 'Агент выполняет следующий шаг';
  return step.detail ? `${label}: ${step.detail}` : `${label}…`;
}
const canDraft = d => stageOf(d) === 'anomaly' && d.ticket_allowed !== false;
function updateChat(c, latestOnly = false, scrollTo = null) {
  if (!isCurrent(c)) return;
  const feed = $('#conversation');
  if (!feed) return;
  const turn = c.turns.at(-1);
  const opens = new Set([...feed.querySelectorAll('details[open]')].map(d => d.dataset.trace));
  if (latestOnly && turn && feed.lastElementChild) feed.lastElementChild.replaceWith(renderTurn(turn, true, opens, c.receipt));
  else feed.replaceChildren(...c.turns.map((t, i) => renderTurn(t, i === c.turns.length - 1, opens, c.receipt)));
  const progress = $('#chat-progress');
  $('#chat-progress-row').hidden = !c.busy;
  const statusText = c.busy ? pendingText(turn) : '';
  if (progress.textContent !== statusText) progress.textContent = statusText;
  const controls = $('#chat-controls');
  const status = stageOf(c.verdict);
  const commands = [];
  if (c.receipt) commands.push(primary('Открыть квитанцию', () => navigate({page: 'receipt', vid: c.vid, sid: c.sid}), {disabled: c.busy}));
  else if (canDraft(c.verdict)) commands.push(primary(c.draft ? 'Открыть черновик заявки' : 'Создать заявку', () => {
    if (c.draft) navigate({page: 'draft', vid: c.vid, sid: c.sid});
    else sendChat(c, 'draft_ticket');
  }, {'data-command': 'draft', disabled: c.busy}, icon('next')));
  else if (!c.busy && !status) commands.push(primary('Получить результат диагностики', () => sendChat(c, 'diagnose')));
  else if (status === 'check_failed' || status === 'normal') commands.push(action('Вернуться к машине', back, {class: 'full', disabled: c.busy}));
  const quick = c.turns.every(t => !t.question) && status === 'anomaly' && !c.busy;
  const shortcuts = $('#quick-questions');
  shortcuts.hidden = !quick;
  shortcuts.replaceChildren(...(quick ? [action('Сверить норматив', () => ask(c, 'Какой норматив по этой проверке?')), action('Что проверить?', () => ask(c, 'Что проверить при осмотре?'))] : []));
  controls.replaceChildren(...commands);
  $('#question').disabled = c.busy;
  $('#send-question').disabled = c.busy || !c.question.trim();
  if (scrollTo) {
    const target = [...feed.lastElementChild.children].filter(node => node.matches(scrollTo)).at(-1);
    target?.scrollIntoView({block: 'start'});
  }
}
function renderChat(v, s, c) {
  main.replaceChildren(el('h1', {tabindex: '-1', class: 'visually-hidden'}, v.vehicle_id), context(v, s, true), el('div', {id: 'conversation', role: 'log', 'aria-label': 'Диалог о проверке', 'aria-live': 'polite'}), el('div', {id: 'quick-questions', class: 'quick', hidden: true}));
  const composer = el('form', {class: 'compose', onsubmit: e => { e.preventDefault(); ask(c, c.question); }},
    el('input', {id: 'question', name: 'question', placeholder: 'Напишите вопрос', 'aria-label': 'Напишите вопрос', autocomplete: 'off', maxlength: '2000', oninput: e => { c.question = e.target.value; $('#send-question').disabled = c.busy || !c.question.trim(); }}),
    el('button', {id: 'send-question', class: 'primary icon-button', type: 'submit', 'aria-label': 'Отправить вопрос'}, icon('send')),
  );
  dock.replaceChildren(el('div', {class: 'dock chat-dock'}, el('div', {class: 'chat-status', id: 'chat-progress-row', hidden: true}, spinner(), el('span', {id: 'chat-progress', role: 'status'})), el('div', {id: 'chat-controls', class: 'stack'}), composer));
  $('#question').value = c.question;
  updateChat(c);
}
function ask(c, value) {
  const q = value.trim();
  if (!q || c.busy) return;
  c.question = '';
  const input = $('#question');
  if (input) input.value = '';
  sendChat(c, null, q);
}

// Accept all SSE line endings and events split mid-character or mid-line.
async function readEvents(response, visit) {
  if (!response.body || !response.headers.get('content-type')?.includes('text/event-stream')) throw new Error('Сервис не открыл поток ответа.');
  const reader = response.body.getReader(), decoder = new TextDecoder();
  let line = '', data = [], cr = false;
  function flushLine() {
    if (!line && data.length) { visit(JSON.parse(data.join('\n'))); data = []; }
    else if (line === 'data' || line.startsWith('data:')) data.push(line.slice(5).replace(/^ /, ''));
    line = '';
  }
  function parse(text) {
    for (const char of text) {
      if (cr && char === '\n') { cr = false; continue; }
      cr = char === '\r';
      if (cr || char === '\n') flushLine();
      else line += char;
    }
  }
  let finished = false;
  try {
    while (true) {
      const {done, value} = await reader.read();
      if (done) { finished = true; break; }
      parse(decoder.decode(value, {stream: true}));
    }
    parse(decoder.decode());
  } finally {
    if (!finished) await reader.cancel().catch(() => {});
    reader.releaseLock();
  }
}
async function sendChat(c, mode, question = '') {
  if (c.busy || (mode === 'draft_ticket' && !canDraft(c.verdict))) return;
  c.busy = true;
  const turn = {id: c.turns.length + 1, question, pending: true, steps: [], messages: [], errors: []};
  c.turns.push(turn);
  updateChat(c, false, question ? '.user-message' : null);
  if (mode === 'diagnose' && isCurrent(c)) main.scrollTop = 0;
  let done = false;
  try {
    const res = await fetch(`${api}/chat`, jsonPost({conversation_id: c.id, vehicle_id: c.vid, session_id: c.sid, message: question, action: mode}));
    if (!res.ok) {
      const body = await res.json().catch(() => null);
      throw new Error(typeof body?.detail === 'string' ? body.detail : `Сервис вернул ошибку (${res.status}).`);
    }
    await readEvents(res, event => {
      if (event.type === 'step') {
        const previous = turn.steps.findLastIndex(s => s.tool === event.tool && s.title === event.title && s.status === 'running');
        if (previous !== -1) turn.steps[previous] = event;
        else turn.steps.push(event);
      } else if (event.type === 'diagnosis' && stages[stageOf(event.data)]) {
        c.verdict = turn.diagnosis = event.data;
      } else if (event.type === 'message') turn.messages.push(event);
      else if (event.type === 'draft' && mode === 'draft_ticket' && event.draft?.draft_id) {
        turn.draft = c.draft = event.draft;
        c.edits = {conclusion: c.draft.conclusion || '', urgency: c.draft.urgency || '', operations: (c.draft.operations || []).join('\n'), spare_parts: (c.draft.spare_parts || []).join('\n')};
      } else if (event.type === 'error') turn.errors.push(event.text || 'Агент не смог выполнить запрос.');
      else if (event.type === 'done') { done = true; return; }
      else return;
      updateChat(c, true, event.type === 'message' && mode !== 'diagnose' ? '.agent-message' : null);
    });
    if (!done) throw new Error('Поток прервался. Ответ мог быть неполным.');
    if (!turn.errors.length && mode === 'diagnose' && !turn.diagnosis) throw new Error('Сервис не прислал результат проверки.');
    if (!turn.errors.length && mode === 'draft_ticket' && !turn.draft) throw new Error('Сервис не прислал черновик.');
  } catch (error) {
    turn.errors.push(error instanceof TypeError ? 'Нет связи с сервисом. Проверьте подключение и повторите запрос.' : error.message);
  } finally {
    c.busy = false;
    turn.pending = false;
    updateChat(c, true, turn.errors.length ? '.notice' : null);
    if (turn.draft && isCurrent(c) && !turn.errors.length) navigate({page: 'draft', vid: c.vid, sid: c.sid});
  }
}

function field(c, name, label, rows, placeholder = '') {
  const input = el('textarea', {name, rows, placeholder, required: name === 'conclusion', oninput: e => { c.edits[name] = e.target.value; }});
  input.value = c.edits[name];
  return el('label', {class: 'field'}, el('span', {}, label), input);
}
function renderDraft(v, s, c) {
  if (c.receipt) { renderReceipt(v, s, c); return; }
  if (!c.draft) { main.replaceChildren(title('Черновик не найден'), action('Назад', back)); return; }
  const d = c.draft;
  const override = el('input', {name: 'urgency_reason', maxlength: '350', value: c.edits.urgencyReason || '', oninput: e => { c.edits.urgencyReason = e.target.value; }});
  const overrideField = el('label', {class: 'field'}, el('span', {}, 'Почему меняете приоритет?'), override, hint('Причина войдёт в заключение.'));
  const syncOverride = () => { overrideField.hidden = !urgency.value || urgency.value === d.urgency; override.required = !overrideField.hidden; };
  const urgency = el('select', {name: 'urgency', required: true, onchange: e => { c.edits.urgency = e.target.value; syncOverride(); }}, [el('option', {value: '', disabled: true}, 'Выберите приоритет'), ...Object.entries(priority).map(([key, label]) => el('option', {value: key}, label))]);
  urgency.value = c.edits.urgency;
  syncOverride();
  const references = (d.references ?? []).filter(r => r.manual_id && Number.isInteger(r.pdf_page) && r.pdf_page > 0);
  const form = el('form', {class: 'stack', id: 'draft-form', onsubmit: e => { e.preventDefault(); confirmTicket(c); }},
    el('section', {class: 'box stack'}, d.anomaly_type || c.verdict?.anomaly_title ? el('p', {class: 'muted'}, 'Тип отклонения: ', el('strong', {}, [d.anomaly_type, c.verdict?.anomaly_title].filter(Boolean).join(' — '))) : null, field(c, 'conclusion', 'Заключение (гипотеза)', 2)),
    el('section', {class: 'box stack'}, el('label', {class: 'field'}, el('span', {}, 'Приоритет в заявке'), urgency), overrideField,
      el('details', {class: 'priority-reasons'}, el('summary', {}, 'Основание приоритета'), reasons(d.urgency_reasons))),
    el('section', {class: 'box stack'}, field(c, 'operations', 'Работы', 2, 'Каждая работа с новой строки'), field(c, 'spare_parts', 'Запчасти', 1, 'Каждая позиция с новой строки')),
    references.length ? el('section', {class: 'box stack'}, el('h2', {}, 'Источники'), references.map(r => citationLink({manual_id: r.manual_id, title: r.title || r.manual, page: r.pdf_page}, [icon('book'), `${r.title || r.manual}, стр. ${r.pdf_page}`, icon('next')], {class: 'source-link'}))) : null,
    el('p', {id: 'ticket-error', role: 'alert', class: 'notice red', hidden: !c.confirmError}, c.confirmError || ''),
  );
  const warning = warnings(d.warnings);
  main.replaceChildren(context(v, s), el('div', {class: 'intro'}, pill('Не отправлена', 'amber'), title('Заявка на осмотр')), ...(warning ? [warning] : []), form);
  dock.replaceChildren(el('div', {class: 'dock'}, el('button', {id: 'confirm-ticket', class: 'primary full', type: 'submit', form: 'draft-form', disabled: c.confirming || c.confirmUncertain}, c.confirming ? 'Отправляем…' : 'Подтвердить и отправить в ТОиР', icon('check')), hint('В ТОиР попадёт только подтверждённая заявка.')));
}
async function confirmTicket(c) {
  if (c.confirming || c.confirmUncertain || c.receipt) return;
  const lines = value => value.split(/\r?\n/).map(line => line.trim()).filter(Boolean);
  const conclusion = c.edits.conclusion.trim();
  const override = c.edits.urgency !== c.draft.urgency ? (c.edits.urgencyReason || '').trim() : '';
  const payload = {draft_id: c.draft.draft_id, conclusion: override ? `${conclusion}\nПричина изменения приоритета: ${override}` : conclusion, urgency: c.edits.urgency, operations: lines(c.edits.operations), spare_parts: lines(c.edits.spare_parts)};
  const invalid = !conclusion ? 'Введите заключение.' : c.edits.urgency !== c.draft.urgency && !override ? 'Укажите причину изменения приоритета.' : '';
  if (invalid) { $('#ticket-error').hidden = false; $('#ticket-error').textContent = invalid; return; }
  c.confirming = true;
  c.confirmError = '';
  const button = $('#confirm-ticket');
  button.disabled = true;
  button.textContent = 'Отправляем…';
  $('#ticket-error').hidden = true;
  try {
    const data = await json(`${api}/tickets/confirm`, jsonPost(payload));
    if (data.status !== 'created' || !data.ticket_id) throw new Error('Не получили номер заявки.');
    c.receipt = {id: data.ticket_id, payload};
    state.vehicles = null;
    if (isCurrent(c, 'draft')) navigate({page: 'receipt', vid: c.vid, sid: c.sid}, true);
    try {
      const updated = await json(endpoint(c.vid));
      state.cards.set(c.vid, updated);
    } catch { state.cards.delete(c.vid); }
  } catch (error) {
    c.confirmUncertain = !error.status || error.status >= 500;
    c.confirmError = c.confirmUncertain ? 'Подтверждение не пришло. Перед повторной попыткой проверьте, появилась ли заявка в ТОиР.' : error.message;
  } finally {
    c.confirming = false;
    if (isCurrent(c, 'draft')) render();
  }
}
function renderReceipt(v, s, c) {
  if (!c.receipt) { main.replaceChildren(title('Квитанция недоступна'), action('Назад', back)); return; }
  const result = c.receipt;
  const fields = [['Машина', [v.vehicle_id, v.garage_no].filter(Boolean).join(' / ')], ['Проверка', dateFor(s?.checked_at)], ['Заключение', result.payload.conclusion], ['Приоритет', priority[result.payload.urgency]]];
  main.replaceChildren(el('section', {class: 'receipt green'}, pill('Принята ТОиР', 'green', 'check'), title('Заявка создана'), el('strong', {class: 'receipt-id mono'}, result.id), el('p', {}, 'Номер вернула система ТОиР.')), el('section', {class: 'box stack'}, el('h2', {}, 'Что отправили'), el('dl', {class: 'receipt-fields'}, fields.map(([label, value]) => el('div', {}, el('dt', {}, label), el('dd', {}, value)))), el('p', {class: 'muted'}, 'Заявка появится в карточке машины.')));
  dock.replaceChildren(el('div', {class: 'dock'}, primary('К списку машин', () => navigate({page: 'park'}))));
}
function render() {
  const route = state.route;
  dock.replaceChildren();
  if (route.page === 'park') return renderPark();
  if (route.page === 'fleet') return renderFleet();
  const v = state.cards.get(route.vid);
  if (!v) return;
  if (route.page === 'vehicle') return renderVehicle(v);
  const s = (v.sessions ?? []).find(check => check.session_id === route.sid);
  const c = conversationFor(route.vid, route.sid);
  if (route.page === 'chat') renderChat(v, s, c);
  else if (route.page === 'draft') renderDraft(v, s, c);
  else if (route.page === 'receipt') renderReceipt(v, s, c);
}

let viewer;
function openManual(cite) {
  viewer = {cite, serial: 0, trigger: document.activeElement};
  manual.replaceChildren();
  if (!manual.open) manual.showModal();
  document.body.classList.add('viewing-page');
  loadManual(cite.page);
}
manual.addEventListener('close', () => {
  document.body.classList.remove('viewing-page');
  viewer?.trigger?.focus({preventScroll: true});
  viewer = null;
});
function pageText(text, quote) {
  const needle = String(quote ?? '').trim().replace(/^…|…$/g, '').trim();
  // The API collapses PDF line breaks when creating some excerpts.
  const pattern = needle.split(/\s+/).map(word => word.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')).join('\\s+');
  const match = pattern && new RegExp(pattern, 'u').exec(text);
  const highlight = match ? el('mark', {}, match[0]) : null;
  const copy = el('div', {class: 'page-text', role: 'region', 'aria-label': 'Текст страницы', tabindex: '0'},
    match ? [text.slice(0, match.index), highlight, text.slice(match.index + match[0].length)] : text);
  return {copy, highlight};
}
async function loadManual(page) {
  if (!viewer || page < 1) return;
  const active = viewer, seq = ++active.serial;
  const cite = active.cite;
  const initialFocus = document.activeElement?.id;
  const head = el('header', {class: 'top manual-top'}, iconButton('Вернуться к диалогу', 'back', () => manual.close(), {id: 'close-manual'}), el('strong', {}, 'Страница руководства'), state.demo ? el('span', {class: 'demo'}, 'ДЕМО') : null);
  const body = el('div', {class: 'manual-body'}, el('h2', {id: 'manual-heading'}, cite.title || cite.designation || 'Руководство'), hint(`Открываем страницу ${page}…`, {role: 'status'}));
  manual.replaceChildren(head, body);
  manual.scrollTop = 0;
  try {
    const meta = await json(manualPath(cite.manual_id, page));
    if (viewer !== active || seq !== active.serial) return;
    const quote = page === cite.page && cite.quote;
    const {copy, highlight} = pageText(meta.text || '', quote);
    const loading = el('p', {class: 'image-status', role: 'status'}, spinner(), 'Загружаем изображение страницы…');
    const image = el('img', {id: 'manual-image', alt: `${meta.title}, страница ${meta.page}`, hidden: true});
    const viewport = el('div', {class: 'page-frame'}, loading, image);
    const zoomOut = iconButton('Уменьшить', 'minus', () => changeZoom(-.5), {id: 'zoom-out', disabled: true});
    const zoomIn = iconButton('Увеличить', 'plus', () => changeZoom(.5), {id: 'zoom-in', disabled: true});
    image.addEventListener('load', () => { loading.remove(); image.hidden = false; zoomIn.disabled = false; });
    image.addEventListener('error', () => { loading.replaceWith(hint('Изображение не загрузилось.', {role: 'status'})); });
    let zoom = 1;
    const changeZoom = delta => {
      zoom = Math.max(1, Math.min(3, zoom + delta));
      image.style.width = `${zoom * 100}%`;
      zoomOut.disabled = zoom === 1;
      zoomIn.disabled = zoom === 3;
    };
    body.replaceChildren(...[el('div', {class: 'intro'}, el('h2', {id: 'manual-heading'}, meta.title || cite.title), hint(meta.designation || cite.designation || '')),
      el('div', {class: 'manual-controls'}, iconButton('Предыдущая страница', 'prev', () => loadManual(page - 1), {id: 'manual-prev', disabled: page <= 1}), el('strong', {class: 'mono', 'aria-live': 'polite'}, `Стр. ${meta.page} / ${meta.pages_total}`), iconButton('Следующая страница', 'next', () => loadManual(page + 1), {id: 'manual-next', disabled: page >= meta.pages_total}), el('span', {class: 'camera-gap'}), zoomOut, zoomIn),
      meta.text ? el('section', {class: 'box manual-text'}, el('h3', {}, 'Текст страницы'), copy) : null,
      quote && !highlight ? el('section', {class: 'box manual-text'}, el('h3', {}, 'Цитата из ответа'), el('blockquote', {}, `«${quote}»`)) : null,
      viewport,
    ].filter(Boolean));
    if (highlight) copy.scrollTop = highlight.getBoundingClientRect().top - copy.getBoundingClientRect().top - 7;
    image.src = `${manualPath(cite.manual_id, page)}.png`;
    const target = initialFocus && document.getElementById(initialFocus);
    (target && !target.disabled ? target : $('#close-manual')).focus({preventScroll: true});
  } catch (error) {
    if (viewer !== active || seq !== active.serial) return;
    body.replaceChildren(el('h2', {id: 'manual-heading'}, 'Страница недоступна'), hint(error.message, {role: 'alert'}), action('Повторить', () => loadManual(page)));
    $('#close-manual').focus();
  }
}

history.replaceState(state.route, '', location.pathname);
showRoute(state.route);
json(`${api}/health`).then(health => { if (health.mode === 'demo') { state.demo = true; header(); } }).catch(() => {});
