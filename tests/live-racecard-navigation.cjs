const {chromium}=require('playwright');
(async()=>{
 const browser=await chromium.launch({headless:true});
 try{
  const page=await browser.newPage({viewport:{width:390,height:844}});
  const errors=[];page.on('pageerror',e=>errors.push(e.message));
  const site='https://ikst2512-eng.github.io/boat-edge-clean/';
  const res=await page.goto(site,{waitUntil:'domcontentloaded',timeout:45000});
  if(!res?.ok())throw Error('PAGES_UNAVAILABLE '+res?.status());
  const keys=[
   {date:'2026-10-30',venue:1,race:1},
   {date:'2026-10-30',venue:23,race:12},
   {date:'2026-10-28',venue:4,race:2}
  ];
  for(const selected of keys){
   await page.evaluate(item=>{
    datePinned=true;venueTouched=true;
    s.date=item.date;s.venue=item.venue-1;s.race=item.race;
    setView('card');render();
   },selected);
   const state=await page.evaluate(()=>({
    key:sameRaceKey(),label:document.getElementById('activeRaceLabel').textContent,
    venue:document.getElementById('forecastVenue').value,
    race:document.getElementById('forecastRace').value,
    path:location.pathname,
    search:location.search
   }));
   const expected=selected.date.replaceAll('-','')+'-'+String(selected.venue).padStart(2,'0')+'-'+String(selected.race).padStart(2,'0');
   if(state.key!==expected||Number(state.venue)!==selected.venue||Number(state.race)!==selected.race||!state.search.includes('race='+selected.race))throw Error('NAV_MISMATCH '+JSON.stringify({selected,state}));
   await page.evaluate(()=>setView('exhibit'));
   const switched=await page.evaluate(()=>({key:sameRaceKey(),visible:!document.getElementById('raceDataSection').hidden}));
   if(switched.key!==expected||!switched.visible)throw Error('EXHIBIT_NAV_MISMATCH '+JSON.stringify(switched));
  }
  // Inspect a live upcoming race with real preview rows when available.
  // Otherwise report an explicit unverified result, never a fabricated pass.
  const today=new Intl.DateTimeFormat('en-CA',{timeZone:'Asia/Tokyo',year:'numeric',month:'2-digit',day:'2-digit'}).format(new Date()).replaceAll('-','');
  const current=new Date();
  const origin='https://boat-edge-clean.onrender.com';
  const url=origin+'/api/clean-racecard?hd='+today+'&jcd=24&rno=12';

  const api=await page.evaluate(async url=>{
   const controller=new AbortController();const timeout=setTimeout(()=>controller.abort(),30000);
   try{const response=await fetch(url,{signal:controller.signal,headers:{Accept:'application/json'}});const body=await response.json();return {http:response.status,status:body.status,ok:body.ok,schema:body.schema_version,race:body.race_key,racers:body.racers?.length}}finally{clearTimeout(timeout)}
  },url);
  if(api.http===200 && api.race===today+'-24-12'){
   const audited=await page.evaluate(async url=>{
    const response=await fetch(url);const body=await response.json();
    const preview=body.beforeinfo;
    const audit=body.source_audit?.beforeinfo;
    return {status:audit?.status,source_status:audit?.source_status,
      racers:preview?.racers,starts:preview?.start_exhibition};
   },url);
   if(audited.status==='ok'){
    if(audited.racers?.length!==6||audited.starts?.length!==6)throw Error('LIVE_EXHIBITION_INCOMPLETE');
    console.log('LIVE_EXHIBITION_API_PASS '+JSON.stringify({race:api.race,exhibition_count:audited.racers.length,entry_count:audited.starts.length}));
   }else console.log('LIVE_EXHIBITION_NOT_VERIFIED '+JSON.stringify({race:api.race,status:audited.status,source_status:audited.source_status}));
  }
  if(api.http===200){
   if(api.schema!=='boat-edge-race-v5'||api.race!==today+'-24-12'||api.racers!==6)throw Error('LIVE_API_INCOMPLETE '+JSON.stringify(api));
   console.log('LIVE_SIX_BOAT_API_PASS '+JSON.stringify(api));
  }else if([400,404,422,502,503].includes(api.http)){
   console.log('LIVE_RACE_DATA_UNAVAILABLE_NOT_A_PASS '+JSON.stringify(api));
  }else throw Error('UNEXPECTED_RACE_API_RESPONSE '+JSON.stringify(api));
  if(errors.length)throw Error('JS_ERRORS '+errors.join('|'));
  console.log('PASS: Published Pages switches venue/race and card/exhibition without stale selected race.');
 }finally{await browser.close()}
})().catch(e=>{console.error(e);process.exitCode=1});
