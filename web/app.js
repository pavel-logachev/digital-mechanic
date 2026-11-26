'use strict';

const $ = (selector, root = document) => root.querySelector(selector);
const main = $('#main'), dock = $('#dock'), topbar = $('#top'), manual = $('#manual');
const api = '/api';
const state = {route: {page: 'park'}, vehicles: null, fleet: null, cards: new Map(), sessions: new Map(), chats: new Map(), query: '', all: false, demo: false};
const {languages, text} = mechanicI18n;
const stored = (key, value) => {
  try { return value === undefined ? localStorage.getItem(key) : localStorage.setItem(key, value); }
  catch { return null; }
};
const savedLang = stored('mechanic:lang');
let lang = Object.hasOwn(languages, savedLang) ? savedLang : 'ru';
let large = stored('mechanic:large') === 'true';
const t = (key, vars) => text(lang, key, vars);
const displayText = value => String(value ?? '').replaceAll('\u2014', '–');
const fleetStages = {ok: ['normal', 'green', 'check'], attention: ['attention', 'amber', 'warn'], quarantine: ['quarantine', 'red', 'cross']};
const stages = {normal: fleetStages.ok, anomaly: ['anomaly', 'amber', 'warn'], check_failed: ['failed', 'red', 'cross']};
const priorities = ['low', 'medium', 'high'];
const priorityLabel = code => priorities.includes(code) ? t(code) : null;
const priorityStyles = {low: ['green', 'check'], medium: ['amber', 'warn'], high: ['red', 'warn']};
const qualities = {good: 'good', warning: 'noisy', bad: 'poor'};
const formatDate = options => new Intl.DateTimeFormat(lang, {timeZone: 'Europe/Moscow', ...options});
let moscow, moscowTime, shortDate, number;
function applySettings() {
  document.documentElement.lang = lang;
  document.documentElement.classList.toggle('large-type', large);
  document.title = t('brand');
  moscow = formatDate({day: '2-digit', month: '2-digit', year: '2-digit'});
  moscowTime = formatDate({hour: '2-digit', minute: '2-digit', hourCycle: 'h23'});
  shortDate = formatDate({day: '2-digit', month: '2-digit'});
  number = new Intl.NumberFormat(lang, {minimumFractionDigits: 2, maximumFractionDigits: 2});
}
applySettings();

const svgNS = 'http://www.w3.org/2000/svg';
const paths = {
  wave: 'M2 12h4l3-7 4 14 3-7h6', back: 'm14 6-6 6 6 6M8 12h13', next: 'm9 6 6 6-6 6', prev: 'm15 6-6 6 6 6',
  search: 'M15.5 15.5 21 21M17 11a6 6 0 1 1-12 0 6 6 0 0 1 12 0Z', truck: 'M6 18H3V6h12v12H9m6 0h3m3 0h1v-6l-3-4h-4m0 5h7M9 18a1.5 1.5 0 1 1-3 0 1.5 1.5 0 0 1 3 0Zm12 0a1.5 1.5 0 1 1-3 0 1.5 1.5 0 0 1 3 0Z',
  check: 'm5 12 4 4L19 6', cross: 'm8 8 8 8m0-8-8 8', warn: 'M12 8v5m0 3v.1M3 20l9-17 9 17Z',
  book: 'M4 4h11l4 4v12H4Zm10 0v5h5M8 12h7m-7 4h7', send: 'm3 3 18 9-18 9 4-9Zm4 9h14', chart: 'M4 4v16h16M7 15l4-5 4 2 5-6',
  mic: 'M9 6a3 3 0 0 1 6 0v5a3 3 0 0 1-6 0ZM5 11a7 7 0 0 0 14 0m-7 7v4m-4 0h8',
  stop: 'M5 5h14v14H5Z',
  clock: 'M12 7v5l3 2m6-2a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z', plus: 'M6 12h12m-6-6v12', minus: 'M6 12h12',
};

