import { test } from 'node:test';
import assert from 'node:assert/strict';
import { currentTurn, frameState, turnInfo, compactAppiumLine, earlierTurns, holdFrame, plannedRows } from '../static/view_logic.mjs';
test('a matching repeated prompt never reuses the earlier attempt answer', () => {
 const job={events:[{event:'TURN_START',attempt_id:'a',turn:'t',prompt:'same'}, {event:'TURN_DONE',attempt_id:'a',turn:'t',response:'old'}, {event:'TURN_START',attempt_id:'b',turn:'t',prompt:'same'}]};
 assert.equal(currentTurn(job).answer,null);
 job.events.push({event:'TURN_DONE',attempt_id:'b',turn:'t',response:'new'});
 assert.equal(currentTurn(job).answer,'new');
});
test('changing turn inside one attempt clears the previous answer',()=>{
 assert.equal(currentTurn({events:[{event:'TURN_DONE',attempt_id:'a',turn:'1',response:'old'},{event:'TURN_START',attempt_id:'a',turn:'2',prompt:'next'}]}).answer,null);
});
test('a frame becomes delayed independently of job and log polling',()=>{
 assert.equal(frameState({state:'LIVE'},1000,3501),'DELAYED');
 assert.equal(frameState({state:'LIVE'},1000,1200),'LIVE');
 assert.equal(frameState({state:'PRIVACY'},1000,1200),'PRIVACY');
 assert.equal(frameState({state:'ENDED'},1000,9000),'ENDED');
});
test('turn position is computed across conversations of a case',()=>{
 const definition={conversations:[['a','b'],['c','d','e']]};
 assert.deepEqual(turnInfo('conversation2_turn1',definition),{conversation:2,conversations:2,turn:1,conversationTurns:3,overall:3,totalTurns:5});
 assert.equal(turnInfo('conversation1_turn1',{conversations:[['only']]}).totalTurns,1);
 assert.equal(turnInfo('unexpected',definition),null);
});
test('Appium log lines keep [HTTP] and status but shorten session ids and dates',()=>{
 const line='2026-11-26 03:46:10:813 [HTTP] <-- GET /session/414b9248-0627-4b97-bd1a-44ab59496e6b/source 200 35 ms - 101098';
 assert.equal(compactAppiumLine(line),'03:46:10:813 [HTTP] <-- GET /session/414b9248…/source 200 35 ms - 101098');
 assert.equal(compactAppiumLine('plain line'),'plain line');
});
test('earlier turns list only finished turns of the current attempt',()=>{
 const job={events:[
  {event:'TURN_START',attempt_id:'old',turn:'conversation1_turn1',prompt:'p0'},{event:'TURN_DONE',attempt_id:'old',turn:'conversation1_turn1',response:'r0'},
  {event:'TURN_START',attempt_id:'a',turn:'conversation1_turn1',prompt:'p1'},{event:'TURN_DONE',attempt_id:'a',turn:'conversation1_turn1',response:'r1'},
  {event:'TURN_START',attempt_id:'a',turn:'conversation1_turn2',prompt:'p2'}]};
 const start=job.events.at(-1);
 assert.deepEqual(earlierTurns(job,start),[{turn:'conversation1_turn1',prompt:'p1',response:'r1'}]);
 assert.deepEqual(earlierTurns(job,null),[]);
});
test('a guarded gap keeps the last frame only for the same running attempt',()=>{
 assert.equal(holdFrame('PRIVACY','a','a'),true);
 assert.equal(holdFrame('PRIVACY','a','b'),false);
 assert.equal(holdFrame('DISCONNECTED','a','a'),false);
 assert.equal(holdFrame('LIVE','a','a'),false);
 assert.equal(holdFrame('DELAYED',null,'a'),false);
});
test('planned rows follow the worker order and mark running, waiting and done',()=>{
 const job={plan:{app:'both',cases:['MB-GEN-009'],repeats:2},
  attempts:[{application:'chatgpt',case_id:'MB-GEN-009',repeat:'1',attempt_id:'a1'}],
  active_attempt:{app:'chatgpt',case:'MB-GEN-009',repeat:2,attempt_id:'a2'}};
 const rows=plannedRows(job,true);
 assert.deepEqual(rows.map(r=>`${r.app}/${r.repeat}/${r.state}`),['chatgpt/1/DONE','chatgpt/2/RUNNING','gemini/1/WAITING','gemini/2/WAITING']);
 assert.equal(rows[1].attemptId,'a2');
 assert.deepEqual(plannedRows(job,false).map(r=>r.state),['DONE','STOPPED','NOT_RUN','NOT_RUN']);
 assert.equal(plannedRows({attempts:[{application:'gemini',case_id:'X',repeat:'1'}]},false)[0].state,'DONE');
});
