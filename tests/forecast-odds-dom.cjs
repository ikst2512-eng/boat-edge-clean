const {chromium}=require('playwright');
const assert=require('node:assert/strict');
(async()=>{
 const browser=await chromium.launch();
 try{
  const page=await browser.newPage({viewport:{width:390,height:844},isMobile:true,hasTouch:true});
  let ready=false;
  for(let attempt=1;attempt<=3;attempt++){
   const response=await page.goto('https://boat-edge-clean.onrender.com/?date=2026-10-31&venue=2&race=1',{waitUntil:'domcontentloaded',timeout:60000});
   console.log('Attempt',attempt,'HTTP',response.status(),'title',await page.title());
   try{await page.waitForSelector('#forecast',{timeout:15000});ready=true;break}catch(e){console.log('Missing forecast on attempt',attempt,'HTML length',(await page.content()).length)}
  }
  assert.ok(ready,'public page did not render forecast after retries');
  const data=await page.evaluate(async()=>{
   const tickets=['6-5-4','1-3-2','2-1-6','4-3-1','1-2-3','3-5-6','2-3-1','5-4-6','6-1-2','3-1-4'];
   const odds={};
   for(let a=1;a<=6;a++)for(let b=1;b<=6;b++)for(let c=1;c<=6;c++)if(new Set([a,b,c]).size===3)odds[[a,b,c].join('-')]=a*100+b*10+c;
   s.date='2026-10-31';s.venue=1;s.race=1;
   setView('forecast');
   predictionModes.research={tickets,probabilities:{},odds:{}};
   selectedPredictionMode='research';applyPredictionMode();
   window.predictionRequestId=(window.predictionRequestId||0)+1;
   const token=window.predictionRequestId;
   const originalFetch=window.fetch;
   window.fetch=async url=>String(url).includes('/api/odds?')?new Response(JSON.stringify({ok:true,odds,fetched_at:new Date().toISOString()}),{status:200,headers:{'Content-Type':'application/json'}}):originalFetch(url);
   try{await loadTicketOdds(sameRaceKey(),token)}finally{window.fetch=originalFetch}
   return {expected:tickets.map(ticket=>({ticket,odds:odds[ticket]})),actual:[...document.querySelectorAll('#predictionRows .prediction-row')].map(row=>({ticket:row.querySelector('.prediction-ticket')?.textContent,odds:row.querySelector('.prediction-odds')?.textContent})),stamp:document.querySelector('#sourceMeta [data-live-odds]')?.textContent,width:document.documentElement.scrollWidth,viewport:innerWidth};
  });
  assert.equal(data.actual.length,10);
  assert.deepEqual(data.actual.map(x=>x.ticket),data.expected.map(x=>x.ticket));
  for(let i=0;i<10;i++)assert.ok(data.actual[i].odds.includes(data.expected[i].odds.toLocaleString('ja-JP')+'倍'),JSON.stringify(data.actual[i]));
  assert.ok(data.stamp?.includes('公式3連単オッズ'));
  assert.ok(data.width<=data.viewport+2,JSON.stringify(data));
  console.log('Forecast DOM 10 tickets matched exact injected 120-odds fixture, unchanged rank, timestamp, mobile width PASS');
 }finally{await browser.close()}
})().catch(e=>{console.error(e);process.exit(1)});