function el(tag, attrs = {}, ...children) {
  const node = document.createElement(tag);
  Object.entries(attrs).forEach(([key, value]) => {
    if (value == null || value === false) return;
    if (key.startsWith('on') && typeof value === 'function') node.addEventListener(key.slice(2), value);
    else node.setAttribute(key, value === true ? '' : ['aria-label', 'title', 'alt', 'placeholder'].includes(key) ? displayText(value) : value);
  });
  for (const child of children.flat(Infinity)) {
    if (child != null && child !== false) node.append(typeof child === 'string' ? displayText(child) : child);
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
const fromStage = ([key, ...style]) => pill(t(key), ...style);
const stagePill = status => fromStage(stages[status] ?? ['noCheck', '', 'clock']);
const fleetPill = status => fleetStages[status] ? fromStage(fleetStages[status]) : null;
const box = (...children) => el('section', {class: 'box'}, children);
const hint = (text, attrs = {}) => el('p', {class: 'muted', ...attrs}, text);
const mono = text => el('span', {class: 'mono'}, text);
const score = x => typeof x === 'number' && Number.isFinite(x) && x >= 0 && x <= 1;
const scoreText = x => score(x) ? number.format(x) : '–';
const stageOf = d => d?.verdict || d?.status;
const dateFor = (value, fmt) => {
  const date = new Date(value);
  return value && !isNaN(date) ? fmt ? fmt.format(date) : `${moscow.format(date)} ${moscowTime.format(date)}` : '–';
};
const endpoint = id => `${api}/vehicles/${encodeURIComponent(id)}`;
const manualPath = (id, page) => `${api}/manuals/${encodeURIComponent(id)}/pages/${page}`;
const jsonPost = body => ({method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(body)});

async function json(path, options) {
  const response = await fetch(path, options);
  const body = await response.json().catch(() => null);
  if (!response.ok || body == null) {
    const error = new Error(typeof body?.detail === 'string' ? body.detail : t('serviceError', {code: response.status}));
    error.status = response.status;
    throw error;
  }
  return body;
}
function header() {
  const {page, vid} = state.route;
  const isPark = page === 'park';
  let tools = $('#header-tools', topbar);
  if (!tools) {
    const select = el('select', {id: 'language', onchange: e => {
      lang = e.target.value;
      stored('mechanic:lang', lang);
      applySettings();
      header();
      if (main.hasAttribute('aria-busy') || !state.vehicles && state.route.page === 'park') return;
      const scroll = main.scrollTop;
      render();
      main.scrollTop = scroll;
    }}, Object.entries(languages).map(([code, name]) => el('option', {value: code, lang: code}, `${code.toUpperCase()} ${name}`)));
    const size = action(el('span', {'aria-hidden': 'true'}, 'Aa+'), () => {
      large = !large;
      stored('mechanic:large', String(large));
      applySettings();
      size.setAttribute('aria-pressed', String(large));
    }, {id: 'font-size'});
    tools = el('div', {id: 'header-tools'}, select, size);
    topbar.append(tools);
  }
  const picker = $('#language', tools), size = $('#font-size', tools);
  picker.value = lang;
  picker.setAttribute('aria-label', t('language'));
  size.setAttribute('aria-label', t('large'));
  size.setAttribute('title', t('large'));
  size.setAttribute('aria-pressed', String(large));
  const identity = el('div', {class: 'identity'}, isPark ? mark() : iconButton(t('back'), 'back', back),
    el('strong', {class: page === 'chat' ? 'brand mono' : 'brand'}, page === 'chat' ? vid : t(isPark ? 'brand' : page)),
    state.demo && el('span', {class: 'demo'}, t('demo')));
  if (topbar.firstElementChild === tools) topbar.prepend(identity);
  else topbar.firstElementChild.replaceWith(identity);
}

function navigate(route, replace = false) {
  history[replace ? 'replaceState' : 'pushState'](route, '', location.pathname);
  showRoute(route, true);
}
function back() { history.back(); }
window.addEventListener('popstate', e => showRoute(e.state?.page ? e.state : {page: 'park'}, true));
async function showRoute(route, focus = false) {
  if (state.route !== route) cancelRecording();
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
    main.replaceChildren(hint(t('loading'), {role: 'status'}));
    try { await load(); }
    catch (error) {
      if (state.route !== route) return;
      main.removeAttribute('aria-busy');
      main.replaceChildren(el('h1', {}, t('loadFailed')), hint(error instanceof TypeError ? t('network') : error.message, {role: 'alert'}), action(t('retry'), () => showRoute(route, true)));
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
const garage = v => v.garage_no ? t('garage', {no: v.garage_no}) : null;
const model = v => v.model || v.make;
const details = (label, ...body) => el('details', {class: 'fold'}, el('summary', {}, label), el('div', {class: 'fold-body'}, body));
function vehicleRow(v, fromFleet = false) {
  const s = v.last_check;
  return action(el('span', {class: 'row-copy'},
    el('strong', {class: 'plate mono'}, v.vehicle_id),
    el('span', {class: 'row-model'}, [garage(v), model(v)].filter(Boolean).join(' · ')),
    fromFleet || v.fleet_status === 'quarantine' || (s?.status === 'normal' && v.fleet_status === 'attention') ? fleetPill(v.fleet_status) : stagePill(s?.status),
    fromFleet && s?.anomaly_title && hint(s.anomaly_title),
  ), () => navigate({page: 'vehicle', vid: v.vehicle_id}), {class: 'vehicle-row'}, icon('next'));
}
function renderPark() {
  const list = el('div', {class: 'vehicle-list'});
  const count = el('span', {class: 'count', 'aria-live': 'polite'});
  const keyboardLabel = () => t(state.numeric ? 'textKeys' : 'numberKeys');
  const input = el('input', {id: 'vehicle-search', type: 'text', enterkeyhint: 'search', autocapitalize: 'characters', spellcheck: 'false', autocomplete: 'off', inputmode: state.numeric ? 'numeric' : 'search', placeholder: t('search'), 'aria-label': t('search'), oninput: e => { state.query = e.target.value; state.all = false; update(); }});
  const clear = iconButton(t('clear'), 'cross', () => { input.value = state.query = ''; state.all = false; update(); input.focus(); });
  const keyboard = action(keyboardLabel(), () => {
    state.numeric = !state.numeric;
    keyboard.textContent = keyboardLabel();
    input.blur();
    input.inputMode = state.numeric ? 'numeric' : 'search';
    input.focus();
  }, {id: 'search-keyboard'});
  const ordered = [...state.vehicles].sort((a, b) => (b.last_check?.checked_at || '').localeCompare(a.last_check?.checked_at || ''));
  const update = () => {
    const key = searchKey(state.query);
    const found = key ? ordered.filter(v => [v.vehicle_id, v.garage_no].some(x => searchKey(x).includes(key))) : ordered;
    const visible = state.all ? found : found.slice(0, 8);
    count.textContent = t('count', {found: found.length, total: ordered.length});
    clear.hidden = !state.query;
    list.replaceChildren(...visible.map(v => vehicleRow(v)));
    if (!found.length) list.append(box(el('strong', {}, t('noResults'))));
    if (visible.length < found.length) list.append(action(t('showAll', {count: found.length}), () => { state.all = true; update(); list.children[8]?.focus(); }));
  };
  input.value = state.query;
  update();
  main.replaceChildren(title(t('choose')), el('div', {class: 'search-group'}, el('div', {class: 'search'}, icon('search'), input, clear), keyboard),
    el('div', {class: 'between list-heading'}, el('h2', {}, t('vehicleList')), count), list,
    action([icon('chart'), t('fleet'), icon('next')], () => navigate({page: 'fleet'}), {class: 'wide-link'}));
}
function renderFleet() {
  const items = state.fleet.priority ?? [];
  main.replaceChildren(title(t('fleet')),
    el('div', {class: 'fleet-counts'}, Object.entries(fleetStages).map(([key, [label, tone, symbol]]) => el('div', {class: `fleet-count ${tone}`}, icon(symbol), el('strong', {class: 'mono'}, String(state.fleet.counts?.[key] ?? '–')), el('span', {}, t(label))))),
    el('h2', {}, t('fleetPriority')),
    items.length ? el('div', {class: 'vehicle-list'}, items.map(v => vehicleRow(v, true))) : box(hint(t('fleetEmpty'))));
}
function context(v, s, chat = false) {
  const label = chat ? garage(v) : v.vehicle_id;
  return el('div', {class: 'context'}, icon('truck'), el('div', {class: 'context-copy'},
    label && el('strong', {class: chat ? null : 'mono'}, label), model(v) && el('span', {}, model(v))),
    s?.checked_at && el('time', {class: 'mono', datetime: s.checked_at}, dateFor(s.checked_at, moscow), el('br'), dateFor(s.checked_at, moscowTime)));
}

function graph(sessions) {
  const recent = sessions.slice(-5);
  if (!recent.length) return null;
  const x = i => recent.length === 1 ? 168 : 40 + i * 254 / (recent.length - 1);
  const y = d => 58 - 42 * d;
  const desc = recent.map(s => `${dateFor(s.checked_at, shortDate)}: ${s.status === 'check_failed' ? t('failed') : score(s.anomaly_score) ? scoreText(s.anomaly_score) : t('noScore')}`).join('; ');
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
  return el('figure', {class: 'box trend'}, canvas, hint(t('trendNote')));
}
function renderVehicle(v) {
  const sessions = v.sessions ?? [];
  const latest = sessions.at(-1);
  const current = state.sessions.get(v.vehicle_id) ?? latest?.session_id;
  const chosen = sessions.find(s => s.session_id === current);
  const selection = el('div', {class: 'box selection'});
  const updateSelection = s => selection.replaceChildren(
    el('h2', {}, t(s === latest ? 'lastCheck' : 'check')),
    el('div', {class: 'between check-copy'}, el('time', {class: 'mono', datetime: s.checked_at}, dateFor(s.checked_at)), stagePill(s.status)),
  );
  if (chosen) updateSelection(chosen);
  const historyRows = [...sessions].reverse().map(s => el('label', {class: 'check-row'},
    el('input', {type: 'radio', name: 'check', value: s.session_id, checked: current === s.session_id, onchange: () => { state.sessions.set(v.vehicle_id, s.session_id); updateSelection(s); }}),
    el('span', {class: 'check-copy'}, el('time', {class: 'mono', datetime: s.checked_at}, dateFor(s.checked_at)), stagePill(s.status)),
  ));
  const tickets = [...(v.tickets ?? [])].reverse();
  main.replaceChildren(
    el('section', {class: 'box vehicle-head'}, title(v.vehicle_id),
      el('p', {class: 'vehicle-model'}, model(v)), garage(v) && hint(garage(v)), fleetPill(v.fleet_status),
      v.engine_model && hint(`${t('engine')}: ${v.engine_model}`)),
    chosen ? selection : box(hint(t('noChecks'))),
    sessions.length > 0 && details(t('checks'), el('fieldset', {class: 'history'}, el('legend', {class: 'visually-hidden'}, t('chooseCheck')), el('div', {class: 'checks'}, historyRows)), graph(sessions)),
    details(t('pastTickets'), tickets.length ? el('div', {class: 'tickets'}, tickets.map(ticket => el('div', {class: 'between'}, el('span', {}, el('strong', {class: 'mono'}, ticket.ticket_id), el('span', {class: 'muted ticket-meta'}, [ticket.anomaly_type, dateFor(ticket.created_at)].filter(Boolean).join(' · '))), priorityLabel(ticket.urgency) && pill(priorityLabel(ticket.urgency), ...priorityStyles[ticket.urgency])))) : hint(t('noTickets'))),
  );
  dock.replaceChildren(el('div', {class: 'dock'}, primary(t('diagnose'), () => {
    const sid = state.sessions.get(v.vehicle_id) ?? current;
    if (!sid) return;
    const conversation = conversationFor(v.vehicle_id, sid);
    navigate({page: 'chat', vid: v.vehicle_id, sid});
    if (!conversation.busy && !conversation.verdict) sendChat(conversation, 'diagnose');
  }, {id: 'diagnose', disabled: !sessions.length}, icon('next'))));
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
  return entries.length ? el('ul', {class: 'reasons'}, entries.map(line => el('li', {}, line))) : hint(t('noReasons'));
}
function warnings(values) {
  const entries = Array.isArray(values) ? values.filter(Boolean) : [];
  return entries.length ? el('section', {class: 'box warnings'}, icon('warn'), el('div', {}, el('h3', {}, t('important')), reasons(entries))) : null;
}
const metric = (label, value) => el('div', {class: 'metric'}, el('dt', {}, label), el('dd', {}, el('strong', {}, value ?? t('noData'))));
function verdict(d, id, opens) {
  const status = stageOf(d);
  const fail = status === 'check_failed', normal = status === 'normal';
  const incompatible = d.rule === 'R3-not-applicable';
  const vTitle = normal ? t('normalTitle') : fail ? t('failedTitle') : incompatible ? t('notApplicable') : d.anomaly_title ? t('hypothesis', {name: d.anomaly_title}) : t('anomalyTitle');
  const urgency = priorityLabel(d.urgency);
  const next = el('div', {class: 'next-action'}, el('h3', {}, t('next')), el('p', {}, d.action || t(fail ? 'nextFail' : normal ? 'nextNormal' : 'nextAnomaly')));
  const top = el('div', {class: `verdict-head ${stages[status][1]}`}, stagePill(status), el('h2', {}, vTitle), next,
    urgency && pill(`${t('priority')}: ${urgency}`, ...priorityStyles[d.urgency]));
  const metrics = !fail && el('dl', {class: 'metrics'}, metric(t('score'), score(d.anomaly_score) ? `${scoreText(d.anomaly_score)} / 1` : null), metric(t('confidence'), score(d.confidence) ? `${scoreText(d.confidence)} / 1` : null), metric(t('quality'), qualities[d.signal_quality] && t(qualities[d.signal_quality])));
  const key = `priority-${id}`;
  const hasReasons = Array.isArray(d.urgency_reasons) && d.urgency_reasons.length > 0;
  const why = (metrics || hasReasons) && el('details', {class: 'fold', open: opens.has(key), 'data-trace': key},
    el('summary', {}, t('metrics')), el('div', {class: 'fold-body'}, metrics, hasReasons && el('strong', {}, t(urgency ? 'whyPriority' : 'whyResult')), hasReasons && reasons(d.urgency_reasons)));
  return el('article', {class: `verdict ${status}`}, top, warnings(d.warnings), why);
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
          nodes.push(citationLink(cite, match[0], {class: 'citation-chip inline-cite', 'aria-label': t('source', {n, name: cite.designation || cite.title, page: cite.page})}));
        } else nodes.push(match[0]);
      }
      start = match.index + match[0].length;
    }
    nodes.push(value.slice(start));
    return nodes;
  };
  let paragraph = null, list = null;
  for (const line of displayText(text).split(/\r?\n/)) {
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
  const footer = references.length ? el('footer', {class: 'message-sources'}, el('strong', {}, t('sources')), el('ul', {}, references.map(([n, cite]) =>
    el('li', {}, citationLink(cite, [el('span', {class: 'citation-chip'}, `[${n}]`), el('span', {class: 'citation-excerpt'},
      el('strong', {}, t('pageRef', {name: cite.designation || cite.title, page: cite.page})), cite.quote && ` – «${cite.quote}»`)], {class: 'citation-row'}))))) : null;
  return [rendered, footer];
}
function trace(turn, open) {
  if (!turn.steps.length) return null;
  return el('details', {class: 'fold trace', open, 'data-trace': `steps-${turn.id}`}, el('summary', {}, t('steps')),
    el('ol', {class: 'fold-body'}, turn.steps.map(s => el('li', {}, el('div', {class: 'between'}, el('strong', {}, s.title),
      s.status === 'running' ? pill(t('working'), 'amber', 'clock') : s.status === 'error' ? pill(t('error'), 'red', 'cross') : pill(t('done'), 'green', 'check')), s.detail ? hint(s.detail) : null))));
}
function renderTurn(turn, latestResult, opens) {
  const block = el('section', {class: 'turn'});
  if (turn.question) block.append(el('div', {class: 'user-message'}, el('strong', {}, t('mechanic')), el('p', {}, turn.question)));
  const answers = turn.messages.map(m => el('article', {class: 'box agent-message'}, markdown(m.text, m.citations)));
  const log = trace(turn, opens.has(`steps-${turn.id}`));
  const diagnosisResponse = turn.diagnosis ? el('details', {class: 'fold', open: opens.has(`answer-${turn.id}`), 'data-trace': `answer-${turn.id}`}, el('summary', {}, t('answer')), el('div', {class: 'fold-body'}, answers)) : null;
  if (turn.diagnosis && !latestResult) {
    block.append(el('details', {class: 'fold previous', open: opens.has(`verdict-${turn.id}`), 'data-trace': `verdict-${turn.id}`}, el('summary', {}, t('result'), stagePill(stageOf(turn.diagnosis))), el('div', {class: 'fold-body'}, verdict(turn.diagnosis, turn.id, opens), answers.length > 0 && diagnosisResponse, log)));
  } else {
    if (turn.diagnosis) block.append(verdict(turn.diagnosis, turn.id, opens));
    if (answers.length) block.append(...(diagnosisResponse ? [diagnosisResponse] : answers));
    if (log) block.append(log);
  }
  for (const error of turn.errors) block.append(el('p', {class: 'notice red', role: 'alert'}, error));
  return block;
}
const spinner = () => el('span', {class: 'spinner', 'aria-hidden': 'true'});
const runningSteps = {
  get_diagnosis: 'stepDiagnose', get_vehicle_history: 'stepHistory', search_manual: 'stepSearch', search_manuals: 'stepSearch',
  read_page: 'stepRead', get_fault_reference: 'stepFault', prepare_ticket: 'stepDraft', draft_ticket: 'stepDraft',
};
function pendingText(turn) {
  const step = turn?.steps.at(-1);
  return t(step?.status === 'running' ? runningSteps[step.tool] ?? 'pending' : 'pending');
}

const canDraft = d => stageOf(d) === 'anomaly' && d.ticket_allowed !== false;
function updateChat(c, latestOnly = false, scrollTo = null) {
  if (!isCurrent(c)) return;
  const feed = $('#conversation');
  if (!feed) return;
  const turn = c.turns.at(-1);
  const result = c.turns.findLast(item => item.diagnosis);
  const opens = new Set([...feed.querySelectorAll('details[open]')].map(d => d.dataset.trace));
  if (latestOnly && turn && feed.lastElementChild) feed.lastElementChild.replaceWith(renderTurn(turn, turn === result, opens));
  else feed.replaceChildren(...c.turns.map(item => renderTurn(item, item === result && item === turn, opens)));
  const progress = $('#chat-progress');
  $('#chat-progress-row').hidden = !c.busy;
  const statusText = c.busy ? pendingText(turn) : '';
  if (progress.textContent !== statusText) progress.textContent = statusText;
  const controls = $('#chat-controls');
  const commands = [];
  if (c.receipt) commands.push(action(t('openReceipt'), () => navigate({page: 'receipt', vid: c.vid, sid: c.sid}), {class: 'full', disabled: c.busy}));
  else if (canDraft(c.verdict)) commands.push(action(t(c.draft ? 'openDraft' : 'createDraft'), () => {
    if (c.draft) navigate({page: 'draft', vid: c.vid, sid: c.sid});
    else sendChat(c, 'draft_ticket');
  }, {class: 'full', 'data-command': 'draft', disabled: c.busy}, icon('next')));
  else if (!c.busy && !c.verdict) commands.push(primary(t('diagnose'), () => sendChat(c, 'diagnose')));
  controls.replaceChildren(...commands);
  updateComposer(c);
  if (scrollTo) feed.lastElementChild?.querySelector(scrollTo)?.scrollIntoView({block: 'start'});
}
function renderChat(v, s, c) {
  main.replaceChildren(el('h1', {tabindex: '-1', class: 'visually-hidden'}, v.vehicle_id), context(v, s, true),
    el('div', {id: 'conversation', role: 'log', 'aria-label': t('chat'), 'aria-live': 'polite'}));
  const composer = el('form', {class: 'compose', onsubmit: e => { e.preventDefault(); ask(c, c.question); }},
    el('div', {class: 'question-row'}, el('textarea', {id: 'question', name: 'question', rows: '2', placeholder: t('question'), 'aria-label': t('question'), autocomplete: 'off', maxlength: '2000', oninput: e => { c.question = e.target.value; if (c.voiceNotice === 'micReady') c.voiceNotice = ''; updateComposer(c); }}),
      iconButton(t('mic'), 'mic', () => toggleRecording(c), {id: 'mic', 'aria-describedby': 'voice-status'})),
    el('div', {class: 'voice-status', id: 'voice-status', role: 'status'}, el('span', {id: 'voice-label'}), el('span', {id: 'mic-timer', class: 'mono', 'aria-hidden': 'true'})),
    el('button', {id: 'send-question', class: 'primary full', type: 'submit', 'aria-label': t('sendQuestion')}, t('send'), icon('send')),
  );
  dock.replaceChildren(el('div', {class: 'dock chat-dock'}, el('div', {class: 'chat-status', id: 'chat-progress-row', hidden: true}, spinner(), el('span', {id: 'chat-progress', role: 'status'})), el('div', {id: 'chat-controls'}), composer));
  $('#question').value = c.question;
  updateChat(c);
}
function ask(c, value) {
  const q = value.trim();
  if (!q || c.busy || recording?.c === c) return;
  c.question = '';
  c.voiceNotice = '';
  const input = $('#question');
  if (input) input.value = '';
  sendChat(c, null, q);
}

let recording;
const RECORD_MS = 60000;
function updateComposer(c) {
  if (!isCurrent(c) || !$('#mic')) return;
  const active = recording?.c === c ? recording : null;
  const running = active?.phase === 'recording';
  const mic = $('#mic'), label = running ? t('micStop') : `${t('micShort')}: ${t('mic')}`;
  mic.disabled = c.busy || Boolean(active && !running);
  mic.hidden = active?.phase === 'sending';
  mic.setAttribute('aria-pressed', String(Boolean(running)));
  if (mic.getAttribute('aria-label') !== label) {
    mic.setAttribute('aria-label', label);
    mic.title = label;
    mic.replaceChildren(icon(running ? 'stop' : 'mic'), el('span', {'aria-hidden': 'true'}, t(running ? 'micStop' : 'micShort')));
  }
  const input = $('#question'), send = $('#send-question');
  $('#chat-controls').hidden = Boolean(active) || c.busy;
  $('.compose').hidden = c.busy;
  input.hidden = send.hidden = Boolean(active);
  $('.question-row').classList.toggle('dictating', Boolean(active));
  input.disabled = c.busy || Boolean(active);
  send.disabled = c.busy || Boolean(active) || !c.question.trim();
  const voice = $('#voice-status');
  const notice = active ? {asking: 'micAsk', recording: 'micRecording', sending: 'micTranscribe'}[active.phase] : c.voiceNotice;
  voice.hidden = !notice;
  voice.classList.toggle('red', running || Boolean(notice && !active && notice !== 'micReady'));
  const message = $('#voice-label');
  if (message.textContent !== (notice ? t(notice) : '')) message.textContent = notice ? t(notice) : '';
  const timer = $('#mic-timer');
  timer.hidden = !running;
  if (running) {
    const elapsed = Math.min(60, Math.floor((performance.now() - active.start) / 1000));
    timer.textContent = `${Math.floor(elapsed / 60)}:${String(elapsed % 60).padStart(2, '0')}`;
  }
}
function releaseRecording(active) {
  clearInterval(active.tick);
  clearTimeout(active.limit);
  active.stream?.getTracks().forEach(track => track.stop());
}
function cancelRecording() {
  if (!recording) return;
  const active = recording;
  recording = null;
  active.abort.abort();
  if (active.recorder?.state === 'recording') active.recorder.stop();
  releaseRecording(active);
}
window.addEventListener('pagehide', () => {
  const c = recording?.c;
  cancelRecording();
  if (c) updateComposer(c);
});
function endRecording(active, notice) {
  if (recording !== active) return;
  recording = null;
  releaseRecording(active);
  active.c.voiceNotice = notice;
  updateComposer(active.c);
}
function stopRecording(active) {
  if (recording !== active || active.phase !== 'recording') return;
  active.phase = 'sending';
  clearInterval(active.tick);
  clearTimeout(active.limit);
  updateComposer(active.c);
  if (active.recorder.state === 'recording') active.recorder.stop();
}
async function uploadRecording(active) {
  releaseRecording(active);
  if (recording !== active) return;
  const type = active.recorder.mimeType || active.parts[0]?.type || '';
  const ext = {'audio/webm': 'webm', 'audio/ogg': 'ogg', 'audio/mp4': 'mp4', 'audio/wav': 'wav', 'video/mp4': 'mp4', 'video/webm': 'webm'}[type.split(';')[0]];
  const audio = new Blob(active.parts, {type});
  if (!audio.size) return endRecording(active, 'micEmpty');
  if (!ext) return endRecording(active, 'micFailed');
  const form = new FormData();
  form.append('audio', audio, `question.${ext}`);
  form.append('lang', active.lang);
  const deadline = setTimeout(() => active.abort.abort(), 45000);
  try {
    const result = await json(`${api}/transcribe`, {method: 'POST', body: form, signal: active.abort.signal});
    if (recording !== active) return;
    const transcript = typeof result.text === 'string' ? displayText(result.text).trim() : '';
    if (!transcript) return endRecording(active, 'micEmpty');
    const c = active.c;
    c.question = transcript.slice(0, 2000);
    if (isCurrent(c)) $('#question').value = c.question;
    endRecording(active, 'micReady');
  } catch {
    endRecording(active, 'micService');
  } finally {
    clearTimeout(deadline);
  }
}
async function toggleRecording(c) {
  if (recording?.c === c) { stopRecording(recording); return; }
  if (recording || c.busy) return;
  c.voiceNotice = '';
  if (!window.isSecureContext || !navigator.mediaDevices?.getUserMedia || typeof MediaRecorder !== 'function') {
    c.voiceNotice = window.isSecureContext ? 'micUnsupported' : 'micSecure';
    updateComposer(c);
    return;
  }
  const active = {c, lang, phase: 'asking', parts: [], abort: new AbortController()};
  recording = active;
  updateComposer(c);
  try {
    active.stream = await navigator.mediaDevices.getUserMedia({audio: true});
    if (recording !== active || !isCurrent(c)) { releaseRecording(active); return; }
    const mimeType = ['audio/webm;codecs=opus', 'audio/mp4', 'audio/ogg;codecs=opus', 'audio/webm', 'audio/ogg']
      .find(type => MediaRecorder.isTypeSupported?.(type));
    active.recorder = new MediaRecorder(active.stream, mimeType ? {mimeType} : undefined);
    active.recorder.addEventListener('dataavailable', event => { if (event.data.size) active.parts.push(event.data); });
    active.recorder.addEventListener('stop', () => uploadRecording(active), {once: true});
    active.recorder.addEventListener('error', () => endRecording(active, 'micFailed'), {once: true});
    active.recorder.start();
    active.phase = 'recording';
    active.start = performance.now();
    active.tick = setInterval(() => updateComposer(c), 200);
    active.limit = setTimeout(() => stopRecording(active), RECORD_MS);
    updateComposer(c);
    $('#mic')?.focus({preventScroll: true});
  } catch (error) {
    endRecording(active, ['NotAllowedError', 'SecurityError'].includes(error.name) ? 'micDenied' : error.name === 'NotFoundError' ? 'micMissing' : 'micFailed');
  }
}

// Accept all SSE line endings and events split mid-character or mid-line.
async function readEvents(response, visit) {
  if (!response.body || !response.headers.get('content-type')?.includes('text/event-stream')) throw new Error(t('streamMissing'));
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
  if (c.busy || recording?.c === c || (mode === 'draft_ticket' && !canDraft(c.verdict))) return;
  c.busy = true;
  const turn = {id: c.turns.length + 1, question, pending: true, steps: [], messages: [], errors: []};
  c.turns.push(turn);
  updateChat(c, false, question ? '.user-message' : null);
  if (mode === 'diagnose' && isCurrent(c)) main.scrollTop = 0;
  let done = false;
  try {
    const res = await fetch(`${api}/chat`, jsonPost({conversation_id: c.id, vehicle_id: c.vid, session_id: c.sid, message: question, action: mode, lang}));
    if (!res.ok) {
      const body = await res.json().catch(() => null);
      throw new Error(typeof body?.detail === 'string' ? body.detail : t('serviceError', {code: res.status}));
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
        c.edits = {conclusion: displayText(c.draft.conclusion), urgency: c.draft.urgency || '', operations: displayText((c.draft.operations || []).join('\n')), spare_parts: displayText((c.draft.spare_parts || []).join('\n'))};
      } else if (event.type === 'error') turn.errors.push(event.text || t('chatError'));
      else if (event.type === 'done') { done = true; return; }
      else return;
      updateChat(c, true, event.type === 'message' && mode !== 'diagnose' ? '.agent-message' : null);
    });
    if (!done) throw new Error(t('streamCut'));
    if (!turn.errors.length && mode === 'diagnose' && !turn.diagnosis) throw new Error(t('noDiagnosis'));
    if (!turn.errors.length && mode === 'draft_ticket' && !turn.draft) throw new Error(t('noDraft'));
  } catch (error) {
    turn.errors.push(error instanceof TypeError ? t('network') : error.message);
  } finally {
    c.busy = false;
    turn.pending = false;
    updateChat(c, true, turn.errors.length ? '.notice' : null);
    if (turn.draft && isCurrent(c) && !turn.errors.length) navigate({page: 'draft', vid: c.vid, sid: c.sid});
  }
}

