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
