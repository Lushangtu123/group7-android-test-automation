import {currentTurn,frameState} from './view_logic.mjs';
const $=s=>document.querySelector(s);
const names={chatgpt:'ChatGPT',gemini:'Gemini'};
const terminal=new Set(['COMPLETED','INTERRUPTED','PROCESS_ERROR']);
const state={token:'',data:null,id:null,job:null,busy:false,source:'python',logs:{python:[],appium:[]},cursors:{python:0,appium:0},mirror:{state:'OFF'},received:0,sequence:0,blob:null,frameJob:null,polling:false,logging:false,framing:false};
const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
async function api(path,body){
 const response=await fetch(path,{method:body===undefined?'GET':'POST',headers:{'X-Demo-Token':state.token,'Content-Type':'application/json'},body:body===undefined?undefined:JSON.stringify(body)});
 const data=await response.json();if(!response.ok)throw Error(data.error||'Local request failed');return data;
}
function error(message){$('#alert').hidden=!message;$('#alert').textContent=message||'';}
function pill(status){return `<span class="pill ${esc(status)}">${esc(status)}</span>`;}
function updatePlan(){const count=Number($('#repeats').value)*($('#application').value==='both'?2:1);$('#plan').textContent=count+' planned executions';renderDefinition();}
function controls(){
 const active=state.job&&!terminal.has(state.job.state);
 $('#start').disabled=state.busy||!!active;$('#stop').hidden=!active;$('#stop').disabled=state.job?.state==='STOPPING';
 for(const id of ['case','application','repeats','saved'])$('#'+id).disabled=state.busy||!!active;
}
function savedRuns(jobs){
 $('#saved').innerHTML='<option value="">Choose a completed run</option>'+jobs.map(j=>`<option value="${j.id}" ${state.id===j.id?'selected':''}>${esc(j.started_utc.slice(0,19))} UTC / ${esc(j.state)}</option>`).join('');
}
function renderJob(job){
 const {start,answer}=currentTurn(job);
 $('#current-app').textContent=start?`${names[start.app]} / ${start.case} / REPEAT ${start.repeat}`:'PREPARING ANDROID SESSION';
 $('#run-state').className='pill '+job.state;$('#run-state').textContent=job.state;
 $('#prompt').textContent=start?.prompt||'Appium is preparing the app and checking the current conversation.';
 $('#answer').textContent=answer??'Waiting for a validated response for this turn.';$('#answer').classList.toggle('waiting',answer===null);
 const attempt=job.details.find(d=>d.attempt_id===start?.attempt_id);
 $('#verdict').innerHTML=attempt?pill(attempt.status):'';
 $('#attempt').textContent=start?`ATTEMPT ${start.attempt_id} / ${start.turn}`:'No attempt ID assigned.';
 $('#progress').textContent=`${job.state} · ${job.attempts.length} / ${job.planned} executions${job.elapsed_seconds!==null?' · '+job.elapsed_seconds+'s':''}`;
 $('#counts').innerHTML=Object.entries(job.counts).map(([s,n])=>`<span>${s} <b>${n}</b></span>`).join('');
 $('#outcomes').innerHTML=job.attempts.length?job.attempts.map(r=>`<tr><td>${names[r.application]} / repeat ${r.repeat}</td><td><button data-attempt="${r.attempt_id}">${r.attempt_id} ↗</button></td><td>${r.completed_turns} / ${r.planned_turns} turns</td><td>${pill(r.status)}</td><td>${Number(r.duration_seconds).toFixed(1)}s</td></tr>`).join(''):'<tr><td colspan="5">Appium is running. No case outcome has been recorded yet.</td></tr>';
 $('#export').hidden=!terminal.has(job.state);$('#export').href='/api/jobs/'+job.id+'/export';
 controls();
}
async function poll(){
 if(!state.id||state.polling)return;state.polling=true;const id=state.id;
 try{const job=await api('/api/jobs/'+id);if(state.id!==id)return;state.job=job;renderJob(job);}
 catch(e){error(e.message);}finally{state.polling=false;}
}
function logLine(line){
 if(state.source==='appium')return line;
 try{const e=JSON.parse(line);return `${e.utc?.slice(11,23)||''} ${e.event}${e.app?' / '+names[e.app]:''}${e.attempt_id?' / '+e.attempt_id:''}${e.turn?' / '+e.turn:''}${e.error?'\n  '+e.error:''}${e.event==='TURN_DONE'?'\n  '+e.response:''}${e.event==='STAGE_START'?' / '+JSON.stringify(e.plan):''}`;}
 catch{return line;}
}
function renderLogs(){
 const lines=state.logs[state.source];$('#logs').textContent=lines.length?lines.map(logLine).join('\n'):'Waiting for actual '+(state.source==='python'?'Python events':'Appium HTTP commands')+'…';$('#logs').scrollTop=$('#logs').scrollHeight;
}
async function tail(){
 if(!state.id||state.logging)return;state.logging=true;const id=state.id;
 try{
  await Promise.all(['python','appium'].map(async source=>{
   const data=await api(`/api/jobs/${id}/logs?source=${source}&after=${state.cursors[source]}`);
   if(id!==state.id)return;if(data.reset)state.logs[source]=[];
   state.cursors[source]=data.cursor;state.logs[source].push(...data.lines);state.logs[source]=state.logs[source].slice(-100);
  }));if(id===state.id)renderLogs();
 }catch(e){$('#log-status').textContent='LOG CONNECTION DELAYED';}finally{state.logging=false;}
}
function camera(){
 const status=frameState(state.mirror,state.received);
 const current=state.frameJob===state.id&&!!state.blob;
 const ended=['OFF','ENDED'].includes(status)&&current;
 $('#camera-dot').classList.toggle('on',status==='LIVE');
 $('#camera-status').textContent=({OFF:'VIEW OFF',ENDED:'RUN FINISHED',LIVE:'DEVICE LIVE',PRIVACY:'VIEW GUARDED',STARTING:'CONNECTING',DELAYED:'STREAM DELAYED',DISCONNECTED:'DEVICE DISCONNECTED'})[status]||status;
 $('#frame-rate').textContent=state.mirror.fps?state.mirror.fps.toFixed(1)+' fps':'— fps';
 $('#device').hidden=!(current&&(status==='LIVE'||ended));$('#device').classList.toggle('frozen',ended);
 $('#zoom').hidden=!current||!['LIVE','OFF','ENDED'].includes(status);
 $('#curtain').hidden=status==='LIVE'&&current;$('#curtain').classList.toggle('ended',ended);
 if(ended){$('#curtain').innerHTML='<strong>Run finished · last live frame</strong>';$('#zoom-label').textContent='LAST FRAME · NOT LIVE';return;}
 const words={OFF:['Ready for real automation.','Start a run to watch Appium operate the Android apps.'],STARTING:['Connecting to Android.','The current device view will appear after verification.'],PRIVACY:['Preparing a verified app view.','Navigation and account screens are hidden. Appium continues in the background.'],DELAYED:['Stream delayed.','No fresh frame received. Test execution is independent of this view.'],DISCONNECTED:['Device view unavailable.','Check the device connection. No test prompt is retried.'],ENDED:['Run finished.','No live frame was published for this selection.']};
 const [title,description]=words[status]||words.STARTING;
 $('#curtain').innerHTML=`<div class="crosshair">⌗</div><h1>${title}</h1><p>${description}</p><span>Current screen · target 5 frames/sec</span>`;
 $('#zoom-label').textContent=status==='LIVE'?'CURRENT DEVICE LIVE VIEW':'DEVICE VIEW · '+status;
 if($('#frame-dialog').open&&status!=='LIVE'){$('#frame-dialog').close();}
}
async function frame(){
 if(state.framing||!state.id)return;state.framing=true;const id=state.id;
 try{
  const meta=await api('/api/mirror/status');if(id!==state.id)return;
  state.mirror=meta.run_id===id?meta:{state:'OFF'};
  if(state.mirror.state==='LIVE'&&meta.sequence!==state.sequence){
   const response=await fetch('/api/mirror/frame',{headers:{'X-Demo-Token':state.token}});
   if(response.ok){
    const blob=await response.blob();const attempt=response.headers.get('X-Frame-Attempt');
    if(id!==state.id)return;
    if(state.job?.active_attempt?.attempt_id&&attempt!==state.job.active_attempt.attempt_id)return;
    const url=URL.createObjectURL(blob),old=state.blob;state.blob=url;state.frameJob=id;state.received=Date.now();state.sequence=Number(response.headers.get('X-Frame-Sequence'));
    $('#device').src=url;$('#large-device').src=url;if(old)URL.revokeObjectURL(old);
    const captured=response.headers.get('X-Frame-Captured-Utc');const delay=Date.now()-Date.parse(captured);
    $('#frame-time').textContent=`${new Date(captured).toLocaleTimeString()} · ${(delay/1000).toFixed(2)}s capture→view`;
    // Bounded numeric diagnostics only. The preview bytes are never recorded here.
    window.liveFrameMetrics=window.liveFrameMetrics||[];window.liveFrameMetrics.push({received:Date.now(),captured,delay_ms:delay,sequence:state.sequence,attempt_id:attempt});if(window.liveFrameMetrics.length>3000)window.liveFrameMetrics.shift();
   }
  }
  camera();
 }catch(e){state.mirror={state:'DISCONNECTED'};camera();}finally{state.framing=false;}
}
function select(id){
 state.id=id;state.job=null;state.logs={python:[],appium:[]};state.cursors={python:0,appium:0};state.sequence=0;state.received=0;state.mirror={state:'OFF'};state.frameJob=null;renderLogs();camera();poll();tail();
}
async function check(){
 $('#readiness').disabled=true;
 try{const health=await api('/api/health');$('#health').textContent=health.ready?'● Existing Android + Appium ready.':'Environment needs attention.';
  if(!health.ready)error(health.checks.filter(c=>!c.ok).map(c=>c.name+': '+c.instruction).join('\n'));return health;
 }finally{$('#readiness').disabled=false;}
}
function renderDefinition(){
 const d=state.data?.definitions.find(d=>d.case_id===$('#case').value);if(!d)return;
 $('#definition').textContent=d.case_id+'\n'+d.conversations.map((g,i)=>'Conversation '+(i+1)+'\n'+g.map((p,j)=>(j+1)+'. '+p).join('\n')).join('\n\n')+'\n\nOracle: '+d.oracle;
}
async function start(){
 if(state.busy||state.job&&!terminal.has(state.job.state))return;
 state.busy=true;controls();error('');
 try{
  const health=await check();if(!health.ready)return;
  const plan={profile:'full',app:$('#application').value,cases:[$('#case').value],repeats:Number($('#repeats').value)};
  const job=await api('/api/runs',plan);select(job.id);state.job=job;renderJob({...job,events:[],details:[],attempts:[],counts:{PASS:0,FAIL:0,REVIEW:0,ERROR:0},elapsed_seconds:0});savedRuns(await api('/api/jobs'));
 }catch(e){error(e.message);}finally{state.busy=false;controls();}
}
function detail(id){
 const d=state.job?.details.find(d=>d.attempt_id===id);if(!d)return;
 $('#answer-detail').innerHTML=`<div class="field-label">SAVED NEW DEMO RESULT · ${esc(id)}</div><h2>${names[d.application]} / ${d.case_id} / repeat ${d.repeat}</h2>${pill(d.status)}${d.input_groups.map((g,i)=>g.map((p,j)=>`<div class="answer-pair"><b>${esc(p)}</b><p>${esc(d.captured_response_groups?.[i]?.[j]??'[No complete response captured]')}</p></div>`).join('')).join('')}`;
 $('#answer-dialog').showModal();
}
$('#start').onclick=start;
$('#readiness').onclick=()=>check().catch(e=>error(e.message));
$('#stop').onclick=async()=>{try{$('#stop').disabled=true;await api('/api/jobs/'+state.id+'/stop',{});await poll();state.mirror={state:'OFF'};camera();}catch(e){error(e.message);}};
$('#saved').onchange=e=>{if(e.target.value)select(e.target.value);};
for(const id of ['case','application','repeats'])$('#'+id).onchange=updatePlan;
for(const source of ['python','appium'])$('#'+source+'-tab').onclick=()=>{state.source=source;for(const name of ['python','appium']){$('#'+name+'-tab').classList.toggle('selected',name===source);$('#'+name+'-tab').setAttribute('aria-selected',name===source);}renderLogs();};
$('#model-button').onclick=()=>{$('#model-dialog').showModal();renderDefinition();};
$('#generate').onclick=async()=>{try{$('#generate').disabled=true;const result=await api('/api/generate',{});$('#generation-result').textContent=`Actual Python output: ${result.candidates} coordinates / ${result.executable} executable scenarios · ${result.elapsed_seconds}s · ${result.id}`;}catch(e){error(e.message);}finally{$('#generate').disabled=false;}};
$('#zoom').onclick=()=>{$('#frame-dialog').showModal();};
$('#fullscreen').onclick=()=>{(document.fullscreenElement?document.exitFullscreen():document.documentElement.requestFullscreen()).catch(e=>error(e.message));};
document.addEventListener('click',e=>{if(e.target.closest('.close'))e.target.closest('dialog').close();const target=e.target.closest('[data-attempt]');if(target)detail(target.dataset.attempt);});
async function init(){
 try{
  state.data=await api('/api/bootstrap');state.token=state.data.token;savedRuns(state.data.jobs);updatePlan();
  const active=state.data.jobs.find(j=>!terminal.has(j.state));
  if(active){select(active.id);await api('/api/mirror/start',{run_id:active.id});}
  setInterval(poll,500);setInterval(tail,350);setInterval(frame,200);setInterval(camera,200);
 }catch(e){error('Unable to connect to the local live demo: '+e.message);}
}
init();
