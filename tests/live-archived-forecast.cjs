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
  // Confirm a newer October 31 research snapshot is not hidden by old-day UI.
  const currentCode='202610310202';
  const currentResponse=await page.request.get('https://raw.githubusercontent.com/ikst2512-eng/boat-edge-clean/main/research_snapshots/'+currentCode+'.json',{timeout:20000});
  if(!currentResponse.ok())throw Error('OCT31_RESEARCH_SNAPSHOT_MISSING '+currentResponse.status());
  const current=await currentResponse.json();
  if(current.race_code!==currentCode||current.status!=='research'||current.validated!==false||
     current.predictions?.length!==10)throw Error('OCT31_RESEARCH_SNAPSHOT_INVALID');
  await page.evaluate(()=>{
   datePinned=true;venueTouched=true;s.date='2026-10-31';s.venue=1;s.race=2;
   setView('forecast');render();
  });
  await page.waitForFunction(()=>displayedPredictionKey==='20261031-02-02'&&
      predictionTickets.length===10,null,{timeout:35000});
  const currentShown=await page.evaluate(()=>({
   tickets:predictionTickets.slice(),
   visible:!document.getElementById('forecast').hidden,
   status:document.getElementById('predictionStatus').textContent
  }));
  if(!currentShown.visible||JSON.stringify(currentShown.tickets)!==JSON.stringify(current.predictions))
   throw Error('OCT31_RESEARCH_FORECAST_DISPLAY_MISMATCH '+JSON.stringify(currentShown));
  console.log('PASS: 2026-10-31 race 02-02 research Top10 matches publicly displayed forecast');
  // Exercise the actual public UI with a full 120-combination API fixture.
  // This checks rendering and immutable ticket order, NOT live upstream availability.
  const allOdds={};
  for(let a=1;a<=6;a++)for(let b=1;b<=6;b++)for(let c=1;c<=6;c++){
   if(a!==b&&a!==c&&b!==c)allOdds[a+'-'+b+'-'+c]=12.5;
  }
  await page.route('**/api/odds?**',route=>route.fulfill({
   status:200,contentType:'application/json',
   body:JSON.stringify({ok:true,odds:allOdds,fetched_at:new Date().toISOString()})
  }));
  await page.evaluate(()=>loadTicketOdds(sameRaceKey(),window.predictionRequestId));
  await page.waitForFunction(()=>document.querySelectorAll('#predictionRows .prediction-odds small').length>=20 &&
   [...document.querySelectorAll('#predictionRows .prediction-odds')].every(el=>el.textContent.includes('取得済オッズ 12.5倍')),
   null,{timeout:15000});
  const afterOdds=await page.evaluate(()=>predictionTickets.slice());
  if(JSON.stringify(afterOdds)!==JSON.stringify(current.predictions))
   throw Error('OFFICIAL_ODDS_CHANGED_TICKET_ORDER');
  console.log('PASS: mock full-120 odds payload renders 10 ticket odds in published DOM without changing ranks');

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
  // Verify the linked per-race finish appears on the selected race card.
  await page.evaluate(()=>{s.venue=2;s.race=1;setView('forecast');render();});
  await page.waitForFunction(()=>document.getElementById('resultListStatus').textContent.includes('結果確定 12/12R'),{timeout:45000});
  const linked=await page.evaluate(()=>({
   first:document.querySelector('#resultList .clean-race-card .clean-inline-finish')?.textContent,
   count:document.querySelectorAll('#resultList .clean-race-card .clean-inline-finish').length
  }));
  if(linked.count!==12||!linked.first?.includes('2 - 3 - 1'))throw Error('RACE_CARD_FINISH_NOT_LINKED '+JSON.stringify(linked));
  console.log('PASS: every completed race displays its confirmed finish on the same race card');
  // End-to-end date-wide review: all scheduled races are visible, and a row opens its own race.
  await page.evaluate(()=>{datePinned=true;s.date='2026-10-30';setView('review');render();});
  await page.locator('#dailyReviewDate').fill('2026-10-30');
  await page.locator('#dailyReviewReload').click();
  await page.waitForFunction(()=>document.querySelectorAll('#dailyReviewRows .daily-review-row').length===144,{timeout:45000});
  await page.waitForFunction(()=>document.getElementById('dailyReviewSummary').textContent.includes('確認 144/144R'),{timeout:90000});
  const review=await page.evaluate(()=>({rows:document.querySelectorAll('#dailyReviewRows .daily-review-row').length,summary:document.getElementById('dailyReviewSummary').textContent,first:document.querySelector('#dailyReviewRows .daily-review-row')?.textContent}));
  if(review.rows!==144||!review.summary.includes('対象 144R'))throw Error('DAILY_REVIEW_INCOMPLETE '+JSON.stringify(review));
  const firstVenue=page.locator('#dailyReviewRows details.daily-review-venue').first();
  await firstVenue.locator('summary').click();
  await firstVenue.locator('.daily-review-row').first().click();
  const selected=await page.evaluate(()=>({view:activeView,key:sameRaceKey()}));
  if(selected.view!=='forecast'||selected.key!=='20261030-01-01')throw Error('DAILY_REVIEW_LINK_BROKEN '+JSON.stringify(selected));
  console.log('PASS: Daily 10/30 review displays all 144 races and opens selected race');
  // Public stylesheet and review venue groups must respect the requested palette.
  await page.evaluate(()=>{setView('review');render()});
  await page.waitForFunction(()=>document.querySelectorAll('#dailyReviewRows details.daily-review-venue').length===12,{timeout:45000});
  const theme=await page.evaluate(()=>({
   background:getComputedStyle(document.body).backgroundColor,
   header:getComputedStyle(document.querySelector('header')).backgroundColor,
   important:getComputedStyle(document.getElementById('dailyReviewSummary')).borderTopColor,
   venues:document.querySelectorAll('#dailyReviewRows details.daily-review-venue').length,
   reviewFocused:document.body.classList.contains('review-focused')
  }));
  if(theme.background!=='rgb(255, 255, 255)'||theme.header!=='rgb(234, 246, 255)'||theme.important!=='rgb(187, 38, 56)'||theme.venues!==12||!theme.reviewFocused)
   throw Error('PUBLIC_THEME_OR_REVIEW_MISMATCH '+JSON.stringify(theme));
  console.log('PASS: live white/pale-blue/red theme and 12 grouped review venues');
  // Verify the selected race's result and saved tickets share one panel in production.
  await page.evaluate(()=>{s.date='2026-10-30';s.venue=2;s.race=1;setView('forecast');render()});
  await page.waitForFunction(()=>document.getElementById('forecastResultStatus').textContent==='CLEAN保存済み確定結果'&&predictionTickets.length===10,{timeout:35000});
  const combined=await page.evaluate(()=>({
   hasPanel:!!document.querySelector('#forecast .forecast-combined-race'),
   result:document.querySelector('#forecast .forecast-combined-race #forecastResultDetail')?.textContent,
   ticketCount:document.querySelectorAll('#forecast .forecast-combined-race #predictionRows .prediction-row').length,
   border:getComputedStyle(document.querySelector('#forecast .forecast-combined-race .forecast-result-preview')).borderTopColor
  }));
  if(!combined.hasPanel||!combined.result?.includes('2 - 3 - 1')||combined.ticketCount!==10||combined.border!=='rgb(187, 38, 56)')
   throw Error('COMBINED_FORECAST_RESULT_LAYOUT_BROKEN '+JSON.stringify(combined));
  console.log('PASS: published race forecast and confirmed result share one panel');
  // Verify a real, newly archived 2026-10-31 forecast is visible through the published UI.
  await page.evaluate(()=>{s.date='2026-10-31';s.venue=23;s.race=1;datePinned=true;venueTouched=true;setView('forecast');render()});
  await page.waitForFunction(()=>displayedPredictionKey==='20261031-24-01'&&predictionTickets.length===10,{timeout:45000});
  const live31=await page.evaluate(()=>({key:displayedPredictionKey,tickets:predictionTickets.slice(),status:document.getElementById('predictionStatus').textContent}));
  if(live31.tickets.length!==10||!live31.status.includes('研究予想'))throw Error('OCT31_FORECAST_NOT_VISIBLE '+JSON.stringify(live31));
  console.log('PASS: 2026-10-31 actual stored ten-ticket research prediction appears in published forecast');
  // Public UX contract: the forecast is first, only one venue selector is visible,
  // and the home page has no back button.
  await page.evaluate(()=>{setView('forecast');render()});
  const forecastUi=await page.evaluate(()=>{
    const root=document.getElementById('forecast');
    const forecast=root.querySelector('.forecast-combined-race');
    const list=root.querySelector('.forecast-race-list');
    const preview=root.querySelector('.forecast-inline-preview');
    const venue=document.getElementById('forecastVenue');
    return {first:root.firstElementChild===forecast||root.children[1]===forecast,forecastBeforeList:!!(forecast.compareDocumentPosition(list)&Node.DOCUMENT_POSITION_FOLLOWING),forecastBeforePreview:!!(forecast.compareDocumentPosition(preview)&Node.DOCUMENT_POSITION_FOLLOWING),selectorVisible:!!venue&&getComputedStyle(venue).display!=='none',duplicateVenueVisible:getComputedStyle(root.querySelector('.result-venue-picker')).display!=='none'}
  });
  if(!forecastUi.first||!forecastUi.forecastBeforeList||!forecastUi.forecastBeforePreview||!forecastUi.selectorVisible||forecastUi.duplicateVenueVisible)throw Error('FORECAST_NOT_FIRST_OR_DUPLICATE_VENUE '+JSON.stringify(forecastUi));
  const tabUi=await page.evaluate(()=>{
    const root=document.getElementById('forecast');
    const tab=p=>root.querySelector('[data-forecast-pane="'+p+'"]');
    if(!tab('result'))return {legacyPublishedPage:true};
    const state=()=>({prediction:!root.querySelector('.forecast-combined-race').hidden,result:!root.querySelector('.forecast-result-tab').hidden,exhibition:!root.querySelector('.forecast-inline-preview').hidden,races:!root.querySelector('.forecast-race-list').hidden});
    const first=state();tab('result').click();const second=state();tab('exhibition').click();const third=state();tab('races').click();const fourth=state();tab('prediction').click();
    return {first,second,third,fourth,homeDeadline:document.querySelector('[data-home-only] #deadlineSection')!==null}
  });
  if(!tabUi.legacyPublishedPage&&(!tabUi.homeDeadline||!tabUi.first.prediction||tabUi.first.result||!tabUi.second.result||tabUi.second.prediction||!tabUi.third.exhibition||tabUi.third.result||!tabUi.fourth.races||tabUi.fourth.prediction))throw Error('FORECAST_TABS_NOT_EXCLUSIVE '+JSON.stringify(tabUi));
  await page.evaluate(()=>{setView('home');render()});
  const homeUi=await page.evaluate(()=>({back:!document.getElementById('raceBrowserToolbar').hidden,home:!document.querySelector('[data-home-only]').hidden}));
  if(homeUi.back||!homeUi.home)throw Error('HOME_BACK_STILL_VISIBLE '+JSON.stringify(homeUi));
  console.log('PASS: Public forecast first, one visible venue selector and home with no back button');
  if(errors.length)throw Error('PAGE_JS_ERRORS '+errors.join('|'));
  console.log('PASS: Published 20261030 01 1R research forecast shows ten exact saved tickets; no reconstructed forecast.');
 }finally{await browser.close()}
})().catch(e=>{console.error(e);process.exitCode=1});
