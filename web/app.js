'use strict';

// пустые части интерфейса (null, false) не должны попадать на экран текстом «null» / «false»
for (const method of ['replaceChildren', 'append']) {
  const native = Element.prototype[method];
  Element.prototype[method] = function (...nodes) { return native.apply(this, nodes.flat(Infinity).filter(n => n != null && n !== false)); };
}
const $ = (selector, root = document) => root.querySelector(selector);
const $$ = (selector, root = document) => [...root.querySelectorAll(selector)];
const main = $('#main'), dock = $('#dock'), topbar = $('#top'), manual = $('#manual'), languageDialog = $('#language-dialog'), dataDialog = $('#data-dialog');
const api = '/api';
const state = {route: {page: 'park'}, vehicles: null, fleetFilter: '', cards: new Map(), chats: new Map(), query: '', all: false, demo: false};
const {languages, text} = mechanicI18n;
const stored = (key, value) => {
  try { return value === undefined ? localStorage.getItem(key) : localStorage.setItem(key, value); }
  catch { return null; }
};
const savedLang = stored('mechanic:lang');
let lang = Object.hasOwn(languages, savedLang) ? savedLang : 'ru';
let large = stored('mechanic:large') === 'true';
let detail = stored('mechanic:detail') === 'detailed' ? 'detailed' : 'brief';
let voiceConsent = stored('mechanic:voice-consent') === 'true';
const t = (key, vars) => text(lang, key, vars);
// редакционная норма: короткое тире вместо длинного, в русском интерфейсе без «ё»
const displayText = value => { const text = String(value ?? '').replaceAll('\u2014', '–'); return lang === 'ru' ? text.replaceAll('ё', 'е').replaceAll('Ё', 'Е') : text; };
const stages = {
  quarantine: ['quarantine', 'red', 'ban'], anomaly: ['anomaly', 'amber', 'warn'],
  check_failed: ['failed', 'violet', 'mic'], normal: ['normal', 'green', 'check'],
  unknown: ['noCheck', 'neutral', 'clock'],
};
const priorities = ['low', 'medium', 'high'];
const priorityLabel = code => priorities.includes(code) ? t(code) : null;
const priorityLine = code => t('priorityLine', {level: priorityLabel(code)?.toLocaleLowerCase(lang)});
const lowerStart = value => lang === 'ru' && value ? value[0].toLocaleLowerCase(lang) + value.slice(1) : value;
const qualities = {good: 'good', warning: 'noisy', bad: 'poor'};
// в браузере может не быть названий месяцев для узбекского, таджикского и т. п. – тогда дата цифрами: 19.11.2026, 17:50
const formatDate = options => {
  if (Intl.DateTimeFormat.supportedLocalesOf(lang).length) return new Intl.DateTimeFormat(lang, {timeZone: 'Europe/Moscow', ...options});
  const numeric = {...options}; if (numeric.month) numeric.month = '2-digit'; if (numeric.day) numeric.day = '2-digit';
  return new Intl.DateTimeFormat('ru-RU', {timeZone: 'Europe/Moscow', ...numeric});
};
let moscow, ruDay, ruTime, number;
let routeSerial = 0;
const routeScroll = new Map();
function applySettings() {
  document.documentElement.lang = lang;
  document.documentElement.classList.toggle('large-type', large);
  document.title = t('brand');
  moscow = formatDate({day: 'numeric', month: 'long', year: 'numeric', hour: '2-digit', minute: '2-digit', hourCycle: 'h23'});
  ruDay = formatDate({day: 'numeric', month: 'long', year: 'numeric'});
  ruTime = formatDate({hour: '2-digit', minute: '2-digit', hourCycle: 'h23'});
  number = new Intl.NumberFormat(lang, {minimumFractionDigits: 2, maximumFractionDigits: 2});
}
applySettings();

