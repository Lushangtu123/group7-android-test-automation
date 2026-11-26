// Pure view helpers. No DOM access, so they can be tested with node --test.

export function currentTurn(job) {
  const events = job?.events || [];
  const start = [...events].reverse().find(e => e.event === 'TURN_START');
  const done = start && [...events].reverse().find(
    e => e.event === 'TURN_DONE' && e.attempt_id === start.attempt_id && e.turn === start.turn
  );
  return { start, answer: done?.response ?? null };
}

export function frameState(mirror, lastReceived, now = Date.now()) {
  const status = mirror?.state || 'OFF';
  return status === 'LIVE' && (!lastReceived || now - lastReceived > 2000) ? 'DELAYED' : status;
}

// "conversation2_turn3" + case definition -> position of this turn in the whole case.
export function turnInfo(turn, definition) {
  const match = /^conversation(\d+)_turn(\d+)$/.exec(turn || '');
  if (!match) return null;
  const conversation = Number(match[1]);
  const index = Number(match[2]);
  const groups = definition?.conversations || [];
  const conversationTurns = groups[conversation - 1]?.length || null;
  const totalTurns = groups.reduce((n, g) => n + g.length, 0) || null;
  const overall = groups.slice(0, conversation - 1).reduce((n, g) => n + g.length, 0) + index;
  return {
    conversation,
    conversations: groups.length || null,
    turn: index,
    conversationTurns,
    overall,
    totalTurns,
  };
}

const UUID = /\b([0-9a-f]{8})-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b/gi;

// Shorten Appium session UUIDs and drop the repeated date so each HTTP line fits on one row.
export function compactAppiumLine(line) {
  return String(line)
    .replace(/^\d{4}-\d{2}-\d{2} (\d{2}:\d{2}:\d{2}:\d{3})/, '$1')
    .replace(UUID, '$1…');
}

// Completed turns of the current attempt before the one now running, oldest first.
export function earlierTurns(job, start) {
  if (!start) return [];
  const prompts = new Map();
  const done = [];
  for (const e of job?.events || []) {
    if (e.attempt_id !== start.attempt_id || e.turn === start.turn) continue;
    if (e.event === 'TURN_START') prompts.set(e.turn, e.prompt);
    if (e.event === 'TURN_DONE') done.push({ turn: e.turn, prompt: prompts.get(e.turn) ?? '', response: e.response ?? '' });
  }
  return done;
}

// While the view is guarded between turns, keep showing the last frame only if it
// belongs to the attempt that is still running.
export function holdFrame(status, frameAttempt, activeAttempt) {
  return ['PRIVACY', 'DELAYED', 'STARTING'].includes(status) && !!frameAttempt && frameAttempt === activeAttempt;
}

// Every planned execution in the worker's order (app, then repeat, then case), matched to
// recorded outcomes. state: DONE, RUNNING, WAITING (not started yet), STOPPED (started, run ended
// before it finished) or NOT_RUN (run ended before it started).
export function plannedRows(job, running) {
  const attempts = job?.attempts || [];
  const plan = job?.plan;
  const used = new Set();
  const rows = [];
  if (plan) {
    const apps = plan.app === 'both' ? ['chatgpt', 'gemini'] : [plan.app];
    const active = job.active_attempt;
    for (const app of apps) {
      for (let repeat = 1; repeat <= plan.repeats; repeat += 1) {
        for (const caseId of plan.cases) {
          const i = attempts.findIndex((r, k) => !used.has(k) && r.application === app && r.case_id === caseId && Number(r.repeat) === repeat);
          if (i >= 0) { used.add(i); rows.push({ app, caseId, repeat, state: 'DONE', attempt: attempts[i] }); continue; }
          const isActive = !!active && active.app === app && active.case === caseId && Number(active.repeat) === repeat;
          const state = running ? (isActive ? 'RUNNING' : 'WAITING') : (isActive ? 'STOPPED' : 'NOT_RUN');
          rows.push({ app, caseId, repeat, state, attemptId: isActive ? active.attempt_id : null });
        }
      }
    }
  }
  attempts.forEach((r, k) => {
    if (!used.has(k)) rows.push({ app: r.application, caseId: r.case_id, repeat: Number(r.repeat), state: 'DONE', attempt: r });
  });
  return rows;
}