function field(c, name, label, rows, placeholder = '') {
  const input = el('textarea', {name, rows, placeholder, required: name === 'conclusion', oninput: e => { c.edits[name] = e.target.value; }});
  input.value = displayText(c.edits[name]);
  return el('label', {class: 'field'}, el('span', {}, label), input);
}
function renderDraft(v, s, c) {
  if (c.receipt) { renderReceipt(v, s, c); return; }
  if (!c.draft) { main.replaceChildren(title(t('noDraft')), action(t('back'), back)); return; }
  const d = c.draft;
  const override = el('input', {name: 'urgency_reason', maxlength: '350', value: c.edits.urgencyReason || '', oninput: e => { c.edits.urgencyReason = e.target.value; }});
  const overrideField = el('label', {class: 'field'}, el('span', {}, t('priorityReason')), override);
  const syncOverride = () => { overrideField.hidden = !urgency.value || urgency.value === d.urgency; override.required = !overrideField.hidden; };
  const urgency = el('select', {name: 'urgency', required: true, onchange: e => { c.edits.urgency = e.target.value; syncOverride(); }}, [el('option', {value: '', disabled: true}, t('choosePriority')), ...priorities.map(key => el('option', {value: key}, priorityLabel(key)))]);
  urgency.value = c.edits.urgency;
  syncOverride();
  const references = (d.references ?? []).filter(r => r.manual_id && Number.isInteger(r.pdf_page) && r.pdf_page > 0);
  const form = el('form', {class: 'stack', id: 'draft-form', onsubmit: e => { e.preventDefault(); confirmTicket(c); }},
    el('section', {class: 'box stack'}, d.anomaly_type || c.verdict?.anomaly_title ? el('p', {class: 'muted'}, `${t('faultType')}: `, el('strong', {}, [d.anomaly_type, c.verdict?.anomaly_title].filter(Boolean).join(' – '))) : null, field(c, 'conclusion', t('conclusion'), 2)),
    el('section', {class: 'box stack'}, el('label', {class: 'field'}, el('span', {}, t('priority')), urgency), overrideField,
      details(t('whyPriority'), reasons(d.urgency_reasons))),
    el('section', {class: 'box stack'}, field(c, 'operations', t('work'), 2, t('newLine')), field(c, 'spare_parts', t('parts'), 1, t('newLine'))),
    references.length ? el('section', {class: 'box stack'}, el('h2', {}, t('sources')), references.map(r => citationLink({manual_id: r.manual_id, title: r.title || r.manual, page: r.pdf_page}, [icon('book'), t('pageRef', {name: r.title || r.manual, page: r.pdf_page}), icon('next')], {class: 'source-link'}))) : null,
    el('p', {id: 'ticket-error', role: 'alert', class: 'notice red', hidden: !c.confirmError}, c.confirmError || ''),
  );
  const warning = warnings(d.warnings);
  main.replaceChildren(context(v, s), el('div', {class: 'intro'}, pill(t('unsent'), 'amber', 'clock'), title(t('draft'))), ...(warning ? [warning] : []), form);
  dock.replaceChildren(el('div', {class: 'dock'}, el('button', {id: 'confirm-ticket', class: 'primary full', type: 'submit', form: 'draft-form', disabled: c.confirming || c.confirmUncertain}, c.confirming ? t('sending') : t('confirm'), icon('check')), hint(t('confirmNote'))));
}
async function confirmTicket(c) {
  if (c.confirming || c.confirmUncertain || c.receipt) return;
  const lines = value => value.split(/\r?\n/).map(line => line.trim()).filter(Boolean);
  const conclusion = c.edits.conclusion.trim();
  const override = c.edits.urgency !== c.draft.urgency ? (c.edits.urgencyReason || '').trim() : '';
  const payload = {draft_id: c.draft.draft_id, conclusion: override ? `${conclusion}\n${t('reasonLine', {reason: override})}` : conclusion, urgency: c.edits.urgency, operations: lines(c.edits.operations), spare_parts: lines(c.edits.spare_parts)};
  const invalid = !conclusion ? t('needConclusion') : c.edits.urgency !== c.draft.urgency && !override ? t('needReason') : '';
  if (invalid) { $('#ticket-error').hidden = false; $('#ticket-error').textContent = invalid; return; }
  c.confirming = true;
  c.confirmError = '';
  const button = $('#confirm-ticket');
  button.disabled = true;
  button.textContent = t('sending');
  $('#ticket-error').hidden = true;
  try {
    const data = await json(`${api}/tickets/confirm`, jsonPost(payload));
    if (data.status !== 'created' || !data.ticket_id) throw new Error(t('noTicketId'));
    c.receipt = {id: data.ticket_id, payload};
    state.vehicles = null;
    if (isCurrent(c, 'draft')) navigate({page: 'receipt', vid: c.vid, sid: c.sid}, true);
    try {
      const updated = await json(endpoint(c.vid));
      state.cards.set(c.vid, updated);
    } catch { state.cards.delete(c.vid); }
  } catch (error) {
    c.confirmUncertain = !error.status || error.status >= 500;
    c.confirmError = c.confirmUncertain ? t('confirmUncertain') : error.message;
  } finally {
    c.confirming = false;
    if (isCurrent(c, 'draft')) render();
  }
}
function renderReceipt(v, s, c) {
  if (!c.receipt) { main.replaceChildren(title(t('noReceipt')), action(t('back'), back)); return; }
  const result = c.receipt;
  const fields = [[t('machine'), [v.vehicle_id, v.garage_no].filter(Boolean).join(' / ')], [t('check'), dateFor(s?.checked_at)], [t('conclusion'), result.payload.conclusion], [t('priority'), priorityLabel(result.payload.urgency)]];
  main.replaceChildren(el('section', {class: 'receipt green'}, pill(t('accepted'), 'green', 'check'), title(t('receipt')), el('strong', {class: 'receipt-id mono'}, result.id)), el('section', {class: 'box stack'}, el('h2', {}, t('sentDetails')), el('dl', {class: 'receipt-fields'}, fields.map(([label, value]) => el('div', {}, el('dt', {}, label), el('dd', {}, value))))));
  dock.replaceChildren(el('div', {class: 'dock'}, primary(t('backPark'), () => navigate({page: 'park'}))));
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
  const copy = el('div', {class: 'page-text'}, match ? [text.slice(0, match.index), highlight, text.slice(match.index + match[0].length)] : text);
  return {copy, found: Boolean(match)};
}
async function loadManual(page) {
  if (!viewer || page < 1) return;
  const active = viewer, seq = ++active.serial;
  const cite = active.cite;
  const initialFocus = document.activeElement?.id;
  const head = el('header', {class: 'top manual-top'}, iconButton(t('closeManual'), 'back', () => manual.close(), {id: 'close-manual'}), el('strong', {}, t('manual')), state.demo ? el('span', {class: 'demo'}, t('demo')) : null);
  const body = el('div', {class: 'manual-body'}, el('h2', {id: 'manual-heading'}, cite.title || cite.designation || t('manual')), hint(t('openPage', {page}), {role: 'status'}));
  manual.replaceChildren(head, body);
  manual.scrollTop = 0;
  try {
    const meta = await json(manualPath(cite.manual_id, page));
    if (viewer !== active || seq !== active.serial) return;
    const quote = page === cite.page && cite.quote;
    const {copy, found} = pageText(meta.text || '', quote);
    const loading = el('p', {class: 'image-status', role: 'status'}, spinner(), t('imageLoading'));
    const image = el('img', {id: 'manual-image', alt: t('pageRef', {name: meta.title, page: meta.page}), hidden: true});
    const viewport = el('div', {class: 'page-frame'}, loading, image);
    const zoomOut = iconButton(t('zoomOut'), 'minus', () => changeZoom(-.5), {id: 'zoom-out', disabled: true});
    const zoomIn = iconButton(t('zoomIn'), 'plus', () => changeZoom(.5), {id: 'zoom-in', disabled: true});
    image.addEventListener('load', () => { loading.remove(); image.hidden = false; zoomIn.disabled = false; });
    image.addEventListener('error', () => { loading.replaceWith(hint(t('imageFailed'), {role: 'status'})); });
    let zoom = 1;
    const changeZoom = delta => {
      zoom = Math.max(1, Math.min(3, zoom + delta));
      image.style.width = `${zoom * 100}%`;
      zoomOut.disabled = zoom === 1;
      zoomIn.disabled = zoom === 3;
    };
    body.replaceChildren(...[el('div', {class: 'intro'}, el('h2', {id: 'manual-heading'}, meta.title || cite.title), hint(meta.designation || cite.designation || '')),
      el('div', {class: 'manual-controls'}, iconButton(t('prevPage'), 'prev', () => loadManual(page - 1), {id: 'manual-prev', disabled: page <= 1}), el('strong', {class: 'mono', 'aria-live': 'polite'}, t('pageNumber', {page: meta.page, total: meta.pages_total})), iconButton(t('nextPage'), 'next', () => loadManual(page + 1), {id: 'manual-next', disabled: page >= meta.pages_total}), el('span', {class: 'camera-gap'}), zoomOut, zoomIn),
      quote ? el('section', {class: 'box manual-text'}, el('h3', {}, t('quote')), el('blockquote', {class: found ? 'matched-quote' : null}, `«${quote}»`)) : null,
      meta.text ? details(t('pageText'), copy) : null,
      viewport,
    ].filter(Boolean));
    image.src = `${manualPath(cite.manual_id, page)}.png`;
    const target = initialFocus && document.getElementById(initialFocus);
    (target && !target.disabled ? target : $('#close-manual')).focus({preventScroll: true});
  } catch (error) {
    if (viewer !== active || seq !== active.serial) return;
    body.replaceChildren(el('h2', {id: 'manual-heading'}, t('pageUnavailable')), hint(error instanceof TypeError ? t('network') : error.message, {role: 'alert'}), action(t('retry'), () => loadManual(page)));
    $('#close-manual').focus();
  }
}

history.replaceState(state.route, '', location.pathname);
showRoute(state.route);
json(`${api}/health`).then(health => { if (health.mode === 'demo') { state.demo = true; header(); } }).catch(() => {});