const svgNS = 'http://www.w3.org/2000/svg';
const paths = {
  wave: 'M2 12h4l3-7 4 14 3-7h6', back: 'm14 6-6 6 6 6M8 12h13', next: 'm9 6 6 6-6 6', down: 'm6 9 6 6 6-6', prev: 'm15 6-6 6 6 6',
  search: 'M15.5 15.5 21 21M17 11a6 6 0 1 1-12 0 6 6 0 0 1 12 0Z', truck: 'M6 18H3V6h12v12H9m6 0h3m3 0h1v-6l-3-4h-4m0 5h7M9 18a1.5 1.5 0 1 1-3 0 1.5 1.5 0 0 1 3 0Zm12 0a1.5 1.5 0 1 1-3 0 1.5 1.5 0 0 1 3 0Z',
  check: 'm5 12 4 4L19 6', cross: 'm8 8 8 8m0-8-8 8', warn: 'M12 8v5m0 3v.1M3 20l9-17 9 17Z',
  book: 'M4 4h11l4 4v12H4Zm10 0v5h5M8 12h7m-7 4h7', send: 'm3 3 18 9-18 9 4-9Zm4 9h14', chart: 'M4 4v16h16M7 15l4-5 4 2 5-6',
  mic: 'M9 6a3 3 0 0 1 6 0v5a3 3 0 0 1-6 0ZM5 11a7 7 0 0 0 14 0m-7 7v4m-4 0h8',
  stop: 'M5 5h14v14H5Z', ban: 'M12 3a9 9 0 1 1 0 18 9 9 0 0 1 0-18ZM5.6 5.6l12.8 12.8', globe: 'M2 12h20M12 2a10 10 0 1 1 0 20 10 10 0 1 1 0-20Zm0 0c5 5 5 15 0 20-5-5-5-15 0-20Z',
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
const stagePill = status => fromStage(stages[status] ?? stages.unknown);
const box = (...children) => el('section', {class: 'box'}, children);
const hint = (text, attrs = {}) => el('p', {class: 'muted', ...attrs}, text);
const checkRow = (id, label, attrs) => el('label', {class: 'check-label', for: id},
  el('input', {type: 'checkbox', id, ...attrs}), el('span', {}, label));
const score = x => typeof x === 'number' && Number.isFinite(x) && x >= 0 && x <= 1;
const scoreText = x => score(x) ? number.format(x) : '–';
const stageOf = d => d?.verdict || d?.status;
function vehicleStage(v, s = v.last_check, latest = s === v.last_check) {
  const stage = stageOf(s);
  // красный «Дефектовка до рейса» – любой высокий приоритет (#102: дефектовка до выпуска), чтобы заголовок не спорил с «Что делать»
  const critical = x => x?.severity === 'C' || x?.rule === 'R4-critical' || x?.urgency === 'high';
  if (critical(s) || s?.fleet_status === 'quarantine' || stage === 'quarantine' || (latest && (v.fleet_status === 'quarantine' || v.last_severity === 'C' || v.last_urgency === 'high'))) return 'quarantine';
  if (stage === 'check_failed') return stage;
  if (stage === 'anomaly' || (latest && stage === 'normal' && v.fleet_status === 'attention')) return 'anomaly';
  return stage === 'normal' ? stage : 'unknown';
}
const dateFor = value => {
  const date = new Date(value);
  if (!value || Number.isNaN(+date)) return '–';
  if (lang === 'ru') return `${ruDay.format(date).replace(/\s+г\.$/u, '')}, ${ruTime.format(date)}`;
  return moscow.format(date);
};
const checkTime = value => el('time', {datetime: value}, dateFor(value));
const shortDate = value => {
  const date = new Date(value);
  return Number.isNaN(+date) ? '–' : new Intl.DateTimeFormat('ru-RU', {day: '2-digit', month: '2-digit', timeZone: 'Europe/Moscow'}).format(date);
};
// B2: столбики оценки отклонения по последним проверкам – HTML, а не SVG, чтобы подписи росли вместе с крупным шрифтом
function scoreChart(v, sessions) {
  const points = [...sessions].sort((a, b) => (Date.parse(a.checked_at) || 0) - (Date.parse(b.checked_at) || 0)).slice(-5);
  if (points.length < 2) return null;
  const bars = points.map((s, i) => {
    const stage = vehicleStage(v, s, i === points.length - 1);
    const value = score(s.anomaly_score) ? s.anomaly_score : null;
    const tone = stages[stage]?.[1] || 'neutral';
    return el('div', {class: 'bar-col', 'data-bar': s.session_id},
      el('span', {class: 'bar-track'},
        el('span', {class: 'bar-value'}, value === null ? t('noScore') : scoreText(value)),
        el('span', {class: `bar ${tone}`, style: `height:calc(${value === null ? 0 : Math.max(.03, value).toFixed(2)} * (100% - 1.6em - 4px))`})),
    );
  });
  const dates = el('div', {class: 'bar-dates', 'aria-hidden': 'true'}, points.map(s => el('span', {class: 'bar-date'}, shortDate(s.checked_at))));
  return el('section', {class: 'box score-chart'}, el('h2', {}, t('scoreChart')),
    el('div', {class: 'bars', role: 'img', 'aria-label': points.map(s => `${shortDate(s.checked_at)}: ${score(s.anomaly_score) ? scoreText(s.anomaly_score) : t('noScore')}`).join('; ')}, bars), dates,
    hint(t('scoreScale')));
}
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
function openLanguage() {
  languageDialog.replaceChildren(
    el('div', {class: 'sheet-head'}, el('h2', {id: 'language-heading'}, t('language')),
      iconButton(t('close'), 'cross', () => languageDialog.close())),
    el('div', {class: 'language-list'}, Object.entries(languages).map(([code, name]) =>
      action([el('span', {class: 'language-code', 'aria-hidden': 'true'}, code.toUpperCase()), name, code === lang && icon('check')], () => {
        languageDialog.close();
        if (lang === code) return;
        lang = code;
        stored('mechanic:lang', lang);
        applySettings();
        header();
        if (main.hasAttribute('aria-busy')) { main.replaceChildren(hint(t('loading'), {role: 'status'})); return; }
        if (state.loadFailed) { showRoute(state.route); return; }
        const scroll = main.scrollTop;
        render();
        main.scrollTop = scroll;
      }, {lang: code, 'data-lang': code, 'aria-pressed': String(lang === code), autofocus: lang === code}))),
  );
  languageDialog.showModal();
}
function openDataDialog(c) {
  const close = () => dataDialog.close();
  const heading = el('h2', {id: 'data-heading'}, t(c ? 'voiceConsentTitle' : 'dataPolicy'));
  if (c) {
    const proceed = primary(t('continueConsent'), () => {
      if (!$('#voice-consent', dataDialog).checked || !isComposerCurrent(c)) { close(); return; }
      voiceConsent = true;
      stored('mechanic:voice-consent', 'true');
      close();
      toggleRecording(c);
    }, {disabled: true});
    dataDialog.replaceChildren(el('div', {class: 'sheet-head'}, heading),
      hint(t('voiceConsentText')),
      checkRow('voice-consent', t('voiceConsentCheck'), {onchange: e => { proceed.disabled = !e.target.checked; }}),
      el('div', {class: 'data-actions'}, action(t('cancelConsent'), close), proceed));
  } else {
    const sections = ['dataWhat', 'dataWhy', 'dataWhere', 'dataAudio', 'dataModels', 'dataDemo'];
    dataDialog.replaceChildren(el('div', {class: 'sheet-head'}, heading, iconButton(t('close'), 'cross', close)),
      el('ul', {class: 'reasons'}, sections.map(key => el('li', {}, t(key)))));
  }
  dataDialog.showModal();
  dataDialog.scrollTop = 0;
}
// Вводная инструкция для механика: сама при первом запуске, потом – кнопкой «?» на главном экране.
// Картинки шагов собраны из настоящих элементов интерфейса (неактивных), чтобы механик узнал их на экране.
const guide = $('#guide');
const replica = (label, cls = 'primary', symbol = null) => el('span', {class: `replica ${cls}`}, symbol && icon(symbol), label);
// stacked – широкая кнопка над пояснением, чтобы на узком экране текст не вылезал за край
const guideRow = (control, text, stacked = false) => el('li', {class: stacked ? 'stacked' : null},
  el('span', {class: 'guide-step'}, el('span', {class: 'guide-control'}, control), el('span', {}, text)));
const sampleSearch = () => el('span', {class: 'replica search-replica'}, icon('search'), el('span', {}, 'Т792'));
const sampleCar = () => el('span', {class: 'sample-car'}, plate('T792HO98'), el('span', {class: 'row-model'}, el('strong', {class: 'garage'}, 'Г-112'), el('span', {}, 'Урал‑5557‑10')), stagePill('quarantine'));
const guideSteps = [
  () => el('ul', {class: 'guide-points'}, ['guide1a', 'guide1b', 'guide1c'].map(key => el('li', {}, icon('check'), el('span', {}, t(key))))),
  () => el('div', {class: 'guide-stack'}, sampleSearch(), el('p', {class: 'guide-caption'}, t('guideLabels')), el('ul', {class: 'guide-legend'}, [['quarantine', 'guideRed'], ['anomaly', 'guideAmber'], ['check_failed', 'guideViolet'], ['normal', 'guideGreen']]
    .map(([stage, key]) => el('li', {}, stagePill(stage), el('span', {}, t(key)))))),
  () => el('div', {class: 'guide-stack'}, sampleCar(), replica(t('diagnose'))),
  () => el('ol', {class: 'guide-flow'}, guideRow(replica(null, 'mic', 'mic'), t('guide4a'), true), guideRow(replica(t('micStop'), 'stop', 'stop'), t('guide4b'), true),
    guideRow(replica(t('send')), t('guide4c'), true)),
  () => el('ol', {class: 'guide-flow wide'}, guideRow(replica(t('createDraft'), 'plain', 'next'), t('guide5a'), true), guideRow(replica(t('confirm'), 'primary', 'send'), t('guide5b'), true)),
  () => el('div', {class: 'guide-stack'}, el('ul', {class: 'guide-tools'}, [[[icon('globe'), 'RU'], 'language'], ['Aᴀ', 'large']]
    .map(([face, key]) => el('li', {}, el('span', {class: 'replica top-replica'}, face), el('span', {}, t(key))))),
    el('span', {class: 'replica help-replica'}, el('span', {class: 'help-mark'}, '?'), t('help'))),
];
function openGuide(step = 0) {
  const total = guideSteps.length;
  const show = n => {
    step = n;
    const last = step === total - 1;
    const next = primary([t(last ? 'guideDone' : 'guideNext'), last ? null : icon('next')], () => last ? closeGuide() : show(step + 1), {id: 'guide-next'});
    guide.replaceChildren(
      el('div', {class: 'guide-head'}, el('span', {class: 'guide-count', 'aria-live': 'polite'}, t('guideStep', {n: step + 1, total})),
        last ? null : action(t('guideSkip'), closeGuide, {class: 'link-button', id: 'guide-skip'})),
      el('div', {class: 'guide-body'}, el('h2', {id: 'guide-heading'}, t(`guide${step + 1}Title`)),
        el('div', {class: 'guide-visual', 'aria-hidden': 'true', inert: true}, guideSteps[step]()),
        el('p', {class: 'guide-text', id: 'guide-text'}, t(`guide${step + 1}Text`)),
        // крупный шрифт – сразу на первом шаге, а не только в конце инструкции
        step === 0 ? action([el('span', {class: 'size-face', 'aria-hidden': 'true'}, 'Aᴀ'), t(large ? 'guideSmaller' : 'guideBigger')],
          () => { toggleLarge(); show(0); $('#guide-size', guide).focus(); }, {id: 'guide-size', 'aria-pressed': String(large)}) : null,
        last ? detailChoice(() => { $('#detail-hint', guide).textContent = t(detail === 'detailed' ? 'detailedHint' : 'briefHint'); }) : null),
      el('div', {class: 'guide-dots', 'aria-hidden': 'true'}, Array.from({length: total}, (_, i) => el('span', {class: i === step ? 'is-current' : null}))),
      el('div', {class: `guide-actions${step ? '' : ' single'}`}, step ? action([icon('prev'), t('back')], () => show(step - 1), {id: 'guide-prev'}) : null, next));
    $('.guide-body', guide).scrollTop = 0;
    if (guide.open) next.focus({preventScroll: true});
  };
  show(step);
  if (!guide.open) guide.showModal();
  $('#guide-next', guide).focus({preventScroll: true});   // showModal сам ставит фокус на первую кнопку («Пропустить»)
}
// отметка ставится сразу при закрытии кнопкой; Escape закрывает окно сам – событие close
function closeGuide() { stored('mechanic:onboarded', '1'); guide.close(); }
guide.addEventListener('close', () => stored('mechanic:onboarded', '1'));

function toggleLarge() {
  large = !large;
  stored('mechanic:large', String(large));
  applySettings();
  $('#font-size')?.setAttribute('aria-pressed', String(large));
  if ($('#question')) { $('#question').placeholder = questionHint(); resizeQuestion(); }
  if (state.route.page === 'chat') fitExcerpts(main);
}
function header() {
  const {page, vid} = state.route;
  const isPark = page === 'park';
  let tools = $('#header-tools', topbar);
  if (!tools) {
    const picker = action(icon('globe'), openLanguage, {id: 'language', 'aria-haspopup': 'dialog'}, el('span', {'aria-hidden': 'true'}));
    const size = action(el('span', {'aria-hidden': 'true'}, 'Aᴀ'), toggleLarge, {id: 'font-size'});
    tools = el('div', {id: 'header-tools'}, picker, size);
    topbar.append(tools);
  }
  const picker = $('#language', tools), size = $('#font-size', tools);
  picker.lastElementChild.textContent = lang.toUpperCase();
  picker.setAttribute('aria-label', `${t('language')}: ${languages[lang]}`);
  size.setAttribute('aria-label', t('large'));
  size.setAttribute('title', t('large'));
  size.setAttribute('aria-pressed', String(large));
  const identity = el('div', {class: 'identity'}, isPark ? mark() :
    action([icon('back'), el('span', {}, t('back'))], back, {class: 'back-button', 'aria-label': t('back')}),
    page === 'fleet' ? null : el(['draft', 'receipt'].includes(page) ? 'strong' : 'h1', {class: 'brand', tabindex: '-1'}, vid || t(isPark ? 'brand' : page)));
  if (topbar.firstElementChild === tools) topbar.prepend(identity);
  else topbar.firstElementChild.replaceWith(identity);
}

function navigate(route, replace = false) {
  routeScroll.set(state.route.key, main.scrollTop);
  route = {...route, key: ++routeSerial};
  history[replace ? 'replaceState' : 'pushState'](route, '', location.pathname);
  showRoute(route, true);
}
function back() { history.back(); }
window.addEventListener('popstate', e => {
  const route = e.state?.page ? e.state : {page: 'park'};
  if (manual.open && !route.manualCite) {
    const samePage = ['page', 'vid', 'sid'].every(key => route[key] === state.route[key]);
    closeManual();
    if (samePage) return;
  }
  if (route.manualCite) { openManual(route.manualCite, false); return; }
  if (languageDialog.open) languageDialog.close();
  routeScroll.set(state.route.key, main.scrollTop);
  showRoute(route, true, routeScroll.get(route.key));
});
async function showRoute(route, focus = false, scroll = 0) {
  if (state.route !== route) {
    if (dataDialog.open) dataDialog.close();
    cancelRecording();
  }
  state.loadFailed = false;
  state.route = route;
  header();
  dock.replaceChildren();
  main.className = route.page;
  main.scrollTop = 0;
  if (state.me === undefined) state.me = await json(`${api}/me`).catch(() => null);
  const load = route.page === 'fleet' ? async () => { [state.fleet, state.vehicles] = await Promise.all([json(`${api}/fleet`), state.vehicles || json(`${api}/vehicles`)]); }
    : route.page === 'park' && !state.vehicles ? async () => { state.vehicles = await json(`${api}/vehicles`); }
    : route.vid && !state.cards.has(route.vid) ? async () => { state.cards.set(route.vid, await json(endpoint(route.vid))); }
    : null;
  if (load) {
    main.setAttribute('aria-busy', 'true');
    main.replaceChildren(hint(t('loading'), {role: 'status'}));
    try { await load(); }
    catch (error) {
      if (state.route !== route) return;
      main.removeAttribute('aria-busy');
      state.loadFailed = true;
      main.replaceChildren(el('h2', {}, t('loadFailed')), hint(error instanceof TypeError ? t('network') : error.message, {role: 'alert'}), action(t('retry'), () => showRoute(route, true)));
      return;
    }
    if (state.route !== route) return;
  }
  main.removeAttribute('aria-busy');
  render();
  main.scrollTop = scroll;
  if (focus) ($('h1', main) || $('.brand', topbar))?.focus({preventScroll: true});
}

function title(text) { return el('h1', {tabindex: '-1'}, text); }
function searchKey(value) {
  const alphabet = {'А':'A', 'В':'B', 'Е':'E', 'К':'K', 'М':'M', 'Н':'H', 'О':'O', 'Р':'P', 'С':'C', 'Т':'T', 'У':'Y', 'Х':'X'};
  return String(value ?? '').toUpperCase().replace(/[АВЕКМНОРСТУХ]/g, s => alphabet[s]).replace(/[^\p{L}\p{N}]/gu, '');
}
const garage = v => v.garage_no || null;
const model = v => v.model || v.make;
const modelText = v => model(v)?.replace(/([\p{L}\p{N}])-(?=[\p{L}\p{N}])/gu, '$1‑');
const details = (label, ...body) => el('details', {class: 'fold'}, el('summary', {}, label), el('div', {class: 'fold-body'}, body));
const stageRank = Object.keys(stages);
const latestFirst = (a, b) => (Date.parse(b?.checked_at) || 0) - (Date.parse(a?.checked_at) || 0);
const orderedVehicles = () => [...state.vehicles].sort((a, b) => stageRank.indexOf(vehicleStage(a)) - stageRank.indexOf(vehicleStage(b)) || latestFirst(a.last_check, b.last_check));
function plate(value) {
  const split = /^(.*\p{L})(\d{2,3})$/u.exec(value);
  return el('strong', {class: 'plate', 'aria-label': value}, split ? [split[1], el('span', {class: 'plate-region'}, split[2])] : value);
}
function vehicleModel(v) {
  return el('span', {class: 'row-model'}, garage(v) && el('strong', {class: 'garage'}, garage(v)), model(v) && el('span', {}, modelText(v)));
}
function statusLine(status, check) {
  const cause = ['quarantine', 'anomaly'].includes(status) && (faultName(check) || (stageOf(check) === 'normal' && t('unresolved')));
  return el('span', {class: 'status-line'}, stagePill(status), cause && el('span', {class: 'cause'}, cause));
}
function vehicleRow(v) {
  return action(el('span', {class: 'row-copy'}, plate(v.vehicle_id), vehicleModel(v), statusLine(vehicleStage(v), v.last_check), v.last_check?.checked_at && el('span', {class: 'row-date'}, `${t('checkedLabel')}: `, checkTime(v.last_check.checked_at))),
    () => navigate({page: 'vehicle', vid: v.vehicle_id}), {class: 'vehicle-row', 'data-stage': vehicleStage(v), 'data-plate': v.vehicle_id}, icon('next'));
}
function renderPark() {
  const list = el('div', {class: 'vehicle-list'});
  const count = el('span', {class: 'count', 'aria-live': 'polite'});
  const input = el('input', {id: 'vehicle-search', 'aria-describedby': 'search-example', type: 'text', enterkeyhint: 'search', autocapitalize: 'characters', spellcheck: 'false', autocomplete: 'off', inputmode: 'search', oninput: e => { state.query = e.target.value; state.all = false; update(); }});
  const clear = iconButton(t('clear'), 'cross', () => { input.value = state.query = ''; state.all = false; update(); input.focus(); });
  const ordered = orderedVehicles();
  const update = () => {
    const key = searchKey(state.query);
    const found = key ? ordered.filter(v => [v.vehicle_id, v.garage_no].some(x => searchKey(x).includes(key))) : ordered;
    const visible = state.all ? found : found.slice(0, 8);
    count.textContent = t('count', {found: visible.length, total: found.length});
    clear.hidden = !state.query;
    list.replaceChildren(...visible.map(vehicleRow));
    if (!found.length) list.append(box(el('strong', {}, t('noResults'))));
    if (visible.length < found.length) list.append(action(t('showAll', {count: found.length - visible.length}), () => { state.all = true; update(); list.children[visible.length]?.focus(); }, {class: 'show-all'}));
  };
  input.value = state.query;
  update();
  main.replaceChildren(el('div', {class: 'search-group'}, el('label', {for: 'vehicle-search'}, t('search')),
    el('div', {class: 'search'}, icon('search'), input, clear), hint(t('searchExample'), {id: 'search-example'})),
    state.me?.user?.role !== 'mechanic' && action([icon('chart'), t('fleet'), icon('next')], () => { state.fleetFilter = ''; state.fleetNormal = false; navigate({page: 'fleet'}); }, {class: 'wide-link'}),
    el('div', {class: 'between list-heading'}, count, state.demo && el('span', {class: 'demo'}, t('demo')),
      // инструкция – словами, а не значком: строка уже есть, места в списке не занимает
      action([el('span', {class: 'help-mark', 'aria-hidden': 'true'}, '?'), t('help')], () => openGuide(), {class: 'link-button help-link', id: 'help', 'aria-haspopup': 'dialog'})), list,
    el('a', {class: 'data-link', href: '#data-dialog', 'aria-haspopup': 'dialog', onclick: e => { e.preventDefault(); openDataDialog(); }}, t('dataPolicy')),
    state.me?.user && el('p', {class: 'account'}, `${state.me.user.name} – ${state.me.user.role_name.toLocaleLowerCase('ru')}`, ' ',
      action(t('logout'), async () => { await fetch(`${api}/logout`, {method: 'POST'}); location.reload(); }, {class: 'link-button'})));
}
function renderFleet() {
  // B3 / С4 ТЗ: сводка по парку (норма / требует внимания / карантин), приоритетный список, история по клику
  const group = v => { const s = vehicleStage(v); return s === 'quarantine' ? 'quarantine' : s === 'normal' ? 'normal' : 'attention'; };
  // очередь – в порядке сервера (тяжесть, приоритет, оценка отклонения); машины, которых нет в очереди, – в конце
  const queue = state.fleet?.priority ?? [];
  const known = new Set(queue.map(v => v.vehicle_id));
  const order = ['quarantine', 'attention', 'normal'];
  const items = [...queue, ...orderedVehicles().filter(v => !known.has(v.vehicle_id))]
    .map((v, i) => [v, i]).sort(([a, i], [b, j]) => order.indexOf(group(a)) - order.indexOf(group(b)) || i - j).map(([v]) => v);
  const by = key => items.filter(v => group(v) === key);
  const failed = items.filter(v => vehicleStage(v) === 'check_failed').length;
  const tickets = items.filter(v => v.open_ticket).length;
  const tiles = [['quarantine', 'quarantine', 'red', 'ban'], ['attention', 'anomaly', 'amber', 'warn'], ['normal', 'normal', 'green', 'check']];
  const list = el('ol', {class: 'priority-list'});
  const more = el('div', {});
  const update = () => {
    const f = state.fleetFilter;
    const visible = f === 'open_ticket' ? items.filter(v => v.open_ticket) : f === 'check_failed' ? items.filter(v => vehicleStage(v) === 'check_failed') : f ? by(f)
      : items.filter(v => group(v) !== 'normal' || state.fleetNormal);
    list.replaceChildren(...visible.map((v, i) => el('li', {}, fleetRow(v, i + 1))));
    if (!visible.length) list.append(el('li', {}, box(hint(t('fleetEmpty')))));
    const normals = by('normal').length;
    more.replaceChildren(!f && !state.fleetNormal && normals ? action(t('showNormal', {count: normals}), () => { state.fleetNormal = true; update(); }, {class: 'wide-link center'}) : '');
    for (const btn of $$('[data-filter]', main)) btn.setAttribute('aria-pressed', String(btn.dataset.filter === f));
    heading.textContent = t(f ? 'fleetGroup' : 'fleetQueue', {name: f === 'open_ticket' ? t('openTickets').toLocaleLowerCase(lang) : f === 'check_failed' ? t('failed').toLocaleLowerCase(lang) : f ? t(tiles.find(x => x[0] === f)[1]).toLocaleLowerCase(lang) : ''});
  };
  const pick = key => () => { state.fleetFilter = state.fleetFilter === key ? '' : key; update(); };
  const heading = el('h2', {class: 'list-title'});
  main.replaceChildren(
    el('div', {class: 'page-head'}, el('h1', {tabindex: '-1'}, t('fleetTitle')), hint(t('fleetTotal', {n: items.length}))),
    el('section', {class: 'box fleet-summary'}, hint(t('fleetTilesHint')),
      el('div', {class: 'tiles'}, tiles.map(([key, label, tone, symbol]) => action(
        [el('span', {class: 'tile-top'}, el('strong', {class: 'tile-number'}, String(by(key).length)), icon(symbol)), el('span', {class: 'tile-label'}, t(label))],
        pick(key), {class: `tile ${tone}`, 'data-filter': key}))),
      action([icon('book'), el('span', {}, t('openTickets')), el('strong', {}, String(tickets))], pick('open_ticket'), {class: 'tickets-filter', 'data-filter': 'open_ticket'}),
      failed ? action([icon('mic'), el('span', {}, t('fleetBriefFailed', {n: ''}).replace(/:\s*$/u, '')), el('strong', {}, String(failed))], pick('check_failed'), {class: 'tickets-filter violet', 'data-filter': 'check_failed'}) : null),
    heading, list, more);
  update();
}
function fleetRow(v, rank) {
  const stage = vehicleStage(v);
  return action([el('span', {class: 'rank', 'aria-hidden': 'true'}, String(rank)),
    el('span', {class: 'row-copy'}, plate(v.vehicle_id), vehicleModel(v), statusLine(stage, v.last_check),
      priorityLabel(v.last_urgency) && stage !== 'normal' ? el('span', {class: `row-priority ${v.last_urgency}`}, priorityLine(v.last_urgency)) : null,
      el('span', {class: 'row-meta'}, v.open_ticket ? el('span', {class: 'ticket-note'}, t('ticketOpen', {id: v.open_ticket})) : null,
        v.last_check?.checked_at ? el('span', {class: 'row-date'}, `${t('checkedLabel')}: `, checkTime(v.last_check.checked_at)) : null)),
    icon('next')], () => navigate({page: 'vehicle', vid: v.vehicle_id}), {class: 'vehicle-row fleet-row', 'data-stage': stage, 'data-plate': v.vehicle_id});
}
function context(v, s) {
  return el('div', {class: 'context'}, vehicleModel(v), s?.checked_at && checkTime(s.checked_at));
}
function openCheck(v, s) {
  const c = conversationFor(v.vehicle_id, s.session_id);
  navigate({page: 'chat', vid: v.vehicle_id, sid: s.session_id});
  if (!c.busy && !c.verdict) sendChat(c, 'diagnose');
}
function renderVehicle(v) {
  const sessions = [...(v.sessions ?? [])].sort(latestFirst);
  const [latest, ...past] = sessions;
  const tickets = [...(v.tickets ?? [])].sort((a, b) => (Date.parse(b.created_at) || 0) - (Date.parse(a.created_at) || 0));
  main.replaceChildren(
    el('section', {class: 'box vehicle-head'}, plate(v.vehicle_id), vehicleModel(v),
      v.engine_model && hint(`${t('engine')}: ${v.engine_model}`),
      v.open_ticket && el('span', {class: 'ticket-note'}, t('ticketOpen', {id: v.open_ticket}))),
    el('section', {class: 'box selection'}, el('h2', {}, t('lastCheck')),
      latest ? [checkTime(latest.checked_at), statusLine(vehicleStage(v, latest, true), latest),
        primary(t('diagnose'), () => openCheck(v, latest), {id: 'diagnose'})] : hint(t('noChecks'))),
    scoreChart(v, sessions),
    details(t('checks'), past.length ? el('div', {class: 'checks'}, past.map(s =>
      action(el('span', {class: 'check-copy'}, checkTime(s.checked_at), statusLine(vehicleStage(v, s, false), s)),
        () => openCheck(v, s), {class: 'check-row', 'data-session': s.session_id}, icon('next')))) : hint(t('noPastChecks'))),
    details(t('pastTickets'), tickets.length ? el('div', {class: 'tickets'}, tickets.map(ticket => el('div', {class: 'ticket-entry'},
      el('strong', {}, ticket.ticket_id), checkTime(ticket.created_at), priorityLabel(ticket.urgency) && el('span', {}, priorityLine(ticket.urgency))))) : hint(t('noTickets'))),
  );
  renderComposer(conversationFor(v.vehicle_id, latest?.session_id ?? null));
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
function isComposerCurrent(c) {
  return isCurrent(c) || (state.route.page === 'vehicle' && state.route.vid === c.vid &&
    (state.cards.get(c.vid)?.last_check?.session_id ?? null) === c.sid);
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
const cleanQuote = value => displayText(value).replace(/(\p{L})-\s+(\p{Ll})/gu, '$1$2').replace(/\s+/gu, ' ').trim();
const cleanAssistant = value => displayText(value)
  .replace(/(?<!\p{L})гипотеза(?!\p{L})/giu, word => word[0] === 'Г' ? 'Возможная причина' : 'возможная причина')
  .replace(/(возможная причина:\s*)(\p{L}+)/giu, (_, prefix, word) => prefix + lowerStart(word));
function resultStage(c, d) {
  const v = state.cards.get(c.vid);
  const latest = v?.last_check?.session_id === (d.session_id || c.sid);
  const status = vehicleStage(v ?? {}, d, latest);
  // A normal recording and an unresolved fleet warning are separate facts.
  return status === 'anomaly' && stageOf(d) === 'normal' ? 'normal' : status;
}
function verdict(c, d, id, opens) {
  const status = resultStage(c, d);
  const fail = status === 'check_failed', normal = status === 'normal';
  const incompatible = d.rule === 'R3-not-applicable';
  const vTitle = t(status === 'quarantine' ? 'stopRelease' : fail ? 'failedTitle' : stages[status][0]);
  const cause = !normal && !fail && !incompatible && faultName(d);
  const entries = Array.isArray(d.urgency_reasons) ? d.urgency_reasons.filter(Boolean) : [];
  // The API sometimes sends a metrics readout as one of the reasons.
  const isMetricsLine = line => (/^(?:оценка отклонения|отклонение|(?:anomaly )?score)\s+\d/i.test(line) && /(?:уверенность|confidence)/i.test(line)) || /^код по справочнику/i.test(line);
  const whyLines = entries.map((line, index) => isMetricsLine(line) ? -1 : index).filter(index => index >= 0).slice(0, 2);
  const otherReasons = entries.filter((_, index) => !whyLines.includes(index));
  const card = el('div', {class: `verdict-head ${stages[status][1]}`}, el('h2', {}, vTitle),
    cause && el('p', {class: 'verdict-cause'}, t('hypothesis', {name: lowerStart(cause)})),
    incompatible && el('p', {}, t('notApplicable')),
    fail && (d.description || d.reason) && el('p', {}, t('rejectReason', {reason: lowerStart(cleanQuote(d.description || d.reason).replace(/^запись отбракована:\s*/iu, ''))})),
    // сначала что делать и насколько срочно, потом цифры и причины
    el('div', {class: 'next-action'}, !normal && el('h3', {}, t('next')),
      el('p', {}, d.action || t(fail ? 'nextFail' : normal ? 'nextNormal' : 'nextAnomaly')),
      priorityLabel(d.urgency) && el('p', {class: 'priority-label'}, priorityLine(d.urgency)),
      fail && reasons(recordTips(d.description || d.reason).map(key => t(key))),
      fail && hint(t('rerecordWhere'))),
    // те же слова и шкала, что у графика в карточке машины: отличие звука от нормы и уверенность программы – два разных числа;
    // порог заявки показываем только там, где заявка вообще возможна
    !fail && score(d.confidence) && el('div', {class: 'verdict-facts'},
      !incompatible && !normal && score(d.anomaly_score) && el('p', {}, `${t('scoreShort')}: ${scoreText(d.anomaly_score)} / 1`),
      el('p', {}, `${t('confidence')}: ${scoreText(d.confidence)} / 1`,
        !normal && !incompatible && score(d.conf_threshold) ? [' ', el('span', {class: 'nowrap'}, `(${t('confThreshold', {v: scoreText(d.conf_threshold)})})`)] : '')),
    !fail && whyLines.length ? el('div', {class: 'verdict-why'}, el('h3', {}, t(normal ? 'note' : 'why')), reasons(whyLines.map(index => entries[index]))) : null);
  const metrics = el('dl', {class: 'metrics'}, metric(t('score'), score(d.anomaly_score) ? `${scoreText(d.anomaly_score)} / 1` : null),
    metric(t('confidence'), score(d.confidence) ? `${scoreText(d.confidence)} / 1` : null), metric(t('quality'), qualities[d.signal_quality] && t(qualities[d.signal_quality])));
  const key = `priority-${id}`;
  const more = el('details', {class: 'fold', open: opens.has(key), 'data-trace': key}, el('summary', {}, t('metrics')),
    el('div', {class: 'fold-body'}, metrics, otherReasons.length && reasons(otherReasons)));
  return el('article', {class: `verdict ${status}`}, card, warnings(d.warnings),
    d.inspect_first === true && el('p', {class: 'notice amber inspection-notice'}, icon('warn'), el('strong', {}, t('inspectFirst'))),
    d.defect_note && defectNote(d.defect_note), more);
}
// Нет инструкции по узлу в руководстве этого двигателя: заявку продукт не отправляет, механик берет готовый текст рекомендации.
function copyButton(value) {
  const button = action(t('copyNumber'), async () => {
    try { await navigator.clipboard.writeText(value); } catch { /* без доступа к буферу номер все равно виден крупно */ }
    button.textContent = t('copiedNumber');
    setTimeout(() => { button.textContent = t('copyNumber'); }, 4000);
  }, {class: 'copy-id', 'data-command': 'copy-ticket'});
  return button;
}
function defectNote(text) {
  const plain = displayText(text);
  // номера машин, проверок и коды не переносим посередине: S-0021 должно читаться целиком
  const body = el('p', {class: 'defect-text'}, ...plain.split(/([A-ZА-ЯЁ0-9]+-[A-ZА-ЯЁ0-9.]+)/u)
    .map((part, i) => i % 2 ? el('span', {class: 'nowrap'}, part) : part).filter(Boolean));
  const copy = action(t('copyText'), async () => {
    try { await navigator.clipboard.writeText(plain); }
    catch { const range = document.createRange(); range.selectNodeContents(body); getSelection().removeAllRanges(); getSelection().addRange(range); document.execCommand('copy'); }
    copy.textContent = t('copiedText');
    setTimeout(() => { copy.textContent = t('copyText'); }, 4000);
  }, {class: 'secondary full', 'data-command': 'copy-defect-note'});
  return el('section', {class: 'box defect-note', 'aria-label': t('defectNote')},
    el('h3', {}, t('noTicketTitle')), hint(t('noTicketWhy')),
    el('h4', {}, t('defectNote')), body, copy);
}

function citationLink(cite, label, attrs = {}) {
  return el('a', {href: manualPath(cite.manual_id, cite.page), ...attrs, onclick: e => {
    if (e.button !== 0 || e.metaKey || e.ctrlKey || e.altKey || e.shiftKey) return;
    e.preventDefault();
    openManual(cite);
  }}, label);
}
// Keep common workshop measurements together without changing their values.
const units = String.raw`мм рт\. ст\.|кгс(?:[·⋅∙.]м|/см[²2])?|кПа|МПа|Па|бар|мм|см[²³23]?|км(?:/ч)?|мкм|м[²³23]?|об(?:/мин)?|мин|сек|ч|л(?:/мин)?|°[CFС]?|%|Н(?:[·⋅∙. ]м)?|кН|кг|мг|г|мл|В|А|Гц|кВт|mm|cm|km(?:/h)?|kg|kPa|MPa|Pa|bar|rpm|Nm|volts?|lit(?:er|re)s?|ms|Hz|kW|in|psi|s|m|h|V|A|L`;
const decimal = '[−-]?\\d+(?:[.,]\\d+)?';
const measurePattern = new RegExp(`(${decimal}\\s*[-–−]\\s*${decimal})(?:[ \u00a0]+(${units})(?![\\p{L}\\d]))?|(${decimal})[ \u00a0]+(${units})(?![\\p{L}\\d])`, 'giu');
// советы по перезаписи – под конкретную причину отбраковки из ML, общий совет последним
function recordTips(reason) {
  const text = String(reason || '').toLocaleLowerCase('ru');
  const specific = /перегруз|клиппинг|clip/u.test(text) ? 'recordTipLoud' : /оборот|холост/u.test(text) ? 'recordTipIdle'
    : /шум|не слышен/u.test(text) ? 'recordTipNoise' : null;
  return specific ? [specific, 'recordTip2'] : ['recordTip1', 'recordTip2', 'recordTip3'];
}
function measureNodes(value) {
  const nodes = [];
  let start = 0;
  for (const match of value.matchAll(measurePattern)) {
    nodes.push(value.slice(start, match.index));
    const [, range, rangeUnit, amount, unit] = match;
    const unitText = rangeUnit || unit;
    nodes.push(el('span', {class: 'measure'}, `${range?.replace(/\s/g, '') || amount}${unitText ? '\u00a0' + unitText : ''}`));
    start = match.index + match[0].length;
  }
  nodes.push(value.slice(start));
  return nodes;
}
function sourceExcerpt(quote, key, opens) {
  const text = cleanQuote(quote);
  if (!text) return null;
  const copy = el('p', {class: 'citation-excerpt'}, text);
  const toggle = action(t('more'), () => {
    container.classList.toggle('is-expanded');
    const expanded = container.classList.contains('is-expanded');
    toggle.setAttribute('aria-expanded', String(expanded));
    toggle.textContent = t(expanded ? 'less' : 'more');
    fitExcerpt(container);
  }, {class: 'excerpt-toggle', 'aria-expanded': 'false'});
  const container = el('div', {class: 'source-excerpt', 'data-excerpt': key}, copy, toggle);
  container.fullQuote = text;
  if (opens.has(key)) toggle.click();
  return container;
}
function markdown(text, citations, id, opens) {
  const rendered = el('div', {class: 'markdown'});
  const sources = new Map((citations ?? []).filter(c => c.manual_id && Number.isInteger(c.page) && c.page > 0).map(c => [Number(c.n), c]));
  const inline = (value, allowBold = true) => {
    const nodes = [], pattern = allowBold ? /\*\*([^*]+)\*\*|\s*\[(\d+)\]/g : /\s*\[(\d+)\]/g;
    let start = 0;
    for (const match of value.matchAll(pattern)) {
      const before = value.slice(start, match.index);
      const n = allowBold && match[1] ? null : Number(match[allowBold ? 2 : 1]);
      const cite = n === null ? null : sources.get(n);
      if (cite) {
        // ссылка [n] не уезжает на отдельную строку: держим её вместе с последним словом и знаком препинания после неё
        const split = before.search(/\S+$/u);
        const word = split < 0 ? '' : before.slice(split);
        nodes.push(...measureNodes(split < 0 ? before : before.slice(0, split)));
        const tail = value.slice(match.index + match[0].length).match(/^[.,;:!?)]+/u)?.[0] || '';
        nodes.push(el('span', {class: 'nowrap'}, word, '\u00a0', citationLink(cite, `[${n}]`, {class: 'citation-chip inline-cite', 'aria-label': t('source', {n, name: cite.title || cite.designation, page: cite.page})}), tail));
        start = match.index + match[0].length + tail.length;
        continue;
      }
      nodes.push(...measureNodes(before));
      if (n === null) nodes.push(el('strong', {}, inline(match[1], false)));
      else nodes.push(match[0]);
      start = match.index + match[0].length;
    }
    nodes.push(...measureNodes(value.slice(start)));
    return nodes;
  };
  let paragraph = null, list = null;
  for (const line of cleanAssistant(text).split(/\r?\n/)) {
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
    el('li', {}, citationLink(cite, el('strong', {}, `[${n}] ${t('pageRef', {name: cite.title || cite.designation, page: cite.page})}`), {class: 'citation-row'}),
      sourceExcerpt(cite.quote, `quote-${id}-${n}`, opens))))) : null;
  return [rendered, footer];
}
function fitExcerpt(quote) {
  const copy = $('.citation-excerpt', quote), button = $('.excerpt-toggle', quote);
  const full = quote.fullQuote;
  if (!copy.clientHeight) return;
  if (copy.textContent !== full) copy.textContent = full;
  if (quote.classList.contains('is-expanded')) return;
  const overflows = () => copy.scrollHeight > copy.clientHeight + 1;
  button.hidden = !overflows();
  if (button.hidden) return;
  const words = full.split(' ');
  let lo = 0, hi = words.length - 1;
  const excerpt = count => `${words.slice(0, count).join(' ')}…`;
  while (lo < hi) {
    const middle = Math.ceil((lo + hi) / 2);
    copy.textContent = excerpt(middle);
    if (overflows()) hi = middle - 1;
    else lo = middle;
  }
  copy.textContent = excerpt(lo);
}
function fitExcerpts(root) {
  root.querySelectorAll('.source-excerpt').forEach(fitExcerpt);
}
function trace(turn, open) {
  if (!turn.steps.length || (turn.steps.length === 1 && !turn.diagnosis && turn.steps[0].status !== 'error')) return null;
  return el('details', {class: 'fold trace', open, 'data-trace': `steps-${turn.id}`}, el('summary', {}, t('steps')),
    el('ol', {class: 'fold-body'}, turn.steps.map(s => el('li', {}, el('div', {class: 'between'}, el('strong', {}, s.title),
      s.status === 'running' ? pill(t('working'), 'neutral', 'clock') : s.status === 'error' ? pill(t('error'), 'red', 'cross') : pill(t('done'), 'green', 'check')), s.detail ? hint(s.detail) : null))));
}
function ticketCommand(c) {
  if (c.receipt) return action(t('openReceipt'), () => navigate({page: 'receipt', vid: c.vid, sid: c.sid}), {class: 'full'});
  if (!canDraft(c.verdict)) return null;
  return action(t(c.draft ? 'openDraft' : 'createDraft'), () => {
    if (c.draft) navigate({page: 'draft', vid: c.vid, sid: c.sid});
    else sendChat(c, 'draft_ticket');
  }, {class: 'full', 'data-command': 'draft', disabled: c.busy}, icon('next'));
}
function renderTurn(c, turn, latestResult, opens) {
  const block = el('section', {class: 'turn'});
  if (turn.question) block.append(el('div', {class: 'user-message'}, el('strong', {}, t('mechanic')), el('p', {}, turn.question)));
  const answers = turn.messages.map((m, i) => el('article', {class: 'box agent-message'}, markdown(m.text, m.citations, `${turn.id}-${i}`, opens)));
  // коротко – по умолчанию; кто только начинает, просит подробнее одной кнопкой под ответом, без переключателей
  if (answers.length && turn.detail !== 'detailed' && turn.mode !== 'draft_ticket' && turn === c.turns.at(-1) && !turn.pending && !c.busy)
    answers.push(action(t('moreDetail'), () => sendChat(c, null, t('moreDetailQ'), 'detailed'), {class: 'more-detail', 'data-command': 'more-detail'}));
  const log = trace(turn, opens.has(`steps-${turn.id}`));
  const diagnosisResponse = turn.diagnosis && answers.length ? el('details', {class: 'fold', open: opens.has(`answer-${turn.id}`), 'data-trace': `answer-${turn.id}`}, el('summary', {}, t('answer')), el('div', {class: 'fold-body'}, answers)) : null;
  // последний результат: объяснение помощника сразу видно под карточкой, пока его нет – место ответа с индикатором
  const explanation = turn.diagnosis && (answers.length || turn.pending) ? el('section', {class: 'explain', 'aria-label': t('answer')},
    el('h3', {class: 'explain-title'}, t('answer')),
    ...(answers.length ? answers : [el('p', {class: 'box explain-pending', role: 'status'}, spinner(), el('span', {}, t('explainPending')))])) : null;
  if (turn.diagnosis && !latestResult) {
    block.append(el('details', {class: 'fold previous', open: opens.has(`verdict-${turn.id}`), 'data-trace': `verdict-${turn.id}`}, el('summary', {}, t('result'), stagePill(resultStage(c, turn.diagnosis))), el('div', {class: 'fold-body'}, verdict(c, turn.diagnosis, turn.id, opens), diagnosisResponse, log)));
  } else {
    if (turn.diagnosis) {
      const card = verdict(c, turn.diagnosis, turn.id, opens);
      const command = ticketCommand(c);
      if (command) card.lastElementChild.before(command);
      block.append(card);
    }
    if (explanation) block.append(explanation);
    else if (answers.length) block.append(...answers);
    if (log) block.append(log);
  }
  for (const error of turn.errors) block.append(el('p', {class: 'notice red', role: 'alert'}, error));
  if (!c.busy && !c.verdict && turn === c.turns.at(-1) && turn.errors.length && turn.mode === 'diagnose') block.append(primary(t('retry'), () => turn.question ? ask(c, c.question, 'diagnose') : sendChat(c, 'diagnose')));
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

const faultName = d => (lang !== 'ru' && /^F\d\d$/.test(d?.anomaly_type ?? '') && t(`fault${d.anomaly_type}`)) || d?.anomaly_title;
const canDraft = d => ['anomaly', 'quarantine'].includes(stageOf(d)) && d.ticket_allowed !== false;
function updateChat(c, latestOnly = false, scrollTo = null) {
  if (!isCurrent(c)) { updateComposer(c); return; }
  const feed = $('#conversation');
  if (!feed) return;
  const turn = c.turns.at(-1);
  const result = c.turns.findLast(item => item.diagnosis);
  const opens = new Set([...feed.querySelectorAll('details[open], .source-excerpt.is-expanded')].map(d => d.dataset.trace || d.dataset.excerpt));
  const focus = document.activeElement;
  if (latestOnly && turn && !turn.diagnosis && feed.lastElementChild) feed.lastElementChild.replaceWith(renderTurn(c, turn, false, opens));
  else feed.replaceChildren(...c.turns.map(item => renderTurn(c, item, item === result, opens)));
  const cmd = $('[data-command="draft"]', feed);
  if (cmd) cmd.disabled = c.busy || recording?.c === c;
  if (focus?.dataset.command && !cmd?.disabled) cmd?.focus({preventScroll: true});
  fitExcerpts(feed);
  const progress = $('#chat-progress');
  // пока ждем объяснение к уже показанному результату, индикатор стоит на месте ответа, а не внизу
  $('#chat-progress-row').hidden = !c.busy || Boolean(turn?.diagnosis && turn.pending);
  const statusText = c.busy ? pendingText(turn) : '';
  if (progress.textContent !== statusText) progress.textContent = statusText;
  updateComposer(c);
  if (scrollTo) feed.lastElementChild?.querySelector(scrollTo)?.scrollIntoView({block: 'start'});
  syncExplainJump(c);
}
// Результат проверки приходит сразу, объяснение помощника – через несколько секунд под карточкой.
// Пока объяснение не видно на экране, внизу кнопка-указатель: «готовлю…», затем «готово – показать».
function syncExplainJump(c) {
  const button = $('#explain-jump');
  if (!button) return;
  const turn = c.turns.at(-1), box = $('#conversation .explain');
  let show = Boolean(isCurrent(c) && turn?.diagnosis && box && !turn.explainSeen && (turn.pending || turn.messages.length));
  if (show) {
    const limit = (button.closest('.dock')?.getBoundingClientRect().top ?? innerHeight) - 24;
    if (box.getBoundingClientRect().top < limit) {
      if (!turn.pending) turn.explainSeen = true;
      show = false;
    }
  }
  button.hidden = !show;
  if (!show) return;
  button.classList.toggle('is-ready', !turn.pending);
  const text = t(turn.pending ? 'explainBelow' : 'explainReady');
  const label = $('#explain-jump-text');
  if (label.textContent !== text) label.textContent = text;
}
let jumpFrame = 0;
main.addEventListener('scroll', () => {
  cancelAnimationFrame(jumpFrame);
  jumpFrame = requestAnimationFrame(() => { if (state.route.page !== 'chat') return; const c = state.chats.get(JSON.stringify([state.route.vid, state.route.sid ?? null])); if (c) syncExplainJump(c); });
}, {passive: true});
function renderChat(v, s, c) {
  const feed = el('div', {id: 'conversation', role: 'log', 'aria-label': t('chat'), 'aria-live': 'polite'});
  feed.addEventListener('toggle', () => fitExcerpts(feed), true);
  main.replaceChildren(context(v, s), feed);
  renderComposer(c);
  updateChat(c);
}
// «Как объяснять ответы» – один раз в инструкции; запрос в /api/chat несет выбранный уровень
function detailChoice(onChange) {
  const group = el('div', {class: 'detail-switch', role: 'group', 'aria-labelledby': 'detail-label'});
  for (const mode of ['brief', 'detailed']) {
    group.append(action(t(mode), () => {
      detail = mode;
      stored('mechanic:detail', mode);
      for (const button of group.children) button.setAttribute('aria-pressed', String(button.dataset.detail === mode));
      onChange?.();
    }, {'data-detail': mode, 'aria-pressed': String(detail === mode)}));
  }
  return el('div', {class: 'detail-choice'}, el('strong', {id: 'detail-label'}, t('answerDetail')), group,
    el('p', {class: 'hint', id: 'detail-hint'}, t(detail === 'detailed' ? 'detailedHint' : 'briefHint')));
}
function renderComposer(c) {
  const composer = el('form', {class: 'compose', onsubmit: e => { e.preventDefault(); ask(c, c.question); }},
    el('div', {class: 'question-row'}, el('textarea', {id: 'question', name: 'question', rows: '1', placeholder: questionHint(), 'aria-label': t('question'), autocomplete: 'off', maxlength: '2000', oninput: e => { c.question = e.target.value; if (c.voiceNotice === 'micReady') c.voiceNotice = ''; updateComposer(c); }}),
      el('div', {class: 'voice-status', id: 'voice-live', role: 'status', hidden: true}, el('span', {id: 'voice-label'}), el('span', {id: 'mic-timer', 'aria-hidden': 'true'})),
      iconButton(t('mic'), 'mic', () => toggleRecording(c), {id: 'mic'}),
      el('button', {id: 'send-question', class: 'primary', type: 'submit', 'aria-label': t('sendQuestion'), hidden: true}, t('send'))),
    el('p', {class: 'voice-status', id: 'voice-status', role: 'status', hidden: true}),
  );
  const jump = el('button', {type: 'button', class: 'chat-status explain-jump', id: 'explain-jump', hidden: true, onclick: () => {
    $('.explain')?.scrollIntoView({block: 'start', behavior: matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth'});
  }}, spinner(), el('span', {id: 'explain-jump-text'}), icon('down'));
  dock.replaceChildren(el('div', {class: 'dock chat-dock'}, el('div', {class: 'chat-status', id: 'chat-progress-row', hidden: true}, spinner(), el('span', {id: 'chat-progress', role: 'status'})), jump, composer));
  $('#question').value = c.question;
  updateComposer(c);
}
// на узком экране с крупным шрифтом длинная подсказка в поле обрезается – тогда короче
const questionHint = () => t(large && innerWidth < 400 ? 'questionShort' : 'question');
addEventListener('resize', () => { const q = $('#question'); if (q) q.placeholder = questionHint(); });
function resizeQuestion() {
  const input = $('#question');
  if (!input || input.hidden) return;
  if (!input.value) { input.style.height = ''; return; }  // пустое поле – ровно по высоте кнопки, подсказка не растягивает
  input.style.height = 'auto';
  const css = getComputedStyle(input);
  const borders = parseFloat(css.borderTopWidth) + parseFloat(css.borderBottomWidth);
  const max = parseFloat(css.lineHeight) * 4 + parseFloat(css.paddingTop) + parseFloat(css.paddingBottom) + borders;
  input.style.height = `${Math.min(input.scrollHeight + borders, max)}px`;
}
window.addEventListener('resize', () => { resizeQuestion(); fitExcerpts(main); });
function ask(c, value, mode = null) {
  const q = value.trim();
  if (!q || c.busy || recording?.c === c || !isComposerCurrent(c)) return;
  c.question = '';
  c.voiceNotice = '';
  $('#question').value = '';
  if (state.route.page === 'vehicle') {
    if (/диагност|результат|что с машин|что с двигател|проверк/i.test(q)) mode = 'diagnose';
    navigate({page: 'chat', vid: c.vid, sid: c.sid});
  }
  sendChat(c, mode, q);
}

let recording;
const RECORD_MS = 60000;
function updateComposer(c) {
  if (!isComposerCurrent(c) || !$('#mic')) return;
  const active = recording?.c === c ? recording : null;
  const running = active?.phase === 'recording';
  const mic = $('#mic'), label = running ? t('micStop') : t('mic');
  const input = $('#question'), send = $('#send-question');
  const hasText = Boolean(c.question.trim());
  mic.disabled = c.busy || Boolean(active && !running);
  mic.hidden = active ? active.phase === 'sending' : hasText;
  mic.setAttribute('aria-pressed', String(Boolean(running)));
  if (mic.getAttribute('aria-label') !== label || running !== mic.classList.contains('recording')) {
    mic.setAttribute('aria-label', label);
    mic.title = label;
    mic.classList.toggle('recording', running);
    mic.replaceChildren(icon(running ? 'stop' : 'mic'), running ? t('micStop') : null);
  }
  const cmd = $('[data-command="draft"]');
  if (cmd) cmd.disabled = c.busy || Boolean(active);
  $('.compose').classList.toggle('is-busy', c.busy);   // поле и режим ответа не пропадают, пока помощник работает
  input.hidden = Boolean(active);
  input.disabled = c.busy || Boolean(active);
  send.hidden = Boolean(active) || !hasText;
  send.disabled = c.busy || send.hidden;
  const live = $('#voice-live'), voice = $('#voice-status');
  const notice = active ? {asking: 'micAsk', recording: 'micRecording', sending: 'micTranscribe'}[active.phase] : c.voiceNotice;
  live.hidden = !active;
  voice.hidden = Boolean(active) || !notice;
  voice.classList.toggle('red', Boolean(notice && !active && notice !== 'micReady'));
  const message = active ? $('#voice-label') : voice;
  if (message.textContent !== (notice ? t(notice) : '')) message.textContent = notice ? t(notice) : '';
  const timer = $('#mic-timer');
  timer.hidden = !running;
  resizeQuestion();
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
    if (isComposerCurrent(c)) $('#question').value = c.question;
    endRecording(active, 'micReady');
  } catch {
    endRecording(active, 'micService');
  } finally {
    clearTimeout(deadline);
  }
}
async function toggleRecording(c) {
  if (recording?.c === c) { stopRecording(recording); return; }
  if (recording || c.busy || !isComposerCurrent(c)) return;
  c.voiceNotice = '';
  if (!window.isSecureContext || !navigator.mediaDevices?.getUserMedia || typeof MediaRecorder !== 'function') {
    c.voiceNotice = window.isSecureContext ? 'micUnsupported' : 'micSecure';
    updateComposer(c);
    return;
  }
  if (!voiceConsent) { if (!dataDialog.open) openDataDialog(c); return; }
  const active = {c, lang, phase: 'asking', parts: [], abort: new AbortController()};
  recording = active;
  updateComposer(c);
  try {
    active.stream = await navigator.mediaDevices.getUserMedia({audio: true});
    if (recording !== active || !isComposerCurrent(c)) { releaseRecording(active); return; }
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
async function sendChat(c, mode, question = '', level = detail) {
  if (c.busy || recording?.c === c || (mode === 'draft_ticket' && !canDraft(c.verdict))) return;
  c.busy = true;
  const turn = {id: c.turns.length + 1, question, mode, detail: level, pending: true, steps: [], messages: [], errors: []};
  c.turns.push(turn);
  updateChat(c, false, question ? '.user-message' : null);
  if (mode === 'diagnose' && isCurrent(c)) main.scrollTop = 0;
  let done = false;
  try {
    const res = await fetch(`${api}/chat`, jsonPost({conversation_id: c.id, vehicle_id: c.vid, session_id: c.sid, message: question, action: mode, lang, detail: level}));
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
        c.draftNeedsInspection = c.verdict?.inspect_first === true;
        c.edits = {conclusion: cleanAssistant(c.draft.conclusion), urgency: c.draft.urgency || '', operations: displayText((c.draft.operations || []).join('\n')), spare_parts: displayText((c.draft.spare_parts || []).join('\n'))};
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
    if (turn.errors.length && question && !turn.messages.length) {
      c.question = question;
      if (isComposerCurrent(c)) $('#question').value = question;
    }
    updateChat(c, true, turn.errors.length ? '.notice' : null);
    if (turn.draft && isCurrent(c) && !turn.errors.length) navigate({page: 'draft', vid: c.vid, sid: c.sid});
  }
}

function groupRefs(references) {
  const groups = new Map();
  for (const r of references) {
    const name = r.title || r.manual;
    if (!groups.has(name)) groups.set(name, []);
    if (!groups.get(name).some(x => x.pdf_page === r.pdf_page && x.manual_id === r.manual_id)) groups.get(name).push(r);
  }
  return [...groups];
}
function field(c, name, label, rows, placeholder = '') {
  const grow = node => { node.style.height = 'auto'; node.style.height = `${node.scrollHeight + 2}px`; };
  const input = el('textarea', {name, rows, placeholder, required: name === 'conclusion', oninput: e => { c.edits[name] = e.target.value; grow(e.target); }});
  input.value = displayText(c.edits[name]);
  requestAnimationFrame(() => grow(input));
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
    el('section', {class: 'box stack'}, d.anomaly_type || c.verdict?.anomaly_title ? el('div', {class: 'field-static'}, el('span', {}, t('faultType')), el('strong', {}, [d.anomaly_type, c.verdict?.anomaly_title].filter(Boolean).join(' – '))) : null, field(c, 'conclusion', t('conclusion'), 2)),
    el('section', {class: 'box stack'}, el('label', {class: 'field'}, el('span', {}, t('priority')), urgency), overrideField,
      details(t('whyPriority'), reasons(d.urgency_reasons))),
    el('section', {class: 'box stack'}, field(c, 'operations', t('work'), 2, t('newLine')), field(c, 'spare_parts', t('parts'), 1, t('newLine'))),
    references.length ? el('section', {class: 'box stack'}, el('h3', {}, t('sources')), groupRefs(references).map(([name, refs]) =>
      el('div', {class: 'ref-group'}, el('p', {class: 'ref-name'}, icon('book'), name),
        el('div', {class: 'ref-pages'}, refs.map(r => citationLink({manual_id: r.manual_id, title: name, page: r.pdf_page}, t('pageShort', {page: r.pdf_page}), {class: 'page-chip', 'aria-label': t('pageRef', {name, page: r.pdf_page})})))))) : null,
    el('p', {id: 'ticket-error', role: 'alert', class: 'notice red', hidden: !c.confirmError}, c.confirmError || ''),
  );
  const warning = warnings(d.warnings);
  main.replaceChildren(context(v, s), el('div', {class: 'intro'}, pill(t('unsent'), 'neutral', 'clock'), title(t('draft')), hint(t('draftIntro'))), ...(warning ? [warning] : []), form);
  const blocked = () => c.draftNeedsInspection && !c.edits.inspectionConfirmed;
  const button = el('button', {id: 'confirm-ticket', class: 'primary full', type: 'submit', form: 'draft-form',
    'aria-describedby': 'confirm-note'}, c.confirming ? t('sending') : t('confirm'), icon('send'));
  const note = hint('', {id: 'confirm-note', role: 'status'});
  const syncConfirm = () => {
    button.disabled = Boolean(c.confirming || c.confirmUncertain || blocked());
    note.textContent = t(blocked() ? 'inspectBeforeSend' : 'confirmNote');
  };
  const inspection = c.draftNeedsInspection && checkRow('inspection-confirmed', t('inspectionConfirmed'), {
    form: 'draft-form', required: true, checked: Boolean(c.edits.inspectionConfirmed), disabled: c.confirming || c.confirmUncertain,
    onchange: e => { c.edits.inspectionConfirmed = e.target.checked; syncConfirm(); },
  });
  syncConfirm();
  dock.replaceChildren(el('div', {class: 'dock'}, inspection, button, note));
}
async function confirmTicket(c) {
  if (c.confirming || c.confirmUncertain || c.receipt || (c.draftNeedsInspection && !c.edits.inspectionConfirmed)) return;
  const lines = value => value.split(/\r?\n/).map(line => line.trim()).filter(Boolean);
  const conclusion = c.edits.conclusion.trim();
  const override = c.edits.urgency !== c.draft.urgency ? (c.edits.urgencyReason || '').trim() : '';
  const payload = {draft_id: c.draft.draft_id, conclusion: override ? `${conclusion}\n${t('reasonLine', {reason: override})}` : conclusion, urgency: c.edits.urgency, operations: lines(c.edits.operations), spare_parts: lines(c.edits.spare_parts),
    ...(c.draftNeedsInspection ? {inspection_confirmed: Boolean(c.edits.inspectionConfirmed)} : {})};
  const invalid = !conclusion ? t('needConclusion') : c.edits.urgency !== c.draft.urgency && !override ? t('needReason') : '';
  if (invalid) { $('#ticket-error').hidden = false; $('#ticket-error').textContent = invalid; return; }
  c.confirming = true;
  c.confirmError = '';
  const button = $('#confirm-ticket');
  button.disabled = true;
  button.textContent = t('sending');
  if (c.draftNeedsInspection) $('#inspection-confirmed').disabled = true;
  $('#ticket-error').hidden = true;
  try {
    const data = await json(`${api}/tickets/confirm`, jsonPost(payload));
    if (data.status !== 'created' || !data.ticket_id) throw new Error(t('noTicketId'));
    c.receipt = {id: data.ticket_id, payload, conclusion, override};
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
  const fields = [[t('machine'), [v.vehicle_id, v.garage_no].filter(Boolean).join(' / ')], [t('checkedAt'), dateFor(s?.checked_at)],
    [t('conclusion'), result.conclusion, 'receipt-prose'], [t('priority'), priorityLabel(result.payload.urgency)],
    ...(result.override ? [[t('overrideLabel'), result.override, 'receipt-prose']] : [])];
  main.replaceChildren(el('section', {class: 'receipt green'}, title(t('receipt')), el('div', {class: 'receipt-row'}, el('strong', {class: 'receipt-id mono'}, result.id), copyButton(result.id)), hint(t('receiptHint'))), el('section', {class: 'box stack'}, el('h2', {}, t('sentDetails')), el('dl', {class: 'receipt-fields'}, fields.map(([label, value, style]) => el('div', {}, el('dt', {}, label), el('dd', {class: style}, value))))));
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
function openManual(cite, push = true) {
  if (push) history.pushState({...state.route, manualCite: cite}, '', location.pathname);
  viewer = {cite, serial: 0, trigger: document.activeElement};
  manual.replaceChildren();
  if (!manual.open) manual.showModal();
  document.body.classList.add('viewing-page');
  loadManual(cite.page);
}
manual.addEventListener('cancel', event => { event.preventDefault(); back(); });
function closeManual() {
  const trigger = viewer?.trigger;
  viewer = null;
  manual.close();
  document.body.classList.remove('viewing-page');
  trigger?.focus({preventScroll: true});
}
function pageText(text, quote) {
  const needle = cleanQuote(quote).replace(/^…|…$/g, '').trim();
  text = text.replace(/(\p{L})-\s+(\p{Ll})/gu, '$1$2');
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
  const head = el('header', {class: 'top manual-top'}, iconButton(t('closeManual'), 'back', back, {id: 'close-manual'}), el('strong', {}, t('manual')));
  const body = el('div', {class: 'manual-body'}, el('h2', {id: 'manual-heading'}, cite.title || cite.designation || t('manual')), hint(t('openPage', {page}), {role: 'status'}));
  manual.replaceChildren(head, body);
  manual.scrollTop = 0;
  $('#close-manual').focus({preventScroll: true});
  try {
    const meta = await json(manualPath(cite.manual_id, page));
    if (viewer !== active || seq !== active.serial) return;
    const quote = page === cite.page ? cleanQuote(cite.quote) : '';
    const {copy, found} = pageText(meta.text || '', quote);
    const loading = el('p', {class: 'image-status', role: 'status'}, spinner(), t('imageLoading'));
    const image = el('img', {id: 'manual-image', alt: t('pageRef', {name: meta.title, page: meta.page}), hidden: true});
    const viewport = el('div', {class: 'page-frame'}, loading, image);
    const zoomOut = iconButton(t('zoomOut'), 'minus', () => changeZoom(-.5), {id: 'zoom-out', disabled: true});
    const zoomIn = iconButton(t('zoomIn'), 'plus', () => changeZoom(.5), {id: 'zoom-in', disabled: true});
    image.addEventListener('load', () => { loading.remove(); image.hidden = false; zoomIn.disabled = false; });
    image.addEventListener('error', () => { loading.replaceWith(hint(t('imageFailed'), {role: 'status'})); });
    let zoom = 1;
    const zoomLevel = el('output', {'aria-live': 'polite'}, '100%');
    const changeZoom = delta => {
      zoom = Math.max(1, Math.min(3, zoom + delta));
      image.style.width = `${zoom * 100}%`;
      zoomLevel.textContent = `${zoom * 100}%`;
      zoomOut.disabled = zoom === 1;
      zoomIn.disabled = zoom === 3;
    };
    const toggleZoom = () => changeZoom(zoom === 1 ? 1 : -2);
    let lastTap;
    let suppressDoubleClickUntil = 0;
    image.addEventListener('pointerup', e => {
      if (e.pointerType !== 'touch' || !e.isPrimary) return;
      const now = performance.now();
      if (lastTap && now - lastTap.at < 330 && Math.hypot(e.clientX - lastTap.x, e.clientY - lastTap.y) < 24) {
        toggleZoom();
        lastTap = null;
        suppressDoubleClickUntil = now + 500;
      } else lastTap = {at: now, x: e.clientX, y: e.clientY};
    });
    image.addEventListener('dblclick', () => { if (performance.now() > suppressDoubleClickUntil) toggleZoom(); });
    body.replaceChildren(...[el('div', {class: 'intro'}, el('h2', {id: 'manual-heading'}, meta.title || cite.title)),
      el('div', {class: 'manual-controls'}, el('div', {class: 'page-navigation'},
        iconButton(t('prevPage'), 'prev', () => loadManual(page - 1), {id: 'manual-prev', disabled: page <= 1}), el('strong', {'aria-live': 'polite'}, t('pageNumber', {page: meta.page, total: meta.pages_total})),
        iconButton(t('nextPage'), 'next', () => loadManual(page + 1), {id: 'manual-next', disabled: page >= meta.pages_total})),
        el('div', {class: 'zoom-group', role: 'group', 'aria-label': t('zoom')}, el('span', {}, t('zoom')), zoomOut, zoomLevel, zoomIn)),
      quote ? el('section', {class: 'box manual-text'}, el('h3', {}, t('quote')), el('blockquote', {class: found ? 'matched-quote' : null}, `«${quote}»`)) : null,
      viewport,
      meta.text ? details(t('pageText'), copy) : null,
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

history.scrollRestoration = 'manual';
state.route.key = routeSerial;
history.replaceState(state.route, '', location.pathname);
showRoute(state.route);
if (stored('mechanic:onboarded') !== '1') openGuide();
json(`${api}/health`).then(health => { if (health.mode === 'demo') { state.demo = true; if (state.route.page === 'park' && !main.hasAttribute('aria-busy') && !state.loadFailed) { const heading = $('.list-heading'); if (heading && !$('.demo', heading)) heading.insertBefore(el('span', {class: 'demo'}, t('demo')), $('#help', heading));  } } }).catch(() => {});
