import { test } from 'node:test';
import assert from 'node:assert/strict';
import { currentTurn, frameState } from '../static/view_logic.mjs';
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
