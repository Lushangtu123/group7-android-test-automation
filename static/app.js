import { currentTurn, frameState, turnInfo, compactAppiumLine, earlierTurns, holdFrame } from './view_logic.mjs';

const $ = s => document.querySelector(s);
const names = { chatgpt: 'ChatGPT', gemini: 'Gemini' };
const appLabels = { both: 'ChatGPT + Gemini', chatgpt: 'ChatGPT', gemini: 'Gemini' };
const terminal = new Set(['COMPLETED', 'INTERRUPTED', 'PROCESS_ERROR']);
// Finished runs do not change, so they are refreshed slowly instead of several times a second.
const IDLE_REFRESH_MS = 5000;

const state = {
  token: '', data: null, id: null, job: null, busy: false, source: 'python',
  logs: { python: [], appium: [] }, cursors: { python: 0, appium: 0 },
  mirror: { state: 'OFF' }, received: 0, sequence: 0, blob: null, frameJob: null,
  saved: null, savedFor: null, cameraKey: '', frameAttempt: null, historyKey: '',
  polling: false, logging: false, framing: false, lastPoll: 0, lastTail: 0,
};

const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
const appName = a => names[a] || a || '';
const isActive = () => !!state.job && !terminal.has(state.job.state);

async function api(path, body) {
  const response = await fetch(path, {
    method: body === undefined ? 'GET' : 'POST',
    headers: { 'X-Demo-Token': state.token, 'Content-Type': 'application/json' },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  let data;
  try { data = await response.json(); }
  catch { throw Error(`Local server returned ${response.status} without a readable reply`); }
  if (!response.ok) throw Error(data.error || 'Local request failed');
  return data;
}

function error(message) { $('#alert').hidden = !message; $('#alert').textContent = message || ''; }
function pill(status) { return `<span class="pill ${esc(status)}">${esc(status)}</span>`; }

function caseLabel(id) {
  const option = [...$('#case').options].find(o => o.value === id);
  return option ? option.textContent : id;
}

function updatePlan() {
  const count = Number($('#repeats').value) * ($('#application').value === 'both' ? 2 : 1);
  $('#plan').textContent = count + (count === 1 ? ' planned execution' : ' planned executions');
  renderDefinition();
  renderPreview();
}

// Before any run is selected, show what the chosen scenario will send and how it is judged.
function renderPreview() {
  const idle = !state.id;
  $('#preview').hidden = !idle;
  $('#live-turn').hidden = idle;
  if (!idle) return;
  const d = state.data?.definitions.find(d => d.case_id === $('#case').value);
  $('#current-app').textContent = 'PREVIEW · ' + caseLabel($('#case').value);
  if (!d) { $('#preview').textContent = 'Scenario details are loading…'; return; }
  const groups = d.conversations;
  const total = groups.reduce((n, g) => n + g.length, 0);
  let n = 0;
  $('#preview').innerHTML = `
    <div class="prompt-head"><span class="field-label">SCENARIO PREVIEW · ${esc(d.feature || '')}</span><span class="turn-position">${total} prompt${total === 1 ? '' : 's'} · ${esc(appLabels[$('#application').value])}</span></div>
    ${groups.map((g, i) => `${groups.length > 1 ? `<div class="field-label conv">CONVERSATION ${i + 1}</div>` : ''}<ol class="preview-prompts" start="${n + 1}">${g.map(p => { n += 1; return `<li>${esc(p)}</li>`; }).join('')}</ol>`).join('')}
    <div class="field-label">PASS RULE</div>
    <p class="preview-rule">${esc(d.expected || d.oracle)}</p>
    <p class="preview-note">Nothing is sent until you press Start real demo.</p>`;
}

function controls() {
  const active = isActive();
  $('#start').disabled = state.busy || active;
  $('#stop').hidden = !active;
  $('#stop').disabled = state.job?.state === 'STOPPING';
  for (const id of ['case', 'application', 'repeats', 'saved']) $('#' + id).disabled = state.busy || active;
}

function runLabel(j) {
  const when = new Date(j.started_utc).toLocaleString([], { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
  const plan = j.plan || {};
  const cases = (plan.cases || []).map(c => caseLabel(c).split(' · ')[0]).join(', ') || 'Unknown case';
  const outcome = j.state === 'COMPLETED' ? '' : ' · ' + j.state;
  return `${when} · ${cases} · ${appLabels[plan.app] || plan.app || ''} ×${plan.repeats ?? '?'}${outcome}`;
}

function savedRuns(jobs) {
  $('#saved').innerHTML = '<option value="">Choose a completed run</option>' + jobs.map(j =>
    `<option value="${esc(j.id)}" ${state.id === j.id ? 'selected' : ''}>${esc(runLabel(j))}</option>`
  ).join('');
}

function renderTurn(start) {
  const info = start && turnInfo(start.turn, state.data?.definitions.find(d => d.case_id === start.case));
  const position = $('#turn-position');
  const steps = $('#turn-steps');
  if (!info || !info.totalTurns) { position.hidden = true; steps.innerHTML = ''; return; }
  position.hidden = false;
  position.textContent = info.conversations > 1
    ? `Conversation ${info.conversation} of ${info.conversations} · turn ${info.turn} of ${info.conversationTurns}`
    : `Turn ${info.turn} of ${info.totalTurns}`;
  if (info.totalTurns < 2) { steps.innerHTML = ''; return; }
  let n = 0;
  steps.innerHTML = state.data.definitions.find(d => d.case_id === start.case).conversations.map(group =>
    group.map(() => { n += 1; return `<i class="${n < info.overall ? 'done' : n === info.overall ? 'now' : ''}"></i>`; }).join('')
  ).join('<i class="gap"></i>');
}

function renderHistory(job, start) {
  const rows = earlierTurns(job, start);
  const key = (start?.attempt_id || '') + ':' + rows.length;
  if (key === state.historyKey) return;
  state.historyKey = key;
  $('#history').hidden = !rows.length;
  $('#history-count').textContent = rows.length;
  $('#history-list').innerHTML = rows.map(r => {
    const info = turnInfo(r.turn, state.data?.definitions.find(d => d.case_id === start.case));
    return `<li><span class="h-turn">${info ? 'T' + info.overall : esc(r.turn)}</span><span class="h-q" title="${esc(r.prompt)}">${esc(r.prompt)}</span><span class="h-a" title="${esc(r.response)}">${esc(r.response)}</span></li>`;
  }).join('');
  // Keep the newest finished turn in view when the list is taller than its box.
  $('#history-list').scrollTop = $('#history-list').scrollHeight;
}

function renderJob(job) {
  $('#preview').hidden = true;
  $('#live-turn').hidden = false;
  const wasActive = state.lastState && !terminal.has(state.lastState);
  state.lastState = job.state;
  const { start, answer } = currentTurn(job);
  $('#current-app').textContent = start ? `${appName(start.app)} / ${start.case} / REPEAT ${start.repeat}` : 'PREPARING ANDROID SESSION';
  $('#run-state').className = 'pill ' + job.state;
  $('#run-state').textContent = job.state;
  $('#prompt').textContent = start?.prompt || 'Appium is preparing the app and checking the current conversation.';
  renderTurn(start);
  renderHistory(job, start);
  const attempt = job.details.find(d => d.attempt_id === start?.attempt_id);
  $('#answer').textContent = answer ?? 'Waiting for a validated response for this turn.';
  $('#answer').className = 'answer ' + (answer === null ? 'waiting' : (attempt?.status || ''));
  $('#verdict').innerHTML = attempt ? pill(attempt.status) : '';
  $('#attempt').textContent = start ? `ATTEMPT ${start.attempt_id} / ${start.turn}` : 'No attempt ID assigned.';
  $('#progress').textContent = `${job.state} · ${job.attempts.length} / ${job.planned} execution${job.planned === 1 ? '' : 's'}${job.elapsed_seconds !== null ? ' · ' + job.elapsed_seconds + 's' : ''}`;
  $('#counts').innerHTML = Object.entries(job.counts).map(([s, n]) =>
    `<span class="${n > 0 ? esc(s) : ''}">${esc(s)} <b>${Number(n)}</b></span>`
  ).join('');
  $('#outcomes').innerHTML = job.attempts.length
    ? job.attempts.map(r => `<tr><td>${esc(appName(r.application))} / repeat ${esc(r.repeat)}</td><td><button type="button" data-attempt="${esc(r.attempt_id)}">${esc(r.attempt_id)} ↗</button></td><td>${esc(r.completed_turns)} / ${esc(r.planned_turns)} turns</td><td>${pill(r.status)}</td><td>${Number(r.duration_seconds).toFixed(1)}s</td></tr>`).join('')
    : `<tr><td colspan="5">${terminal.has(job.state) ? 'No case outcome was recorded before the run ended.' : 'Appium is running. No case outcome has been recorded yet.'}</td></tr>`;
  $('#export').hidden = !terminal.has(job.state);
  $('#export').href = '/api/jobs/' + encodeURIComponent(job.id) + '/export';
  controls();
  // A run that just finished while being watched: bring the results table into view.
  if (wasActive && terminal.has(job.state)) {
    $('#results').scrollIntoView({ behavior: 'smooth', block: 'start' });
    savedRuns(state.data.jobs = state.data.jobs.map(j => j.id === job.id ? { ...j, state: job.state } : j));
  }
  if (terminal.has(job.state)) loadSavedFrame(job);
}

async function poll() {
  if (!state.id || state.polling) return;
  if (state.job && state.job.id === state.id && !isActive() && Date.now() - state.lastPoll < IDLE_REFRESH_MS) return;
  state.polling = true;
  const id = state.id;
  try {
    const job = await api('/api/jobs/' + encodeURIComponent(id));
    if (state.id !== id) return;
    state.job = job; state.lastPoll = Date.now();
    renderJob(job);
  } catch (e) { error(e.message); }
  finally { state.polling = false; }
}

const EVENT_TONE = { TURN_DONE: 'ok', RESULT: 'ok', STAGE_END: 'ok', SESSION_READY: 'ok', NEW_CHAT_READY: 'ok' };

function pythonLine(line) {
  let e;
  try { e = JSON.parse(line); } catch { return esc(line); }
  const tone = e.error ? 'bad' : (EVENT_TONE[e.event] || 'ev');
  const parts = [e.app && appName(e.app), e.attempt_id, e.turn].filter(Boolean).map(esc).join(' / ');
  let out = `<span class="t">${esc(e.utc?.slice(11, 23) || '')}</span> <span class="${tone}">${esc(e.event)}</span>${parts ? ' <span class="dim">/</span> ' + parts : ''}`;
  if (e.event === 'STAGE_START') out += ' <span class="dim">/ ' + esc(JSON.stringify(e.plan)) + '</span>';
  if (e.error) out += '\n  <span class="bad">' + esc(e.error) + '</span>';
  if (e.event === 'TURN_DONE') out += '\n  ' + esc(e.response);
  return out;
}

function appiumLine(line) {
  return esc(compactAppiumLine(line))
    .replace(/^(\d{2}:\d{2}:\d{2}:\d{3})/, '<span class="t">$1</span>')
    .replace(/ (\d{3}) (\d+ ms)/, (_, code, ms) => ` <span class="${code < 300 ? 'ok' : code < 400 ? 'warn' : 'bad'}">${code}</span> <span class="dim">${ms}</span>`);
}

function renderLogs() {
  const el = $('#logs');
  const stick = el.scrollHeight - el.scrollTop - el.clientHeight < 60;
  const lines = state.logs[state.source];
  el.innerHTML = lines.length
    ? lines.map(state.source === 'python' ? pythonLine : appiumLine).join('\n')
    : esc('Waiting for actual ' + (state.source === 'python' ? 'Python events' : 'Appium HTTP commands') + '…');
  // Only follow new output when the reader is already at the bottom.
  if (stick) el.scrollTop = el.scrollHeight;
}

async function tail() {
  if (!state.id || state.logging) return;
  if (state.job && state.job.id === state.id && !isActive() && Date.now() - state.lastTail < IDLE_REFRESH_MS) return;
  state.logging = true;
  const id = state.id;
  try {
    let changed = false;
    await Promise.all(['python', 'appium'].map(async source => {
      const data = await api(`/api/jobs/${encodeURIComponent(id)}/logs?source=${source}&after=${state.cursors[source]}`);
      if (id !== state.id) return;
      if (data.reset) { state.logs[source] = []; changed = true; }
      if (data.lines.length) changed = true;
      state.cursors[source] = data.cursor;
      state.logs[source].push(...data.lines);
      state.logs[source] = state.logs[source].slice(-100);
    }));
    if (id === state.id) {
      // Logs arrive in pages; keep reading quickly until a request brings nothing new.
      state.lastTail = changed ? 0 : Date.now();
      $('#log-status').textContent = 'ACTUAL OUTPUT · IDS SHORTENED';
      if (changed || !$('#logs').childElementCount) renderLogs();
    }
  } catch { $('#log-status').textContent = 'LOG CONNECTION DELAYED'; }
  finally { state.logging = false; }
}

// For a finished run, show the last saved evidence frame instead of the idle "ready" screen.
async function loadSavedFrame(job) {
  if (state.savedFor === job.id) return;
  state.savedFor = job.id;
  const id = job.id;
  try {
    const meta = await api(`/api/jobs/${encodeURIComponent(id)}/preview?meta=1`);
    const response = await fetch(`/api/jobs/${encodeURIComponent(id)}/preview`, { headers: { 'X-Demo-Token': state.token } });
    if (!response.ok || state.id !== id) return;
    const url = URL.createObjectURL(await response.blob());
    if (state.saved) URL.revokeObjectURL(state.saved.url);
    state.saved = { id, url, captured: meta.captured_utc, attempt: meta.attempt_id };
  } catch { /* No verified frame for this run; the panel says so. */ }
  camera();
}

const CURTAIN = {
  OFF: ['Ready for real automation.', 'Start a run to watch Appium operate the Android apps.'],
  STARTING: ['Connecting to Android.', 'The current device view will appear after verification.'],
  PRIVACY: ['Preparing a verified app view.', 'Navigation and account screens are hidden. Appium continues in the background.'],
  DELAYED: ['Stream delayed.', 'No fresh frame received. Test execution is independent of this view.'],
  DISCONNECTED: ['Device view unavailable.', 'Check the device connection. No test prompt is retried.'],
  ENDED: ['Run finished.', 'No live frame was published for this selection.'],
  SAVED: ['Saved run.', 'No verified device frame was kept for this run. Its results and logs are shown alongside.'],
};
// Shown over the dimmed last frame while Appium works on a screen that is not published.
const HELD_TEXT = {
  PRIVACY: 'Appium is working · showing the last verified frame',
  STARTING: 'Connecting · showing the last verified frame',
  DELAYED: 'Stream delayed · showing the last frame',
};
const STATUS_TEXT = { OFF: 'VIEW OFF', ENDED: 'RUN FINISHED', LIVE: 'DEVICE LIVE', PRIVACY: 'VIEW GUARDED', STARTING: 'CONNECTING', DELAYED: 'STREAM DELAYED', DISCONNECTED: 'DEVICE DISCONNECTED', SAVED: 'SAVED RUN', SAVED_FRAME: 'SAVED FRAME' };

function camera() {
  let status = frameState(state.mirror, state.received);
  const liveBlob = state.frameJob === state.id && !!state.blob;
  const finished = !!state.job && state.job.id === state.id && terminal.has(state.job.state);
  let mode = 'curtain';
  if (status === 'LIVE' && liveBlob) mode = 'live';
  else if (liveBlob && holdFrame(status, state.frameAttempt, state.job?.active_attempt?.attempt_id)) mode = 'held';
  else if (['OFF', 'ENDED'].includes(status) && liveBlob) { mode = 'ended'; status = 'ENDED'; }
  else if (finished && state.saved?.id === state.id) { mode = 'saved'; status = 'SAVED_FRAME'; }
  else if (finished) status = 'SAVED';

  $('#camera-dot').classList.toggle('on', mode === 'live');
  $('#camera-dot').classList.toggle('saved', mode === 'saved');
  $('#camera-status').textContent = STATUS_TEXT[status] || status;
  $('#frame-rate').textContent = state.mirror.fps ? state.mirror.fps.toFixed(1) + ' fps' : '— fps';
  if (mode === 'saved') {
    if ($('#device').src !== state.saved.url) { $('#device').src = state.saved.url; $('#large-device').src = state.saved.url; }
    $('#frame-time').textContent = 'Saved ' + new Date(state.saved.captured).toLocaleTimeString() + ' · not live';
  }
  $('#device').hidden = mode === 'curtain';
  $('#device').classList.toggle('frozen', mode === 'ended' || mode === 'saved' || mode === 'held');
  $('#zoom').hidden = mode === 'curtain';
  $('#curtain').hidden = mode === 'live';

  // Rebuild the overlay only when its content changes, so it does not flicker or re-announce.
  const key = mode + ':' + status;
  if (key !== state.cameraKey) {
    state.cameraKey = key;
    const curtain = $('#curtain');
    curtain.classList.toggle('banner', ['ended', 'saved', 'held'].includes(mode));
    curtain.classList.toggle('top', mode === 'held');
    if (mode === 'held') {
      curtain.innerHTML = `<strong>${esc(HELD_TEXT[status] || HELD_TEXT.PRIVACY)}</strong>`;
      $('#zoom-label').textContent = 'LAST VERIFIED FRAME · ' + status;
    } else if (mode === 'ended') {
      curtain.innerHTML = '<strong>Run finished · last live frame</strong>';
      $('#zoom-label').textContent = 'LAST FRAME · NOT LIVE';
    } else if (mode === 'saved') {
      curtain.innerHTML = '<strong>Saved run · last evidence frame</strong>';
      $('#zoom-label').textContent = 'SAVED EVIDENCE FRAME · NOT LIVE';
    } else {
      const [title, description] = CURTAIN[status] || CURTAIN.STARTING;
      curtain.innerHTML = `<div class="crosshair">⌗</div><h1>${title}</h1><p>${description}</p><span>Current screen · target 5 frames/sec</span>`;
      $('#zoom-label').textContent = status === 'LIVE' ? 'CURRENT DEVICE LIVE VIEW' : 'DEVICE VIEW · ' + status;
    }
  }
  if ($('#frame-dialog').open && mode === 'curtain') $('#frame-dialog').close();
}

async function frame() {
  if (state.framing || !state.id) return;
  // The device mirror only exists while a run is active.
  if (!isActive()) {
    if (!['OFF', 'ENDED'].includes(state.mirror.state)) { state.mirror = { state: state.frameJob === state.id ? 'ENDED' : 'OFF' }; camera(); }
    return;
  }
  state.framing = true;
  const id = state.id;
  try {
    const meta = await api('/api/mirror/status');
    if (id !== state.id) return;
    state.mirror = meta.run_id === id ? meta : { state: 'OFF' };
    if (state.mirror.state === 'LIVE' && meta.sequence !== state.sequence) {
      const response = await fetch('/api/mirror/frame', { headers: { 'X-Demo-Token': state.token } });
      if (response.ok) {
        const blob = await response.blob();
        const attempt = response.headers.get('X-Frame-Attempt');
        if (id !== state.id) return;
        if (state.job?.active_attempt?.attempt_id && attempt !== state.job.active_attempt.attempt_id) return;
        const url = URL.createObjectURL(blob), old = state.blob;
        state.blob = url; state.frameJob = id; state.frameAttempt = attempt; state.received = Date.now();
        state.sequence = Number(response.headers.get('X-Frame-Sequence'));
        $('#device').src = url; $('#large-device').src = url;
        if (old) URL.revokeObjectURL(old);
        const captured = response.headers.get('X-Frame-Captured-Utc');
        const delay = Date.now() - Date.parse(captured);
        $('#frame-time').textContent = `${new Date(captured).toLocaleTimeString()} · ${(delay / 1000).toFixed(2)}s capture→view`;
        // Bounded numeric diagnostics only. The preview bytes are never recorded here.
        window.liveFrameMetrics = window.liveFrameMetrics || [];
        window.liveFrameMetrics.push({ received: Date.now(), captured, delay_ms: delay, sequence: state.sequence, attempt_id: attempt });
        if (window.liveFrameMetrics.length > 3000) window.liveFrameMetrics.shift();
      }
    }
    camera();
  } catch { state.mirror = { state: 'DISCONNECTED' }; camera(); }
  finally { state.framing = false; }
}

function select(id) {
  Object.assign(state, {
    id, job: null, lastState: null, logs: { python: [], appium: [] }, cursors: { python: 0, appium: 0 },
    sequence: 0, received: 0, mirror: { state: 'OFF' }, frameJob: null, frameAttempt: null, savedFor: null, lastPoll: 0, lastTail: 0, historyKey: '',
  });
  $('#frame-time').textContent = 'No device frame received.';
  renderPreview(); renderLogs(); camera(); poll(); tail();
}

// Back to the idle state: no run selected, scenario preview shown.
function clearSelection() {
  Object.assign(state, { id: null, job: null, lastState: null, mirror: { state: 'OFF' }, frameJob: null, frameAttempt: null, savedFor: null, historyKey: '' });
  state.logs = { python: [], appium: [] };
  $('#run-state').className = 'pill'; $('#run-state').textContent = 'IDLE';
  $('#progress').textContent = 'No run started';
  $('#counts').innerHTML = ['PASS', 'FAIL', 'REVIEW', 'ERROR'].map(s => `<span>${s} <b>0</b></span>`).join('');
  $('#outcomes').innerHTML = '<tr><td colspan="5">Independent results appear here as each test finishes.</td></tr>';
  $('#export').hidden = true;
  $('#frame-time').textContent = 'No device frame received.';
  renderLogs(); camera(); renderPreview(); controls();
}

async function check() {
  $('#readiness').disabled = true;
  $('#health').textContent = 'Checking the existing emulator, apps and Appium…';
  try {
    const health = await api('/api/health');
    $('#health').textContent = health.ready ? '● Existing Android + Appium ready.' : 'Environment needs attention.';
    $('#checks').hidden = false;
    $('#checks').innerHTML = health.checks.map(c =>
      `<li class="${c.ok ? '' : 'bad'}" title="${esc(c.detail)}"><b>${c.ok ? '✓' : '✕'}</b>${esc(c.name)}</li>`
    ).join('');
    if (!health.ready) error(health.checks.filter(c => !c.ok).map(c => c.name + ': ' + c.instruction).join('\n'));
    else error('');
    return health;
  } finally { $('#readiness').disabled = false; }
}

function renderDefinition() {
  const d = state.data?.definitions.find(d => d.case_id === $('#case').value);
  if (!d) return;
  $('#definition').textContent = d.case_id + '\n' + d.conversations.map((g, i) =>
    'Conversation ' + (i + 1) + '\n' + g.map((p, j) => (j + 1) + '. ' + p).join('\n')
  ).join('\n\n') + '\n\nOracle: ' + d.oracle;
}

async function start() {
  if (state.busy || isActive()) return;
  state.busy = true; controls(); error('');
  try {
    const health = await check();
    if (!health.ready) return;
    const plan = { profile: 'full', app: $('#application').value, cases: [$('#case').value], repeats: Number($('#repeats').value) };
    const job = await api('/api/runs', plan);
    select(job.id);
    state.job = job;
    renderJob({ ...job, events: [], details: [], attempts: [], counts: { PASS: 0, FAIL: 0, REVIEW: 0, ERROR: 0 }, elapsed_seconds: 0 });
    state.data.jobs = await api('/api/jobs');
    savedRuns(state.data.jobs);
    $('.workbench').scrollIntoView({ behavior: 'smooth', block: 'start' });
  } catch (e) { error(e.message); }
  finally { state.busy = false; controls(); }
}

async function stop() {
  if (!confirm('Stop the running Android test?\n\nEvidence recorded so far is kept, but the current attempt will not finish.')) return;
  try {
    $('#stop').disabled = true;
    await api('/api/jobs/' + encodeURIComponent(state.id) + '/stop', {});
    state.lastPoll = 0;
    await poll();
    state.mirror = { state: 'OFF' };
    camera();
  } catch (e) { error(e.message); $('#stop').disabled = false; }
}

function detail(id) {
  const d = state.job?.details.find(d => d.attempt_id === id);
  if (!d) return;
  $('#answer-detail').innerHTML = `<div class="field-label">SAVED NEW DEMO RESULT · ${esc(id)}</div><h2>${esc(appName(d.application))} / ${esc(d.case_id)} / repeat ${esc(d.repeat)}</h2>${pill(d.status)}${d.input_groups.map((g, i) => g.map((p, j) => `<div class="answer-pair"><b>${esc(p)}</b><p>${esc(d.captured_response_groups?.[i]?.[j] ?? '[No complete response captured]')}</p></div>`).join('')).join('')}`;
  $('#answer-dialog').showModal();
}

function selectTab(source, focus) {
  state.source = source;
  for (const name of ['python', 'appium']) {
    const tab = $('#' + name + '-tab');
    tab.classList.toggle('selected', name === source);
    tab.setAttribute('aria-selected', String(name === source));
    tab.tabIndex = name === source ? 0 : -1;
  }
  $('#logs').setAttribute('aria-labelledby', source + '-tab');
  if (focus) $('#' + source + '-tab').focus();
  $('#logs').scrollTop = $('#logs').scrollHeight;
  renderLogs();
}

$('#start').onclick = start;
$('#stop').onclick = stop;
$('#readiness').onclick = () => check().catch(e => error(e.message));
$('#saved').onchange = e => { if (e.target.value) select(e.target.value); else clearSelection(); };
for (const id of ['case', 'application', 'repeats']) $('#' + id).onchange = updatePlan;
for (const source of ['python', 'appium']) $('#' + source + '-tab').onclick = () => selectTab(source);
$('[role="tablist"]').addEventListener('keydown', e => {
  if (!['ArrowLeft', 'ArrowRight', 'Home', 'End'].includes(e.key)) return;
  e.preventDefault();
  selectTab(state.source === 'python' ? 'appium' : 'python', true);
});
$('#model-button').onclick = () => { $('#model-dialog').showModal(); renderDefinition(); };
$('#generate').onclick = async () => {
  try {
    $('#generate').disabled = true;
    const result = await api('/api/generate', {});
    $('#generation-result').textContent = `Actual Python output: ${result.candidates} coordinates / ${result.executable} executable scenarios · ${result.elapsed_seconds}s · ${result.id}`;
  } catch (e) { error(e.message); }
  finally { $('#generate').disabled = false; }
};
$('#zoom').onclick = () => { $('#frame-dialog').showModal(); };
$('#fullscreen').onclick = () => {
  (document.fullscreenElement ? document.exitFullscreen() : document.documentElement.requestFullscreen()).catch(e => error(e.message));
};
document.addEventListener('click', e => {
  if (e.target.closest('.close')) e.target.closest('dialog').close();
  const target = e.target.closest('[data-attempt]');
  if (target) detail(target.dataset.attempt);
});

async function init() {
  camera();
  try {
    state.data = await api('/api/bootstrap');
    state.token = state.data.token;
    savedRuns(state.data.jobs);
    updatePlan();
    const active = state.data.jobs.find(j => !terminal.has(j.state));
    if (active) { select(active.id); await api('/api/mirror/start', { run_id: active.id }); }
    setInterval(poll, 500);
    setInterval(tail, 350);
    setInterval(frame, 200);
    setInterval(camera, 200);
  } catch (e) { error('Unable to connect to the local live demo: ' + e.message); }
}
init();
