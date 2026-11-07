import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {plannedSlots, eligibleSlot, execute, WORKFLOWS} from '../cloudflare/independent_capture_wakeup.mjs';
const JST=9*60*60*1000;
const jst=(h,m,d=5)=>new Date(Date.UTC(2026,10,d,h,m)-JST);
const tick=(h,m,d=5)=>jst(h,m,d).getTime();
const fakeRun=(event,when,rest={})=>({id:101,event,head_branch:'main',status:'completed',conclusion:'success',created_at:when.toISOString(),...rest});
function mock({schedule=[],manual=[],failAt=0,failPost=false,postStatus=204}={}) {
  const calls=[];
  async function fetcher(url,options) {
    calls.push({url,method:options.method,body:options.body});
    if (failAt === calls.length) throw new Error('network_failure');
    if (options.method==='POST') return {status:failPost?403:postStatus};
    const rows=url.includes('event=workflow_dispatch')?manual:schedule;
    return {status:200,json:async()=>({workflow_runs:rows})};
  }
  return {calls,fetcher};
}
const run=(clock=tick(7,10),m=mock(),token='TEST_ONLY')=>execute({scheduledTime:clock,now:clock,token,fetcher:m.fetcher});
const noPosts=m=>assert.equal(m.calls.filter(c=>c.method==='POST').length,0);

test('CLEAN 63 and four-mode 56 actual daily slots',()=>{
  assert.equal(plannedSlots('clean',jst(12,0)).length,63);
  assert.equal(plannedSlots('four_mode',jst(12,0)).length,56);
  assert.equal(plannedSlots('clean',jst(12,0)).at(-1),tick(22,28));
  assert.equal(plannedSlots('four_mode',jst(12,0)).at(-1),tick(20,52));
});

test('single 5min UTC cron covers every slot once',()=>{
  const wrangler=readFileSync(new URL('../cloudflare/wrangler.toml',import.meta.url),'utf8');
  assert.match(wrangler,/crons = \["\*\/5 22-23,0-13 \* \* \*"\]/);
  for(const kind of Object.keys(WORKFLOWS))for(const slot of plannedSlots(kind,jst(12,0))){
    const ticks=[];
    for(let delta=1;delta<=8;delta++){
      const t=new Date(slot+delta*60_000); const h=t.getUTCHours();
      if(t.getUTCMinutes()%5===0&&(h>=22||h<=13)&&eligibleSlot(kind,t)===slot)ticks.push(t);
    }
    assert.equal(ticks.length,1,`${kind} ${new Date(slot).toISOString()} wakeup coverage`);
  }
});

test('source GitHub cron still matches plannedSlots and Render fallback',()=>{
  const yamlPaths={clean:'.github/workflows/clean-prospective.yml',four_mode:'.github/workflows/four-mode-prospective-capture.yml'};
  for(const [kind,path] of Object.entries(yamlPaths)){
    const y=readFileSync(new URL(`../${path}`,import.meta.url),'utf8');
    const expressions=[...y.matchAll(/^\s+- cron: '([^']+)'/gm)].map(x=>x[1]);
    assert.ok(expressions.length>0);
    const actual=new Set();
    const expand=x=>x.split(',').flatMap(t=>t.includes('-')?Array.from({length:+t.split('-')[1]-+t.split('-')[0]+1},(_,i)=>+t.split('-')[0]+i):[+t]);
    for(const expr of expressions){const [mins,hrs,day,month,dow]=expr.split(' ');assert.deepEqual([day,month,dow],['*','*','*']);
      for(const hour of expand(hrs))for(const minute of expand(mins))actual.add(`${(hour+9)%24}:${minute}`);
    }
    const expected=new Set(plannedSlots(kind,jst(12,0)).map(slot=>{const d=new Date(slot+JST);return `${d.getUTCHours()}:${d.getUTCMinutes()}`;}));
    assert.deepEqual(actual,expected);
  }
});

test('two eligible workflows dispatch only missing slots',async()=>{
  const m=mock();const out=await run(tick(7,10),m);
  assert.deepEqual(m.calls.map(x=>x.method),['GET','GET','GET','GET','POST','POST']);
  for(const name of Object.keys(WORKFLOWS)) assert.equal(out.workflows[name].action,'dispatch_accepted_not_forecast_proof');
  assert.ok(m.calls.filter(x=>x.method==='POST').every(x=>JSON.parse(x.body).ref==='main'));
  assert.equal(out.formal,false);assert.equal(out.new_forecast_saved_proven,false);
});

test('no network outside capture windows',async()=>{
  const m=mock();const out=await run(tick(22,55),m,undefined);assert.equal(out.action,'outside_recovery_windows_no_network');assert.equal(m.calls.length,0);
});

