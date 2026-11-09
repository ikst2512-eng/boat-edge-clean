const {chromium,webkit}=require('playwright');
(async()=>{
 const browserEngine=process.env.BROWSER_ENGINE==='webkit'?'webkit':'chromium';
 const browser=await (browserEngine==='webkit'?webkit:chromium).launch({headless:true});
 let page;
 try{
  page=await browser.newPage({viewport:{width:390,height:844}});
  const errors=[];
  page.on('pageerror',e=>errors.push(e.message));
  // Read-only observation on the *published* WebKit page. Do not suppress
  // SecurityError: the existing E2E job must remain red until deployed code works.
  if(browserEngine==='webkit'){
   await page.addInitScript(()=>{
    const evidence={pushState:0,replaceState:0,recent:[]};
    Object.defineProperty(window,'__cleanPublicHistoryEvidence',{value:evidence});
    for(const method of ['pushState','replaceState']){
     const original=history[method].bind(history);
     history[method]=function(...args){
      evidence[method]++;
      const row={method,atMs:Math.round(performance.now()),
       destination:String(args[2]??'').slice(0,130),
       site:(new Error().stack||'').split('\n').slice(2,5).join(' | ').slice(0,380)};
      evidence.recent.push(row);
      if(evidence.recent.length>16)evidence.recent.shift();
      return original(...args);
     };
    }
   });
  }
  // Transient Render 429/5xx/transport failures must be visible in CI logs.
  // Retry only a bounded number of times; never accept error or altered data.
  async function getArchiveWithRetry(code){
   const url='https://boat-edge-clean.onrender.com/api/four-mode-archive?code='+code;
   const headers={Origin:'https://ikst2512-eng.github.io'};
   const retryable=new Set([429,500,502,503,504]);
   for(let attempt=1;attempt<=3;attempt++){
    let response;
    try{
     response=await page.request.get(url,{timeout:45000,headers});
    }catch(error){
     console.log('ARCHIVE_API_TRANSPORT_RETRY '+JSON.stringify({code,attempt,
      terminal:attempt===3,error:String(error).slice(0,160)}));
     if(attempt===3)throw error;
    }
    if(response){
     if(!retryable.has(response.status()))return response;
     console.log('ARCHIVE_API_TRANSIENT_HTTP_RETRY '+JSON.stringify({
      code,attempt,status:response.status(),terminal:attempt===3
     }));
     if(attempt===3)return response;
    }
    await new Promise(resolve=>setTimeout(resolve,1300*attempt));
   }
   throw Error('ARCHIVE_API_UNREACHABLE_'+code);
  }
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
  // The legacy 12-race pane is lazy: explicitly activate it for this historical audit.
  await page.evaluate(()=>{setForecastPane('races');loadResultList();});
  // The selected venue's complete result list must include 12 distinct race rows.
  await page.waitForFunction(()=>document.querySelectorAll('#resultList .clean-race-card').length===12,{timeout:35000});
  const list=await page.evaluate(()=>[...document.querySelectorAll('#resultList .clean-race-card')].map(node=>({
    race:node.querySelector('.clean-race-head strong')?.textContent,
    status:node.querySelector('.clean-race-state')?.textContent
  })));
  if(list.length!==12||list.some((item,i)=>item.race!==(i+1)+'R'))throw Error('RESULT_LIST_RACE_ORDER_INVALID '+JSON.stringify(list));
  console.log('PASS: published venue 06 result list has 12 ordered race cards');
  // Venue switches must immediately retain twelve race rows and status text.
  // Navigation intentionally compacts each row's redundant four/five controls
  // to ONE "このレースの予想を見る" button; the four tabs live in the selected race panel.
  // The old >=4-actions assertion confused this deliberate design with missing results.
  await page.evaluate(()=>{s.venue=0;s.race=1;setView('forecast');render();});
  await page.waitForFunction(()=>
    document.querySelectorAll('#resultList .clean-race-card').length===12&&
    [...document.querySelectorAll('#resultList .clean-race-actions')].every(n=>n.dataset.compact==='1'),
    null,{timeout:10000});
  const initialRows=await page.evaluate(()=>[...document.querySelectorAll('#resultList .clean-race-card')].map(node=>({
   name:node.querySelector('.clean-race-head strong')?.textContent,
   state:node.querySelector('.clean-race-state')?.textContent,
   actions:[...node.querySelectorAll('.clean-race-actions button')].map(b=>b.textContent.trim())
  })));
  if(initialRows.length!==12||initialRows.some((v,i)=>
      v.name!==(i+1)+'R'||!v.state||v.actions.length!==1||v.actions[0]!=='このレースの予想を見る'))
   throw Error('RESULT_LIST_COMPACT_NAV_OR_STATUS_MISMATCH '+JSON.stringify(initialRows));
  console.log('PASS: 12 result rows with status and single intentional forecast action on venue switch');
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
  // Return to the real four-tab forecast view before testing public navigation.
  await page.evaluate(()=>setForecastPane('prediction'));
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
  // Current navigation uses one selected panel at a time. The forecast's
  // saved-result cache and the distinct Result tab must agree on this race;
  // the old combined-panel .forecast-result-preview is intentionally hidden.
  await page.evaluate(()=>{s.date='2026-10-30';s.venue=2;s.race=1;setView('forecast');render()});
  await page.waitForFunction(()=>document.getElementById('forecastResultStatus').textContent==='CLEAN保存済み確定結果'&&predictionTickets.length===10,{timeout:35000});
  const forecastState=await page.evaluate(()=>({
   forecastVisible:!document.getElementById('forecast').hidden,
   hasForecastPanel:!!document.querySelector('#forecast .forecast-combined-race'),
   savedResult:document.getElementById('forecastResultDetail')?.textContent,
   ticketCount:document.querySelectorAll('#forecast #predictionRows .prediction-row').length
  }));
  if(!forecastState.forecastVisible||!forecastState.hasForecastPanel||
      !forecastState.savedResult?.includes('2 - 3 - 1')||forecastState.ticketCount!==10)
   throw Error('FORECAST_SAVED_RESULT_MISMATCH '+JSON.stringify(forecastState));
  await page.evaluate(()=>{setView('result');render()});
  await page.waitForFunction(()=>document.getElementById('resultStatus').textContent==='CLEAN保存済み結果',{timeout:35000});
  const separateResult=await page.evaluate(()=>({
   view:activeView,
   resultVisible:!document.getElementById('resultSection').hidden,
   order:[...document.querySelectorAll('#resultDetail .result-summary .boat-num')].map(n=>n.textContent.trim())
  }));
  if(separateResult.view!=='result'||!separateResult.resultVisible||
      JSON.stringify(separateResult.order)!==JSON.stringify(['2','3','1']))
   throw Error('SEPARATE_RESULT_TAB_MISSING '+JSON.stringify(separateResult));
  console.log('PASS: saved research forecast and confirmed result available on their respective race tabs');
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
  if(browserEngine==='webkit'&&tabUi.legacyPublishedPage)throw Error('WEBKIT_PUBLIC_FOUR_TABS_ABSENT');
  if(!tabUi.legacyPublishedPage&&(!tabUi.homeDeadline||!tabUi.first.prediction||tabUi.first.result||!tabUi.second.result||tabUi.second.prediction||!tabUi.third.exhibition||tabUi.third.result||!tabUi.fourth.races||tabUi.fourth.prediction))throw Error('FORECAST_TABS_NOT_EXCLUSIVE '+JSON.stringify(tabUi));
  if(browserEngine==='webkit')console.log('PASS_WEBKIT_PUBLIC_FOUR_TABS '+JSON.stringify(tabUi));
  await page.evaluate(()=>{setView('home');render()});
  const homeUi=await page.evaluate(()=>({back:!document.getElementById('raceBrowserToolbar').hidden,home:!document.querySelector('[data-home-only]').hidden}));
  if(homeUi.back||!homeUi.home)throw Error('HOME_BACK_STILL_VISIBLE '+JSON.stringify(homeUi));
  console.log('PASS: Public forecast first, one visible venue selector and home with no back button');
  // Nov 6: prove research archive + post-race result are linked in the live UI.
  // This must never be reported as T-12, formal prediction or pre-race odds proof.
  {
   const code='202611061006',key='20261106-10-06';
   const base='https://raw.githubusercontent.com/ikst2512-eng/boat-edge-clean/main/';
   const [a,b]=await Promise.all([
    page.request.get(base+'four_mode_forecasts/'+code+'.json',{timeout:30000}),
    page.request.get(base+'confirmed_results/'+code+'.json',{timeout:30000})
   ]);
   if(!a.ok()||!b.ok())throw Error('NOV6_SOURCE_UNAVAILABLE '+a.status()+'/'+b.status());
   const saved=await a.json(),result=await b.json(),modes=['narrow','hit','balance','hole'];
   const finish=result.finish_order?.join('-'),counts=modes.map(x=>saved.modes?.[x]?.tickets?.length);
   if(saved.race_code!==code||saved.status!=='provisional'||saved.validated!==false||
     !(Date.parse(saved.generated_at_jst)<Date.parse(saved.deadline_jst))||
     result.race_code!==code||result.status!=='confirmed'||finish!=='4-1-5'||
     JSON.stringify(counts)!==JSON.stringify([5,10,16,22]))
    throw Error('NOV6_SOURCE_INCONSISTENT '+JSON.stringify({counts,finish}));
   const api=await getArchiveWithRetry(code);
   if(!api.ok())throw Error('NOV6_ARCHIVE_API_HTTP_'+api.status());
   const payload=await api.json();
   if(payload.status!=='historical_research_only'||payload.race_code!==code||
     payload.production_forecast!==false||payload.verified_first_git_add!==false||
     modes.some(id=>JSON.stringify(payload.modes?.[id]?.tickets)!==JSON.stringify(saved.modes[id].tickets)))
    throw Error('NOV6_ARCHIVE_PROVENANCE_OR_TICKETS_INVALID');
   const pagesOrigin='https://ikst2512-eng.github.io';
   const corsOk=api.headers()['access-control-allow-origin']===pagesOrigin;
   // Draft-only simulation: browser requests the real Render archive body,
   // but Playwright supplies ONLY the proposed CORS response header.
   // Production CORS remains unverified until human-reviewed deployment.
   let corsSimulated=false;
   if(!corsOk){
    if(process.env.GITHUB_EVENT_NAME!=='pull_request')
     throw Error('NOV6_PUBLIC_SITE_CORS_NOT_DEPLOYED');
    corsSimulated=true;
    const archiveUrl='https://boat-edge-clean.onrender.com/api/four-mode-archive?code='+code;
    // The actual response was fetched and byte-validated above. Reuse its
    // exact decoded payload so page teardown never abandons route.fetch().
    await page.route(archiveUrl,async route=>{
     await route.fulfill({
      status:api.status(),contentType:'application/json',
      headers:{'access-control-allow-origin':pagesOrigin},
      body:JSON.stringify(payload)
     });
    });
    console.log('NOV6_PR_ONLY_CORS_HEADER_SIMULATION '+JSON.stringify({
     code,productionCorsVerified:false,simulation:'single ACAO header on actual archive response'
    }));
   }
   await page.evaluate(()=>{datePinned=true;venueTouched=true;s.date='2026-11-06';s.venue=9;s.race=6;setView('forecast');render()});
   const observe=()=>page.evaluate(()=>({
    selected:typeof sameRaceKey==='function'?sameRaceKey():'missing',
    view:typeof activeView==='string'?activeView:'unknown',
    date:s.date,venue:s.venue+1,race:s.race,
    status:document.getElementById('fourModeForecastStatus')?.textContent,
    loaded:document.getElementById('fourModeForecastStatus')?.dataset.loaded,
    rootKey:document.getElementById('fourModeForecastRows')?.dataset.raceKey,
    cards:document.querySelectorAll('#fourModeForecastRows .four-mode-forecast-item').length,
    forecastHidden:document.getElementById('forecast')?.hidden,
    requestId:window.predictionRequestId,
    pending:pendingVenuePick
   }));
   await page.waitForTimeout(2500);
   console.log('NOV6_LIVE_EARLY_STATE '+JSON.stringify(await observe()));
   try{
    await page.waitForFunction(k=>{
     const root=document.getElementById('fourModeForecastRows');
     return root?.dataset.raceKey===k&&document.getElementById('fourModeForecastStatus')?.dataset.loaded==='true';
    },key,{timeout:25000});
   }catch(e){
    throw Error('NOV6_LIVE_RENDER_PENDING_DIAGNOSTIC '+JSON.stringify(await observe())+' errors='+errors.join(' | ')+' cause='+e.message);
   }
   const visible=await page.evaluate(()=>({
    status:document.getElementById('fourModeForecastStatus').textContent,
    cards:[...document.querySelectorAll('#fourModeForecastRows .four-mode-forecast-item')].map(card=>
      [...card.querySelectorAll('.four-mode-forecast-ticket')].map(row=>row.dataset.fourModeCombo))
   }));
   if(!visible.status.includes('正式予想とは区別')||visible.cards.length!==4||
     modes.some((id,i)=>JSON.stringify(visible.cards[i])!==JSON.stringify(saved.modes[id].tickets.map(v=>v.combo))))
    throw Error('NOV6_VISIBLE_ARCHIVE_MISMATCH '+JSON.stringify(visible));
   await page.waitForFunction(combo=>
    document.querySelector('#fourModeForecastRows .four-mode-match-summary')?.textContent?.includes(combo),
    finish,{timeout:40000});
   const reference=await page.evaluate(()=>({
    text:document.querySelector('#fourModeForecastRows .four-mode-match-summary')?.textContent,
    matched:[...document.querySelectorAll('#fourModeForecastRows .four-mode-match-ticket')].map(n=>n.dataset.fourModeCombo)
   }));
   if(reference.matched.length!==2||!reference.matched.every(x=>x===finish)||
     !reference.text?.includes('正式的中・的中率には含めません'))
    throw Error('NOV6_REFERENCE_MATCH_INVALID '+JSON.stringify(reference));
   // Evidence captures are NEVER used to certify production while the header is simulated.
   const fs=require('node:fs');
   fs.mkdirSync('test-results',{recursive:true});
   const evidenceLabel=corsSimulated?'PR_SIMULATED_CORS_NOT_DEPLOYED':'LIVE_CORS_RESEARCH_ONLY';
   const evidenceBase='test-results/nov6-202611061006-'+evidenceLabel.toLowerCase();
   await page.evaluate(label=>{
    const banner=document.createElement('div');
    banner.id='ci-evidence-simulation-watermark';
    banner.textContent=label;
    Object.assign(banner.style,{
     position:'fixed',top:'0',left:'0',right:'0',zIndex:'2147483647',
     padding:'9px',fontSize:'15px',fontWeight:'900',textAlign:'center',
     color:'#ffffff',background:'#7a1729',pointerEvents:'none'
    });
    document.body.append(banner);
   },evidenceLabel);
   await page.screenshot({path:evidenceBase+'-fourmode.png',fullPage:true});
   await page.evaluate(()=>{setView('result');render()});
   await page.waitForFunction(()=>document.getElementById('resultStatus').textContent==='CLEAN保存済み結果',null,{timeout:45000});
   const shown=await page.evaluate(()=>({
    view:activeView,order:[...document.querySelectorAll('#resultDetail .result-summary .boat-num')].map(el=>el.textContent.trim())
   }));
   if(shown.view!=='result'||shown.order.join('-')!==finish)
    throw Error('NOV6_RESULT_TAB_MISMATCH '+JSON.stringify(shown));
   await page.screenshot({path:evidenceBase+'-confirmed-result.png',fullPage:true});
   const artifactMeta={
    race_code:code,source_status:saved.status,validated:saved.validated,
    mode_counts:counts,finish_order:finish,reference_matches:2,
    confirmed_result_source:result.source_url,
    production_forecast:false,formal_accuracy_counted:false,
    first_git_add_verified:false,pre_race_odds_verified:false,
    live_cors_verified:corsOk,cors_header_simulated_in_pr:corsSimulated,
    screenshot_watermark:evidenceLabel,
    evidence_scope:'published Pages research display, not official T-12 or iPhone hardware'
   };
   fs.writeFileSync(evidenceBase+'-scope.json',JSON.stringify(artifactMeta,null,2)+'\n');
   for(const photo of [evidenceBase+'-fourmode.png',evidenceBase+'-confirmed-result.png']){
    if(fs.statSync(photo).size<2000)throw Error('NOV6_SCREENSHOT_EVIDENCE_EMPTY '+photo);
   }
   console.log('NOV6_REVIEW_SCREENSHOTS_SAVED '+JSON.stringify({
    mode:evidenceLabel,paths:[evidenceBase+'-fourmode.png',evidenceBase+'-confirmed-result.png']
   }));
   console.log((corsSimulated?'NOV6_PR_SIMULATED_CORS_E2E_PASS ':'LIVE_NOV6_RESEARCH_ONLY_E2E_PASS ')+JSON.stringify({
    code,counts,finish,referenceMatches:2,firstGitAddVerified:false,
    productionForecast:false,liveCorsVerified:corsOk,headerSimulatedInPr:corsSimulated
   }));
  }
  // Nov 7: a separate real-race sentinel. This must not reuse the Nov 6 result
  // or turn historical research matches into attested pre-deadline accuracy.
  {
   const code='202611071006',key='20261107-10-06',finish='1-3-2';
   const base='https://raw.githubusercontent.com/ikst2512-eng/boat-edge-clean/main/';
   const modes=['narrow','hit','balance','hole'];
   const [sourceResponse,resultResponse]=await Promise.all([
    page.request.get(base+'four_mode_forecasts/'+code+'.json',{timeout:30000}),
    page.request.get(base+'confirmed_results/'+code+'.json',{timeout:30000})
   ]);
   if(!sourceResponse.ok()||!resultResponse.ok())
    throw Error('NOV7_SOURCE_UNAVAILABLE '+sourceResponse.status()+'/'+resultResponse.status());
   const saved=await sourceResponse.json(),result=await resultResponse.json();
   const counts=modes.map(mode=>saved.modes?.[mode]?.tickets?.length);
   const ranks=modes.map(mode=>(saved.modes?.[mode]?.tickets||[]).findIndex(ticket=>ticket.combo===finish)+1);
   if(saved.race_code!==code||saved.status!=='provisional'||saved.validated!==false||
      !(Date.parse(saved.generated_at_jst)<Date.parse(saved.deadline_jst))||
      result.race_code!==code||result.status!=='confirmed'||result.finish_order?.join('-')!==finish||
      JSON.stringify(counts)!=='[5,10,16,22]'||JSON.stringify(ranks)!=='[3,3,5,0]')
    throw Error('NOV7_SOURCE_OR_RANKS_CHANGED '+JSON.stringify({counts,ranks,finish}));
   const apiUrl='https://boat-edge-clean.onrender.com/api/four-mode-archive?code='+code;
   const pagesOrigin='https://ikst2512-eng.github.io';
   const api=await getArchiveWithRetry(code);
   if(!api.ok())throw Error('NOV7_ARCHIVE_API_HTTP_'+api.status());
   const payload=await api.json();
   if(payload.race_code!==code||payload.status!=='historical_research_only'||
      payload.production_forecast!==false||payload.verified_first_git_add!==false||
      modes.some(mode=>JSON.stringify(payload.modes?.[mode]?.tickets)!==JSON.stringify(saved.modes[mode].tickets)))
    throw Error('NOV7_ARCHIVE_SOURCE_MISMATCH');
   const corsOk=api.headers()['access-control-allow-origin']===pagesOrigin;
   let corsSimulated=false;
   if(!corsOk){
    if(process.env.GITHUB_EVENT_NAME!=='pull_request')
     throw Error('NOV7_PUBLIC_SITE_CORS_NOT_DEPLOYED');
    corsSimulated=true;
    await page.route(apiUrl,route=>route.fulfill({
     status:api.status(),contentType:'application/json',
     headers:{'access-control-allow-origin':pagesOrigin},
     body:JSON.stringify(payload)
    }));
   }
   await page.evaluate(()=>{
    datePinned=true;venueTouched=true;s.date='2026-11-07';s.venue=9;s.race=6;
    setView('forecast');render();
   });
   await page.waitForFunction(k=>
    document.getElementById('fourModeForecastRows')?.dataset.raceKey===k&&
    document.getElementById('fourModeForecastStatus')?.dataset.loaded==='true',
    key,{timeout:35000});
   const visible=await page.evaluate(()=>({
    status:document.getElementById('fourModeForecastStatus').textContent,
    cards:[...document.querySelectorAll('#fourModeForecastRows .four-mode-forecast-item')].map(card=>
     [...card.querySelectorAll('.four-mode-forecast-ticket')].map(row=>row.dataset.fourModeCombo))
   }));
   if(!visible.status.includes('正式予想とは区別')||visible.cards.length!==4||
      modes.some((mode,i)=>JSON.stringify(visible.cards[i])!==JSON.stringify(saved.modes[mode].tickets.map(t=>t.combo))))
    throw Error('NOV7_VISIBLE_TICKETS_MISMATCH '+JSON.stringify(visible));
   await page.waitForFunction(combo=>
    document.querySelector('#fourModeForecastRows .four-mode-match-summary')?.textContent?.includes(combo),
    finish,{timeout:40000});
   const hit=await page.evaluate(()=>({
    text:document.querySelector('#fourModeForecastRows .four-mode-match-summary')?.textContent,
    matches:[...document.querySelectorAll('#fourModeForecastRows .four-mode-match-ticket')].map(row=>row.dataset.fourModeCombo),
    badges:[...document.querySelectorAll('#fourModeForecastRows .four-mode-match-badge')].map(card=>card.textContent.trim())
   }));
   if(hit.matches.length!==3||hit.matches.some(x=>x!==finish)||
      !hit.text?.includes('参考一致：4モード中 3モード')||
      !hit.text?.includes('正式的中・的中率には含めません')||
      hit.badges.length!==4||!hit.badges[3].includes('一致なし'))
    throw Error('NOV7_REFERENCE_3_OF_4_INVALID '+JSON.stringify(hit));
   const fs=require('node:fs');fs.mkdirSync('test-results',{recursive:true});
   const label=corsSimulated?'PR_SIMULATED_CORS_NOT_DEPLOYED':'LIVE_CORS_RESEARCH_ONLY';
   const prefix='test-results/nov7-202611071006-'+label.toLowerCase();
   await page.evaluate(text=>{
    const banner=document.getElementById('ci-evidence-simulation-watermark');
    if(banner)banner.textContent=text;
   },label);
   await page.screenshot({path:prefix+'-fourmode.png',fullPage:true});
   await page.evaluate(()=>{setView('result');render()});
   await page.waitForFunction(k=>
    displayedResultKey===k&&displayedResultCombo==='1-3-2'&&
    document.getElementById('resultStatus')?.textContent==='CLEAN保存済み結果',
    key,{timeout:45000});
   const shown=await page.evaluate(()=>({
    view:activeView,order:[...document.querySelectorAll('#resultDetail .result-summary .boat-num')].map(x=>x.textContent.trim())
   }));
   if(shown.view!=='result'||shown.order.join('-')!==finish)
    throw Error('NOV7_RESULT_TAB_MISMATCH '+JSON.stringify(shown));
   await page.screenshot({path:prefix+'-confirmed-result.png',fullPage:true});
   const evidence={
    race_code:code,source_status:saved.status,validated:saved.validated,
    mode_counts:counts,reference_ranks:ranks,finish_order:finish,
    reference_matches:3,production_forecast:false,formal_accuracy_counted:false,
    first_git_add_verified:false,pre_race_odds_verified:false,
    live_cors_verified:corsOk,cors_header_simulated_in_pr:corsSimulated,
    screenshot_watermark:label,evidence_scope:'real research archives and result on public Pages, not formal T-12'
   };
   fs.writeFileSync(prefix+'-scope.json',JSON.stringify(evidence,null,2)+'\n');
   for(const photo of [prefix+'-fourmode.png',prefix+'-confirmed-result.png']){
    if(fs.statSync(photo).size<2000)throw Error('NOV7_SCREENSHOT_EVIDENCE_EMPTY '+photo);
   }
   console.log((corsSimulated?'NOV7_PR_SIMULATED_CORS_E2E_PASS ':'LIVE_NOV7_RESEARCH_ONLY_E2E_PASS ')+
    JSON.stringify({code,counts,ranks,finish,referenceMatches:3,
     productionForecast:false,liveCorsVerified:corsOk,headerSimulatedInPr:corsSimulated}));
  }
  if(errors.length)throw Error('PAGE_JS_ERRORS '+errors.join('|'));
  console.log('PASS: Published 20261030 01 1R research forecast shows ten exact saved tickets; no reconstructed forecast.');
 }catch(error){
  if(browserEngine==='webkit'&&page){
   const evidence=await page.evaluate(()=>window.__cleanPublicHistoryEvidence||null)
    .catch(e=>({diagnosticUnavailable:String(e).slice(0,200)}));
   console.error('PUBLIC_WEBKIT_HISTORY_FAILURE_DIAGNOSTIC '+JSON.stringify({
    error:String(error).slice(0,220),evidence,
    source:'published Pages, not Draft HTML',failureUnchanged:true
   }));
  }
  throw error;
 }finally{await browser.close()}
})().catch(e=>{console.error(e);process.exitCode=1});
