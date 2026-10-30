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
   const back=await page.evaluate(()=>{
    const control=document.getElementById('raceViewBack');
    if(!control||control.hidden||document.getElementById('raceBrowserToolbar').hidden)
     throw Error('RACE_VIEW_BACK_CONTROL_MISSING');
    control.click();
    return {key:sameRaceKey(),view:activeView,visible:!document.getElementById('raceDataSection').hidden};
   });
   if(back.key!==expected||back.view!=='card')throw Error('RACE_VIEW_BACK_MISMATCH '+JSON.stringify({selected,back}));
  }
  // Inspect a live upcoming race with real preview rows when available.
  // Otherwise report an explicit unverified result, never a fabricated pass.
  const parts=Object.fromEntries(new Intl.DateTimeFormat('en-US',{timeZone:'Asia/Tokyo',year:'numeric',month:'2-digit',day:'2-digit'}).formatToParts(new Date()).filter(x=>x.type!=='literal').map(x=>[x.type,x.value]));
  const today=parts.year+parts.month+parts.day;
  if(!/^20\d{6}$/.test(today))throw Error('INVALID_JST_DAY '+today);
  const origin='https://boat-edge-clean.onrender.com';
  const feed='https://boatraceopenapi.github.io/api/v1/'+today.slice(0,4)+'/'+today+'.json';
  let selected=null;
  let selections=[];
  let liveExhibitionVerified=false;
  let scheduleFeedStatus='unavailable';
  const raceDiagnostics=[];
  try{
   const response=await fetch(feed,{signal:AbortSignal.timeout(10000)});
   if(!response.ok)throw Error('LIVE_SCHEDULE_FEED_HTTP_'+response.status);
   if(response.ok){
    const data=await response.json();
    if(!data?.programs?.stadiums || typeof data.programs.stadiums!=='object')throw Error('LIVE_SCHEDULE_FEED_SCHEMA_INVALID');
    scheduleFeedStatus='ok';
    const stadiums=data?.programs?.stadiums||{};
    const upcoming=[];
    for(const [venue,info] of Object.entries(stadiums)){
     for(const [race,entry] of Object.entries(info.races||{})){
      const rawCutoff=entry?.closed_at;
      if(typeof rawCutoff!=='string'||!/20\d\d-\d\d-\d\d \d\d:\d\d:\d\d/.test(rawCutoff))continue;
      const cutoff=new Date(rawCutoff.replace(' ','T')+'+09:00');
      if(Number(venue)>=1&&Number(venue)<=24&&Number(race)>=1&&Number(race)<=12
         &&Number.isFinite(cutoff.getTime())&&cutoff.getTime()>Date.now()+120000){
       upcoming.push({venue:Number(venue),race:Number(race),cutoff:cutoff.getTime()});
      }
     }
    }
    // A race closing soon is more likely to have published exhibition data.
    // Prefer the 2–22 minute pre-cutoff window; preserve fallback for diagnostics.
    const previewWindow=upcoming.filter(x=>x.cutoff<=Date.now()+22*60*1000);
    upcoming.sort((a,b)=>a.cutoff-b.cutoff);
    previewWindow.sort((a,b)=>a.cutoff-b.cutoff);
    // Sample several distinct races: one unpublished feed must not hide other live exhibitions.
    // Diversify venues: eight early races from three venues can miss an
    // independently published preview at another course entirely.
    const ordered=[...previewWindow,...upcoming.filter(x=>!previewWindow.includes(x))];
    const usedVenues=new Set();
    const distinct=ordered.filter(x=>{
     if(usedVenues.has(x.venue))return false;
     usedVenues.add(x.venue);return true;
    });
    selections=[...distinct,...ordered.filter(x=>!distinct.includes(x))].slice(0,8);
    selected=selections[0]||null;
    console.log('LIVE_PROBE_SELECTED_RACES '+JSON.stringify(selections));
    console.log('LIVE_PREVIEW_WINDOW_CANDIDATES '+JSON.stringify({count:previewWindow.length}));
    console.log('LIVE_SCHEDULE_CANDIDATES '+JSON.stringify({date:today,count:upcoming.length,selected}));
   }
  }catch(e){console.log('LIVE_SCHEDULE_LOOKUP_UNAVAILABLE '+String(e).slice(0,130));}
  if(selected){
   for(const selected of selections){
   if(liveExhibitionVerified)break;
   const url=origin+'/api/clean-racecard?hd='+today+'&jcd='+selected.venue+'&rno='+selected.race;
   const api=await page.evaluate(async url=>{
    const controller=new AbortController(),timeout=setTimeout(()=>controller.abort(),20000);
    try{
     const response=await fetch(url,{signal:controller.signal,headers:{Accept:'application/json'}});
     const body=await response.json();
     return {http:response.status,body};
    }catch(error){
     return {http:0,error:String(error),body:null};
    }finally{clearTimeout(timeout)}
   },url);
   if(api.http===0){
    raceDiagnostics.push({race:today+'-'+String(selected.venue).padStart(2,'0')+'-'+String(selected.race).padStart(2,'0'),http:'network',preview:'通信失敗・タイムアウト'});
    console.log('LIVE_RACE_API_TIMEOUT_OR_NETWORK_NOT_A_PASS '+JSON.stringify({url,error:api.error}));
    continue;
   }
   const expected=today+'-'+String(selected.venue).padStart(2,'0')+'-'+String(selected.race).padStart(2,'0');
   if(api.http===200){
    const d=api.body;
    if(d.schema_version!=='boat-edge-race-v5'||d.race_key!==expected||d.racers?.length!==6)throw Error('LIVE_API_INCOMPLETE '+expected);
    console.log('LIVE_SIX_BOAT_API_PASS '+expected);
    const preview=d.beforeinfo,audit=d.source_audit?.beforeinfo;
    raceDiagnostics.push({race:expected,http:200,preview:audit?.status||'監査情報なし',sources:audit?.source_status});
    if(audit?.status==='ok'){
     const observed=Date.parse(audit.fetched_at||'');
     const deadline=Date.parse(d.meta?.date+'T'+d.meta?.deadline+':00+09:00');
     if(!Number.isFinite(observed)||!Number.isFinite(deadline)||observed>=deadline||observed>Date.now())
      throw Error('LIVE_EXHIBITION_TIMESTAMP_INVALID '+JSON.stringify({race:expected,observed:audit.fetched_at,deadline:d.meta?.deadline}));
     if(preview?.racers?.length!==6||preview?.start_exhibition?.length!==6)throw Error('LIVE_EXHIBITION_INCOMPLETE '+expected);
     // Cross-check that the actual user-facing forecast preview can consume the same race.
     await page.evaluate(item=>{datePinned=true;venueTouched=true;s.date=item.date;s.venue=item.venue-1;s.race=item.race;setView('forecast');render();},
       {date:today.slice(0,4)+'-'+today.slice(4,6)+'-'+today.slice(6,8),...selected});
     const expectedRows=Array.from({length:6},(_,i)=>{
      const lane=i+1,ex=preview.racers.find(v=>Number(v.lane)===lane),st=preview.start_exhibition.find(v=>Number(v.lane)===lane);
      if(!ex||!st)throw Error('LIVE_EXHIBITION_MISSING_LANE '+lane);
      return {lane,text:'展示 '+ex.exhibition_time+'｜チルト '+ex.tilt+'｜進入 '+st.course+'コース｜展示ST '+st.st};
     });
     await page.waitForFunction(key=>document.getElementById('forecastPreviewRows')?.children.length===6&&sameRaceKey()===key,expected,{timeout:12000});
     const displayed=await page.locator('#forecastPreviewRows .clean-race-lane').allInnerTexts();
     if(displayed.length!==6||expectedRows.some((row,i)=>!displayed[i].includes(row.text)))
      throw Error('LIVE_EXHIBITION_DOM_MISMATCH '+JSON.stringify({expectedRows,displayed}));
     if(Date.now()>=deadline){
      console.log('LIVE_EXHIBITION_DISPLAY_AFTER_CUTOFF_NOT_A_PASS '+expected);
      continue;
     }
     liveExhibitionVerified=true;
     console.log('LIVE_EXHIBITION_DOM_PASS '+JSON.stringify({race:expected,exhibition_count:6,values_verified:true}));
    }else console.log('LIVE_EXHIBITION_NOT_VERIFIED '+JSON.stringify({race:expected,status:audit?.status,source_status:audit?.source_status}));
   }else if([400,404,422,502,503].includes(api.http)){raceDiagnostics.push({race:expected,http:api.http,preview:'API利用不可'});console.log('LIVE_RACE_DATA_UNAVAILABLE_NOT_A_PASS '+JSON.stringify({race:expected,http:api.http,status:api.body?.status}));}
   else throw Error('UNEXPECTED_RACE_API_RESPONSE '+api.http);
   }
  }else console.log('NO_LIVE_UPCOMING_RACE_NOT_A_PASS '+today);
  if(errors.length)throw Error('JS_ERRORS '+errors.join('|'));
  console.log('PASS_NAVIGATION: Published Pages switches venue/race and card/exhibition without stale selected race.');
  const exhibitionVerdict=liveExhibitionVerified?'PASS_LIVE_EXHIBITION_SIX_BOATS':'UNVERIFIED_LIVE_EXHIBITION_NOT_A_PASS';
  console.log(exhibitionVerdict);
  // Scheduled monitoring must detect an actual live-data gap rather than
  // silently passing because navigation worked. Nighttime / no-race runs
  // remain explicitly unverified, never a fabricated exhibition success.
  if(process.env.GITHUB_STEP_SUMMARY){
   const fs=require('node:fs');
   const proof=liveExhibitionVerified?'実証済み（APIと画面の6艇分が一致）':'未実証（展示6艇分の一致確認なし）';
   const rows=[
    '## BOAT EDGE CLEAN 公開ブラウザ検証',
    '',
    '| 検証項目 | 結果 |',
    '| --- | --- |',
    '| 公開Pagesの画面遷移 | 成功 |',
    '| 開催情報ソースの取得 | '+(scheduleFeedStatus==='ok'?'成功':'失敗・未取得')+' |',
    '| 締切前検査の対象数 | '+selections.length+'件（最大8件） |',
    '| 締切前展示6艇分の本番照合 | '+proof+' |',
    '| 実測対象レース | '+(selected?selections.map(x=>today+'-'+String(x.venue).padStart(2,'0')+'-'+String(x.race).padStart(2,'0')).join(', '):'なし')+' |',
    '',
    '判定: `'+exhibitionVerdict+'`',
    '',
    '| レース | HTTP | 展示の取得状態 | ソース状態（tkz/stt/sui） |',
    '| --- | --- | --- | --- |',
    ...(raceDiagnostics.length?raceDiagnostics.map(x=>'| '+x.race+' | '+x.http+' | '+x.preview+' | '+(['tkz','stt','sui'].map(k=>x.sources?.[k]||'―').join(' / '))+' |'):['| 対象なし | ― | 未実証 | ― |']),
    '',
    'Navigation CI成功だけでは展示実測成功を意味しません。',
    ''
   ];
   fs.appendFileSync(process.env.GITHUB_STEP_SUMMARY,rows.join('\n')+'\n');
  }
  if(process.env.GITHUB_EVENT_NAME==='schedule' && scheduleFeedStatus!=='ok')throw Error('SCHEDULED_LIVE_SCHEDULE_SOURCE_UNAVAILABLE');
  if(process.env.GITHUB_EVENT_NAME==='schedule' && selections.length>0 && !liveExhibitionVerified){
   throw Error('SCHEDULED_LIVE_EXHIBITION_UNVERIFIED_WITH_ELIGIBLE_RACES '+JSON.stringify({
    date:today,eligible_checked:selections.length,races:selections.map(x=>[x.venue,x.race])
   }));
  }
 }finally{await browser.close()}
})().catch(e=>{console.error(e);process.exitCode=1});
