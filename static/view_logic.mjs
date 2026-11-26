export function currentTurn(job) {
 const events=job?.events||[];
 const start=[...events].reverse().find(e=>e.event==='TURN_START');
 const done=start&&[...events].reverse().find(e=>e.event==='TURN_DONE'&&e.attempt_id===start.attempt_id&&e.turn===start.turn);
 return {start,answer:done?.response??null};
}
export function frameState(mirror,lastReceived,now=Date.now()) {
 const status=mirror?.state||'OFF';
 return status==='LIVE'&&(!lastReceived||now-lastReceived>2000)?'DELAYED':status;
}
