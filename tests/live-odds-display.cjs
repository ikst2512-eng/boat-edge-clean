const {chromium}=require('playwright');
(async()=>{
 const browser=await chromium.launch({headless:true});
 try{
  const page=await browser.newPage({viewport:{width:390,height:844}});
  const code='202610310202', tickets=['1-2-4','1-2-3','1-3-2','1-3-5','1-2-5','1-4-2','1-3-4','1-4-3','1-2-6','1-3-6'];
  const odds={};
  for(let a=1;a<=6;a++)for(let b=1;b<=6;b++)for(let c=1;c<=6;c++)if(a!==b&&a!==c&&b!==c)odds[a+'-'+b+'-'+c]=12.5;
  await page.route('**/api/odds?**',route=>route.fulfill({status:200,contentType:'application/json',body:JSON.stringify({ok:true,odds,fetched_at:new Date().toISOString()})}));
  const res=await page.goto('https://ikst2512-eng.github.io/boat-edge-clean/',{waitUntil:'domcontentloaded',timeout:45000});
  if(!res?.ok())throw Error('PAGES_HTTP_'+res?.status());
  await page.evaluate(()=>{datePinned=true;venueTouched=true;s.date='2026-10-31';s.venue=1;s.race=2;setView('forecast');render()});
  await page.waitForFunction(()=>displayedPredictionKey==='20261031-02-02'&&predictionTickets.length===10,null,{timeout:35000});
  const before=await page.evaluate(()=>predictionTickets.slice());
  if(before.length!==10)throw Error('SAVED_FORECAST_UNAVAILABLE');
  const token=await page.evaluate(()=>window.predictionRequestId);
  await page.evaluate(token=>loadTicketOdds(sameRaceKey(),token),token);
  await page.waitForFunction(()=>[...document.querySelectorAll('#predictionRows .prediction-odds')].length===10&&
     [...document.querySelectorAll('#predictionRows .prediction-odds')].every(x=>x.textContent.includes('取得済オッズ 12.5倍')),null,{timeout:12000});
  const after=await page.evaluate(()=>predictionTickets.slice());
  if(JSON.stringify(after)!==JSON.stringify(before))throw Error('ODDS_REORDERED_SAVED_TICKETS');
  console.log('PASS_PUBLIC_ODDS_DOM_10_TICKETS_MOCKED_120_COMBINATIONS '+code);
 }finally{await browser.close()}
})().catch(e=>{console.error(e);process.exitCode=1});