test('missing token is fail-closed',async()=>{const m=mock();await assert.rejects(()=>run(tick(7,10),m,''),/GITHUB_DISPATCH_TOKEN_required/);assert.equal(m.calls.length,0);});

test('four-mode ends 20:52, CLEAN continues 21:10',async()=>{
  const m=mock();const out=await run(tick(21,10),m);
  assert.equal(out.workflows.four_mode.action,'no_dispatch');assert.equal(m.calls.length,3);
});

test('special final CLEAN slot only 22:30 and never after 22:33',async()=>{
  assert.equal(eligibleSlot('clean',jst(22,30)),tick(22,28));
  assert.equal(eligibleSlot('clean',jst(22,33)),null);
  const m=mock();const out=await run(tick(22,30),m);assert.equal(out.workflows.clean.action,'dispatch_accepted_not_forecast_proof');
});

test('reject cron invocation outside configured UTC, wrong minute',async()=>{
  const m=mock();await assert.rejects(()=>execute({scheduledTime:tick(7,11),now:tick(7,11),token:'TEST',fetcher:m.fetcher}),/cron_outside_allowlist/);noPosts(m);
});

test('reject delayed trigger and future controller timestamp',async()=>{
  for(const lag of [-1000,91_000,5*60_000]){
    const m=mock();await assert.rejects(()=>execute({scheduledTime:tick(7,10),now:tick(7,10)+lag,token:'TEST',fetcher:m.fetcher}),/late_or_future_cron_trigger/);assert.equal(m.calls.length,0);
  }
});

test('direct successful, queued, in_progress, unknown block dispatch',async()=>{
  for(const [status,conclusion] of [['completed','success'],['queued',null],['in_progress',null],['completed',null]]){
    const m=mock({schedule:[fakeRun('schedule',jst(7,8),{status,conclusion})]});
    const out=await run(tick(7,10),m);assert.equal(out.workflows.four_mode.action,'no_dispatch');noPosts(m);
  }
});

test('failed scheduled run is recoverable but not publication proof',async()=>{
  const m=mock({schedule:[fakeRun('schedule',jst(7,8),{conclusion:'failure'})]});
  const out=await run(tick(7,10),m);assert.equal(out.workflows.four_mode.action,'dispatch_accepted_not_forecast_proof');assert.equal(out.on_time_cron_proven,false);
});

test('manual dispatch near slot blocks even when manual failed',async()=>{
  const m=mock({manual:[fakeRun('workflow_dispatch',jst(7,8),{conclusion:'failure'})]});
  const out=await run(tick(7,10),m);assert.equal(out.workflows.clean.reason,'previous_dispatch_or_active_job');noPosts(m);
});

test('an earlier active main run blocks, earlier success does not',async()=>{
  let m=mock({schedule:[fakeRun('schedule',jst(7,8),{status:'queued',conclusion:null})]});
  let out=await run(tick(7,25),m);assert.equal(out.workflows.four_mode.reason,'previous_dispatch_or_active_job');noPosts(m);
  m=mock({schedule:[fakeRun('schedule',jst(7,8))]});out=await run(tick(7,25),m);
  assert.equal(out.workflows.four_mode.action,'dispatch_accepted_not_forecast_proof');
});

test('nonmain cannot masquerade as successful main run',async()=>{
  const m=mock({schedule:[fakeRun('schedule',jst(7,8),{head_branch:'feature/other'})]});const out=await run(tick(7,10),m);
  assert.equal(out.workflows.four_mode.action,'dispatch_accepted_not_forecast_proof');
});

test('malformed GitHub history fails closed',async()=>{
  for(const change of [{id:'123'},{head_branch:null},{created_at:'invalid'},{event:'push'},{status:null}]){
    const m=mock({schedule:[fakeRun('schedule',jst(7,8),change)]});
    await assert.rejects(()=>run(tick(7,10),m));noPosts(m);
  }
});

test('full first page cannot hide recent main run',async()=>{
  const rows=Array.from({length:100},(_,i)=>fakeRun('schedule',jst(7,8),{id:i+1}));
  const m=mock({schedule:rows});await assert.rejects(()=>run(tick(7,10),m),/pagination_incomplete/);noPosts(m);
});

test('second workflow GET failure prevents partial POST',async()=>{
  const m=mock({failAt:3});await assert.rejects(()=>run(tick(7,10),m),/network_failure/);noPosts(m);
});

test('non-200 history fails before POST',async()=>{
  const m=mock();m.fetcher=async (url,opts)=>{m.calls.push({url,method:opts.method});return {status:503};};
  await assert.rejects(()=>run(tick(7,10),m),/github_history_http_error/);noPosts(m);
});

test('POST must return 204; no false success',async()=>{
  const m=mock({postStatus:200});await assert.rejects(()=>run(tick(7,10),m),/dispatch_not_accepted/);
});
