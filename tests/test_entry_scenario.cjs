const assert=require('node:assert/strict');
const {test}=require('node:test');
const {readFileSync}=require('node:fs');
const {Script}=require('node:vm');
const scenario=require('../entry_scenario.js');
const identity=[1,2,3,4,5,6];
const rates=[7,6,5.5,5,4.5,4];
test('identity entry: 120-position model gives a normalized, valid boat ticket top ten',()=>{
 const result=scenario.rank(rates,identity);
 assert.equal(result.tickets.length,10);
 assert.equal(new Set(result.tickets.map(x=>x.combo)).size,10);
 assert(result.tickets.every(x=>/^[1-6]-[1-6]-[1-6]$/.test(x.combo)&&new Set(x.combo.split('-')).size===3));
 assert(result.tickets.every((x,i,a)=>i===0||a[i-1].p>=x.p));
 assert.equal(result.forecast_usable,false);
 assert.equal(result.confidence_calibrated,false);
});
test('manual change changes course priors while preserving boat number on tickets',()=>{
 const before=scenario.rank(rates,identity);
 const after=scenario.rank(rates,[2,1,3,4,5,6]);
 assert.notDeepEqual(after.tickets.map(x=>x.combo),before.tickets.map(x=>x.combo));
 assert.equal(after.entry.join(''), '213456');
 assert.equal(after.validated,false);
});
test('six distinct boats required, all 6! entry permutations remain structurally valid',()=>{
 for(const bad of [[1,1,2,3,4,5],[1,2,3,4,5],[0,2,3,4,5,6],[1,2,3,4,5,7],[1,2,3,4,5,'6']]){
  assert.throws(()=>scenario.rank(rates,bad),/entry_must_be_six_unique_boats/);
 }
 assert.throws(()=>scenario.rank([1,2,3,4,5],identity),/invalid_six_national_rates/);
 assert.throws(()=>scenario.rank([1,2,3,4,5,NaN],identity),/invalid_six_national_rates/);
});
test('exact historical beta0.4 research-model identity weighting is preserved',()=>{
 const counts="59,60,36,28,51,31,48,24,34,29,21,15,24,19,19,12,3,4,10,9,21,17,11,8,12,11,9,3,9,5,4,7,4,5,1,4,1,1,1,2,13,19,12,12,11,8,2,2,8,4,4,3,6,7,4,2,2,2,2,1,7,8,8,6,2,10,1,5,7,4,5,5,7,3,6,4,6,4,2,6,4,1,6,7,6,3,2,1,6,1,0,5,7,5,3,1,4,5,1,0,2,4,1,2,3,1,1,0,2,0,1,2,1,3,1,2,3,0,1,0".split(',').map(Number);
 const combos=[];for(let a=1;a<=6;a++)for(let b=1;b<=6;b++)for(let c=1;c<=6;c++)if(a!==b&&a!==c&&b!==c)combos.push([a,b,c]);
 const W=Array.from({length:6},()=>0);combos.forEach((t,i)=>W[t[0]-1]+=counts[i]);
 const avg=rates.reduce((a,b)=>a+b)/6,ws=W.map((n,i)=>(n+12)*Math.exp(.4*(rates[i]-avg))),total=ws.reduce((a,b)=>a+b);
 const expected=combos.map((t,i)=>({combo:t.join('-'),p:100*ws[t[0]-1]/total*(counts[i]+.5)/(W[t[0]-1]+10)})).sort((a,b)=>b.p-a.p||a.combo.localeCompare(b.combo,'en')).slice(0,10);
 const actual=scenario.rank(rates,identity).tickets;
 assert.deepEqual(actual.map(x=>x.combo),expected.map(x=>x.combo));
 actual.forEach((x,i)=>assert(Math.abs(x.p-expected[i].p)<1e-10));
});
test('main page connects distinct source, user controls, never rewrites saved forecasts',()=>{
 const html=readFileSync('index.html','utf8');
 assert(html.includes('<script src="/entry_scenario.js"></script>'));
 for(const name of ['entryScenarioOrder','entryScenarioApply','entryScenarioReset','entryScenarioTickets','loadEntryScenario();','BoatEntryScenario.rank']){
  assert(html.includes(name),'missing '+name);
 }
 assert(html.includes('raw.source_audit?.actual_entry?.status'));
 assert(html.includes("raw.meta?.phase!=='PRE_RESULT'"));
 assert(html.includes('Date.now()>=state.deadline'));
 assert(html.includes('未検証'));
 assert(!readFileSync('entry_scenario.js','utf8').includes('fetch('));
 assert(readFileSync('server.py','utf8').includes('elif path == "/entry_scenario.js"'));
 const matches=[...html.matchAll(/<script>([\s\S]*?)<\/script>/g)];
 assert(matches.length>0,'inline script');
 matches.forEach(m=>new Script(m[1]));
});
