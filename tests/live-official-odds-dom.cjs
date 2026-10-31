const {chromium}=require('playwright');
(async()=>{
 const browser=await chromium.launch({headless:true});
 try{
  const page=await browser.newPage({viewport:{width:390,height:844}});
  const now=new Date();
  const parts=Object.fromEntries(new Intl.DateTimeFormat('en-US',{timeZone:'Asia/Tokyo',year:'numeric',month:'2-digit',day:'2-digit'}).formatToParts(now).filter(x=>x.type!=='literal').map(x=>[x.type,x.value]));
  const day=parts.year+parts.month+parts.day;
  const feed=await page.request.get('https://boatraceopenapi.github.io/api/v1/'+parts.year+'/'+day+'.json',{timeout:18000});
  if(!feed.ok()){console.log('LIVE_ODDS_DOM_UNVERIFIED schedule_http='+feed.status());return;}
  const data=await feed.json();
  const candidates=[];
  for(const [venue,entry] of Object.entries(data?.programs?.stadiums||{})){
   for(const [race,info] of Object.entries(entry.races||{})){
    const cutoff=Date.parse(info.closed_at?.replace(' ','T')+'+09:00');
    if(Number.isFinite(cutoff)&&cutoff>Date.now()+4*60000&&cutoff<Date.now()+3*3600000)
      candidates.push({venue:Number(venue),race:Number(race),cutoff});
   }
  }
  candidates.sort((a,b)=>a.cutoff-b.cutoff);
  const chosen=candidates[0];
  if(!chosen){console.log('LIVE_ODDS_DOM_UNVERIFIED no_upcoming_race');return;}
  const key=day+'-'+String(chosen.venue).padStart(2,'0')+'-'+String(chosen.race).padStart(2,'0');
  const api='https://boat-edge-clean.onrender.com/api/odds?hd='+day+'&jcd='+String(chosen.venue).padStart(2,'0')+'&rno='+chosen.race;
  let response;
  try{response=await page.request.get(api,{timeout:25000});}
  catch(e){console.log('LIVE_ODDS_DOM_UNVERIFIED api_transport');return;}
  if(response.status()!==200){console.log('LIVE_ODDS_DOM_UNVERIFIED api_http='+response.status()+' race='+key);return;}
  const official=await response.json();
  const odds=official.odds;
  if(!official.ok||!odds||Object.keys(odds).length!==120){console.log('LIVE_ODDS_DOM_UNVERIFIED incomplete_api race='+key);return;}
  const site=await page.goto('https://ikst2512-eng.github.io/boat-edge-clean/',{waitUntil:'domcontentloaded',timeout:45000});
  if(!site?.ok())throw Error('PUBLISHED_SITE_UNAVAILABLE');
  await page.evaluate(({day,venue,race})=>{datePinned=true;venueTouched=true;s.date=day.slice(0,4)+'-'+day.slice(4,6)+'-'+day.slice(6,8);s.venue=venue-1;s.race=race;setView('forecast');render();},{day,...chosen});
  try{await page.waitForFunction(()=>predictionTickets.length===10&&displayedPredictionKey===sameRaceKey(),null,{timeout:18000});}
  catch{console.log('LIVE_ODDS_DOM_UNVERIFIED saved_prediction_unavailable race='+key);return;}
  const tickets=await page.evaluate(()=>predictionTickets.slice());
  const token=await page.evaluate(()=>window.predictionRequestId);
  await page.evaluate(token=>loadTicketOdds(sameRaceKey(),token),token);
  try{await page.waitForFunction(()=>document.querySelectorAll('#predictionRows .prediction-odds').length===10&&
     [...document.querySelectorAll('#predictionRows .prediction-odds')].every(x=>x.textContent.includes('取得済オッズ')),null,{timeout:42000});}
  catch{
   const diagnostic=await page.evaluate(()=>({
    view:activeView,race:sameRaceKey(),displayed:displayedPredictionKey,
    requestId:window.predictionRequestId,
    oddsKeys:Object.keys(predictionOdds||{}).length,
    rows:document.querySelectorAll('#predictionRows .prediction-odds').length,
    firstRow:document.querySelector('#predictionRows .prediction-odds')?.textContent?.slice(0,160),
    sourceMeta:document.getElementById('sourceMeta')?.textContent?.slice(0,220)
   }));
   throw Error('LIVE_ODDS_DOM_FAILED api_200_full120_but_odds_not_displayed race='+key+' details='+JSON.stringify(diagnostic));
  }
  const displayed=await page.evaluate(()=>({tickets:predictionTickets.slice(),odds:{...predictionOdds}}));
  if(JSON.stringify(displayed.tickets)!==JSON.stringify(tickets))throw Error('LIVE_ODDS_REORDERED_FORECAST');
  for(const ticket of tickets)if(displayed.odds[ticket]!==odds[ticket])throw Error('LIVE_ODDS_DOM_API_MISMATCH '+ticket);
  console.log('LIVE_ODDS_DOM_API_PASS race='+key+' exact_tickets='+tickets.length);
 }finally{await browser.close()}
})().catch(e=>{console.error(e);process.exitCode=1});
