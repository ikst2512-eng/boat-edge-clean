const {chromium}=require('playwright');
(async()=>{
 const browser=await chromium.launch({headless:true});
 try{
  const page=await browser.newPage({viewport:{width:390,height:844}});
  const errors=[];
  page.on('pageerror',e=>errors.push(e.message));
  const site='https://ikst2512-eng.github.io/boat-edge-clean/';
  const response=await page.goto(site,{waitUntil:'domcontentloaded',timeout:45000});
  if(!response?.ok())throw Error('PUBLIC_SITE_UNAVAILABLE '+response?.status());
  const race='202610230401';
  const source=await page.request.get('https://raw.githubusercontent.com/ikst2512-eng/boat-edge-clean/main/research_snapshots/'+race+'.json',{timeout:20000});
  if(!source.ok())throw Error('ARCHIVE_NOT_AVAILABLE '+source.status());
  const saved=await source.json();
  if(saved.race_code!==race||saved.status!=='research'||saved.validated!==false||saved.predictions?.length!==10)
   throw Error('UNVERIFIED_ARCHIVE');
  await page.evaluate(()=>{
   datePinned=true;venueTouched=true;
   s.date='2026-10-23';s.venue=3;s.race=1;
   setView('forecast');render();
  });
  await page.waitForFunction(()=>document.querySelectorAll('#predictionRows .prediction-row').length===10,{timeout:30000});
  const shown=await page.evaluate(()=>({
   tickets:predictionTickets.slice(),
   status:document.getElementById('predictionStatus').textContent,
   visible:!document.getElementById('forecast').hidden
  }));
  if(!shown.visible||JSON.stringify(shown.tickets)!==JSON.stringify(saved.predictions))
   throw Error('DISPLAY_ARCHIVE_MISMATCH '+JSON.stringify(shown));
  if(errors.length)throw Error('PAGE_JS_ERRORS '+errors.join('|'));
  console.log('PASS: Published 20261023 04 1R research forecast shows ten exact saved tickets; no reconstructed forecast.');
 }finally{await browser.close()}
})().catch(e=>{console.error(e);process.exitCode=1});
