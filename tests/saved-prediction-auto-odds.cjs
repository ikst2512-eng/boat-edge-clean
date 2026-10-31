const {chromium,webkit}=require('playwright');
(async()=>{
 const engine=process.env.BROWSER_ENGINE==='webkit'?webkit:chromium;
 const browser=await engine.launch();
 try{
  const page=await browser.newPage({viewport:{width:390,height:844},isMobile:true,hasTouch:true});
  const archiveUrl='https://raw.githubusercontent.com/ikst2512-eng/boat-edge-clean/main/research_snapshots/202610310202.json';
  const saved=await (await page.request.get(archiveUrl)).json();
  if(saved.race_code!=='202610310202'||saved.predictions?.length!==10)throw Error('archive invalid');
  let apiCalls=0;
  const odds={};for(let a=1;a<=6;a++)for(let b=1;b<=6;b++)for(let c=1;c<=6;c++)if(new Set([a,b,c]).size===3)odds[[a,b,c].join('-')]=a*10+b+c/10;
  await page.route('**/api/odds?*',route=>{apiCalls++;return route.fulfill({status:200,contentType:'application/json',body:JSON.stringify({ok:true,odds,fetched_at:new Date().toISOString()})})});
  const response=await page.goto('https://boat-edge-clean.onrender.com/?date=2026-10-31&venue=2&race=2',{waitUntil:'domcontentloaded',timeout:60000});
  if(response.status()!==200)throw Error('site HTTP '+response.status());
  await page.waitForSelector('#predictionRows',{state:'attached',timeout:30000});
  await page.evaluate(()=>{setView('forecast');render()});
  await page.waitForFunction(()=>document.querySelectorAll('#predictionRows .prediction-row').length===10,{timeout:45000});
  await page.waitForFunction(()=>!!document.querySelector('#sourceMeta [data-live-odds]'),{timeout:45000});
  const rows=await page.locator('#predictionRows .prediction-row').evaluateAll(items=>items.map(e=>({ticket:e.querySelector('.prediction-ticket')?.textContent,value:e.querySelector('.prediction-odds')?.textContent})));
  if(apiCalls<1)throw Error('auto odds API not called');
  saved.predictions.forEach((ticket,i)=>{if(rows[i]?.ticket!==ticket)throw Error('saved order mismatch '+i);if(!rows[i].value.includes(odds[ticket].toLocaleString('ja-JP')+'倍'))throw Error('odds mismatch '+ticket)});
  const widths=await page.evaluate(()=>({page:document.documentElement.scrollWidth,viewport:innerWidth}));
  if(widths.page>widths.viewport+2)throw Error('mobile overflow '+JSON.stringify(widths));
  console.log('SAVED_RESEARCH_AUTO_ODDS_DOM_PASS',engine.name(),'10 exact tickets','apiCalls',apiCalls,'width',widths.page);
 }finally{await browser.close()}
})().catch(e=>{console.error(e);process.exit(1)});
