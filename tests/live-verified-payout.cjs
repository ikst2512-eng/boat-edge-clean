const {chromium}=require('playwright');
(async()=>{
 const browser=await chromium.launch({headless:true});
 try{
  const page=await browser.newPage({viewport:{width:390,height:844}});
  const errors=[];page.on('pageerror',e=>errors.push(e.message));
  const site='https://ikst2512-eng.github.io/boat-edge-clean/';
  const response=await page.goto(site,{waitUntil:'domcontentloaded',timeout:45000});
  if(!response?.ok())throw Error('PUBLIC_SITE_HTTP '+response?.status());
  const code='202610282312';
  const archiveResponse=await page.request.get('https://raw.githubusercontent.com/ikst2512-eng/boat-edge-clean/main/four_mode_performance/verified_races/'+code+'.json');
  if(!archiveResponse.ok())throw Error('VERIFIED_ARCHIVE_UNAVAILABLE');
  const record=await archiveResponse.json();
  if(record.schema!=='CLEAN_VERIFIED_FOUR_MODE_RACE_V1'||record.verified!==true||record.official_finish!=='1-4-5'||record.official_payout_yen_per_100!==1270||record.modes.hit?.hit!==true)throw Error('BASELINE_INVALID');
  await page.evaluate(()=>{datePinned=true;venueTouched=true;s.date='2026-10-28';s.venue=22;s.race=12;setView('review');render();});
  await page.waitForFunction(()=>document.getElementById('reviewStatus')?.textContent?.includes('照合済み'),{timeout:45000});
  const display=await page.evaluate(()=>({
   status:document.getElementById('reviewStatus').textContent,
   metrics:document.getElementById('reviewMetrics').textContent,
   reason:document.getElementById('reviewReason').textContent
  }));
  if(!display.metrics.includes('1-4-5')||!display.metrics.includes('1,270円')||!display.metrics.includes(record.modes.hit.return_yen.toLocaleString('ja-JP')+'円')||!display.metrics.includes('本命'))throw Error('VERIFIED_PAYOUT_DISPLAY_MISMATCH '+JSON.stringify(display));
  if(errors.length)throw Error('PAGE_JS_ERRORS '+errors.join(' | '));
  console.log('PASS: 2026-10-28 Karatsu 12R publicly shows verified 1-4-5 and 1,270 yen official payout; original four-mode hit return '+record.modes.hit.return_yen+' yen.');
 }finally{await browser.close()}
})().catch(e=>{console.error(e);process.exitCode=1});
