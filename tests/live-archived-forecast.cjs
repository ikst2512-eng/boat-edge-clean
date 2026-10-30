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
  // Confirm the actual October 30 schedule is reflected in the venue picker.
  const scheduleResponse=await page.request.get('https://raw.githubusercontent.com/ikst2512-eng/boat-edge-clean/main/schedule_snapshots/20261030.json',{timeout:20000});
  if(!scheduleResponse.ok())throw Error('TODAY_SCHEDULE_NOT_PUBLISHED '+scheduleResponse.status());
  const schedule=await scheduleResponse.json();
  const expectedVenues=schedule.venues.map(v=>v.jcd).sort();
  const expectedRaceCount=schedule.venues.reduce((n,v)=>n+v.races.length,0);
  if(schedule.date!=='2026-10-30'||expectedVenues.length!==12||expectedRaceCount!==144)throw Error('TODAY_SCHEDULE_INVALID');
  const visibleSchedule=await page.evaluate(async()=>{
   datePinned=true;s.date='2026-10-30';
   await loadHeldVenues(true);
   return {date:todayVenueRaces?.date,venues:todayVenueRaces?.venues.map(v=>v.jcd).sort(),raceCount:todayVenueRaces?.venues.reduce((n,v)=>n+v.races.length,0),status:document.getElementById('venueState').textContent};
  });
  if(visibleSchedule.date!=='2026-10-30'||JSON.stringify(visibleSchedule.venues)!==JSON.stringify(expectedVenues)||visibleSchedule.raceCount!==expectedRaceCount||visibleSchedule.status.includes('取得できません'))
   throw Error('PUBLIC_SCHEDULE_DISPLAY_MISMATCH '+JSON.stringify(visibleSchedule));
  console.log('PASS: 2026-10-30 published venue schedule shows 12 venues / 144 races');
  const race='202610300101';
  const source=await page.request.get('https://raw.githubusercontent.com/ikst2512-eng/boat-edge-clean/main/research_snapshots/'+race+'.json',{timeout:20000});
  if(!source.ok())throw Error('ARCHIVE_NOT_AVAILABLE '+source.status());
  const saved=await source.json();
  if(saved.race_code!==race||saved.status!=='research'||saved.validated!==false||saved.predictions?.length!==10)
   throw Error('UNVERIFIED_ARCHIVE');
  await page.evaluate(()=>{
   datePinned=true;venueTouched=true;
   s.date='2026-10-30';s.venue=0;s.race=1;
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
  const additional=[{race:'202610300102',venue:0},{race:'202610300701',venue:6}];
  for(const item of additional){
   const archived=await page.request.get('https://raw.githubusercontent.com/ikst2512-eng/boat-edge-clean/main/research_snapshots/'+item.race+'.json',{timeout:20000});
   if(!archived.ok())throw Error('SECONDARY_ARCHIVE_MISSING '+item.race+' '+archived.status());
   const record=await archived.json();
   if(record.race_code!==item.race||record.status!=='research'||record.predictions?.length!==10)throw Error('SECONDARY_ARCHIVE_INVALID '+item.race);
   await page.evaluate(v=>{s.venue=v.venue;s.race=v.race;setView('forecast');render();},{venue:item.venue,race:Number(item.race.slice(10))});
   await page.waitForFunction(expected=>displayedPredictionKey===expected&&predictionTickets.length===10,item.race.slice(0,8)+'-'+item.race.slice(8,10)+'-'+item.race.slice(10),{timeout:35000});
   const tickets=await page.evaluate(()=>predictionTickets.slice());
   if(JSON.stringify(tickets)!==JSON.stringify(record.predictions))throw Error('SECONDARY_DISPLAY_MISMATCH '+item.race);
   console.log('PASS: race switch displays exact saved forecast '+item.race);
  }
  // Today's finished races must show actual saved results beside saved forecasts.
  const settledCode='202610300301';
  const confirmedResp=await page.request.get('https://raw.githubusercontent.com/ikst2512-eng/boat-edge-clean/main/confirmed_results/'+settledCode+'.json',{timeout:20000});
  if(!confirmedResp.ok())throw Error('CONFIRMED_RESULT_MISSING '+confirmedResp.status());
  const confirmed=await confirmedResp.json();
  if(confirmed.race_code!==settledCode||confirmed.status!=='confirmed')throw Error('CONFIRMED_RESULT_INVALID');
  await page.evaluate(()=>{s.date='2026-10-30';s.venue=2;s.race=1;setView('forecast');render()});
  await page.waitForFunction(()=>document.getElementById('forecastResultStatus').textContent==='CLEAN保存済み確定結果',{timeout:35000});
  await page.waitForFunction(()=>displayedPredictionKey==='20261030-03-01'&&predictionTickets.length===10,{timeout:30000});
  const visible=await page.evaluate(()=>({text:document.getElementById('forecastResultDetail').textContent,predictions:predictionTickets.slice()}));
  if(!visible.text.includes(confirmed.finish_order.join(' - '))||visible.predictions.length!==10)throw Error('FORECAST_RESULT_NOT_VISIBLE '+JSON.stringify(visible));
  // Verify repeated same-race refresh never blanks already validated views.
  await page.evaluate(()=>{loadPredictions(true);loadForecastResult();});
  const refreshState=await page.evaluate(()=>({
   tickets:predictionTickets.slice(),result:document.getElementById('forecastResultDetail').textContent,
   status:document.getElementById('forecastResultStatus').textContent
  }));
  if(JSON.stringify(refreshState.tickets)!==JSON.stringify(visible.predictions)||!refreshState.result.includes(confirmed.finish_order.join(' - ')))
   throw Error('SAME_RACE_REFRESH_BLANKED_VIEW '+JSON.stringify(refreshState));
  await page.waitForFunction(()=>document.getElementById('forecastResultStatus').textContent==='CLEAN保存済み確定結果',{timeout:35000});
  console.log('PASS: Oct 30 venue 03 race 1 both confirmed result and saved 10 predictions visible');
  for(const target of [{code:'202610300302',venue:2,race:2},{code:'202610300602',venue:5,race:2}]){
   const base='https://raw.githubusercontent.com/ikst2512-eng/boat-edge-clean/main/';
   const [pr,rr]=await Promise.all([page.request.get(base+'prospective_predictions/'+target.code+'.json'),page.request.get(base+'confirmed_results/'+target.code+'.json')]);
   if(!pr.ok()||!rr.ok())throw Error('RACE_SOURCES_MISSING '+target.code);
   const [forecast,result]=await Promise.all([pr.json(),rr.json()]);
   await page.evaluate(item=>{s.venue=item.venue;s.race=item.race;setView('forecast');render();},target);
   await page.waitForFunction(code=>displayedPredictionKey===code.slice(0,8)+'-'+code.slice(8,10)+'-'+code.slice(10)&&predictionTickets.length===10,target.code,{timeout:35000});
   await page.waitForFunction(()=>document.getElementById('forecastResultStatus').textContent==='CLEAN保存済み確定結果',{timeout:35000});
   const data=await page.evaluate(()=>({tickets:predictionTickets.slice(),result:document.getElementById('forecastResultDetail').textContent}));
   if(JSON.stringify(data.tickets)!==JSON.stringify(forecast.predictions)||!data.result.includes(result.finish_order.join(' - ')))throw Error('CROSS_VENUE_FORECAST_RESULT_MISMATCH '+target.code);
   console.log('PASS: cross-venue forecast and result '+target.code);
  }
  // The selected venue's complete result list must include 12 distinct race rows.
  await page.waitForFunction(()=>document.querySelectorAll('#resultList .clean-race-card').length===12,{timeout:35000});
  const list=await page.evaluate(()=>[...document.querySelectorAll('#resultList .clean-race-card')].map(node=>({
    race:node.querySelector('.clean-race-head strong')?.textContent,
    status:node.querySelector('.clean-race-state')?.textContent
  })));
  if(list.length!==12||list.some((item,i)=>item.race!==(i+1)+'R'))throw Error('RESULT_LIST_RACE_ORDER_INVALID '+JSON.stringify(list));
  console.log('PASS: published venue 06 result list has 12 ordered race cards');
  // A new venue selection must immediately expose twelve navigable placeholders
  // while independent result/payout requests are still in flight.
  await page.evaluate(()=>{s.venue=0;s.race=1;setView('forecast');render();});
  const initialRows=await page.evaluate(()=>[...document.querySelectorAll('#resultList .clean-race-card')].map(node=>({
   name:node.querySelector('.clean-race-head strong')?.textContent,
   actions:node.querySelectorAll('.clean-race-actions button').length
  })));
  if(initialRows.length!==12||initialRows.some((v,i)=>v.name!==(i+1)+'R'||v.actions<4))
   throw Error('RESULTS_BLANK_DURING_FETCH '+JSON.stringify(initialRows));
  console.log('PASS: 12 navigable result rows visible immediately on venue switch');
  // Independently verify all 12 completed races for two different venues.
  for(const venue of [0,2]){
   await page.evaluate(v=>{s.venue=v;s.race=1;setView('forecast');render();},venue);
   await page.waitForFunction(v=>document.querySelectorAll('#resultList .clean-race-card').length===12&&document.getElementById('resultListStatus').textContent.includes(names[v]+'｜')&&document.getElementById('resultListStatus').textContent.includes('結果確定 12/12R'),venue,{timeout:45000});
   const states=await page.evaluate(()=>[...document.querySelectorAll('#resultList .clean-race-card')].map((node,i)=>({
     race:node.querySelector('.clean-race-head strong')?.textContent,
     state:node.querySelector('.clean-race-state')?.textContent
   })));
   if(states.length!==12||states.some((v,i)=>v.race!==(i+1)+'R'||v.state!=='結果確定'))
    throw Error('CONFIRMED_LIST_MISMATCH_VENUE_'+(venue+1)+' '+JSON.stringify(states));
   console.log('PASS: venue '+(venue+1)+' all twelve results confirmed');
  }
  if(errors.length)throw Error('PAGE_JS_ERRORS '+errors.join('|'));
  console.log('PASS: Published 20261030 01 1R research forecast shows ten exact saved tickets; no reconstructed forecast.');
 }finally{await browser.close()}
})().catch(e=>{console.error(e);process.exitCode=1});
