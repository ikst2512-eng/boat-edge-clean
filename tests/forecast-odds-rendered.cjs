const {chromium}=require('playwright');const assert=require('node:assert/strict');
(async()=>{const b=await chromium.launch();try{
const p=await b.newPage({viewport:{width:390,height:844},isMobile:true,hasTouch:true});
await p.goto('https://boat-edge-clean.onrender.com/?date=2026-10-31&venue=2&race=1',{waitUntil:'domcontentloaded',timeout:60000});
await p.waitForSelector('#forecast',{state:'attached',timeout:30000});
const result=await p.evaluate(()=>{
const tickets=['6-5-4','1-3-2','2-1-6','4-3-1','1-2-3','3-5-6','2-3-1','5-4-6','6-1-2','3-1-4'];
const all={};for(let a=1;a<=6;a++)for(let b=1;b<=6;b++)for(let c=1;c<=6;c++)if(new Set([a,b,c]).size===3)all[a+'-'+b+'-'+c]=a*100+b*10+c;
predictionModes.research={tickets,odds:{},probabilities:{}};selectedPredictionMode='research';selectedTop=10;applyPredictionMode();
const current=predictionModes.research;current.odds=Object.fromEntries(current.tickets.map(t=>[t,all[t]]));predictionOdds=current.odds;drawPredictions();
return {expected:tickets.map(t=>({ticket:t,odds:all[t]})),actual:[...document.querySelectorAll('#predictionRows .prediction-row')].map(r=>({ticket:r.querySelector('.prediction-ticket')?.textContent,odds:r.querySelector('.prediction-odds')?.textContent})),width:document.documentElement.scrollWidth,viewport:innerWidth};
});
assert.equal(result.actual.length,10);assert.deepEqual(result.actual.map(x=>x.ticket),result.expected.map(x=>x.ticket));
for(let i=0;i<10;i++)assert.ok(result.actual[i].odds.includes(result.expected[i].odds+'倍'),JSON.stringify(result.actual[i]));
assert.ok(result.width<=result.viewport+2,JSON.stringify(result));
console.log('Rendered odds/tickets match and mobile viewport PASS');
}finally{await b.close()}})().catch(e=>{console.error(e);process.exitCode=1});