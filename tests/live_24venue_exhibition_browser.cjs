'use strict';
// P2 diagnostic: every venue must be exercised with a REAL held race from
// immutable schedule_snapshots. Read-only live Pages + Render, no request mocks.
// This is historical display coverage, NOT independent live official 24/24 data
// or a formal predeadline source/forecast certification.
const fs=require('node:fs');
const crypto=require('node:crypto');
const assert=require('node:assert/strict');
const {chromium,webkit,request}=require('playwright');
const PAGE='https://ikst2512-eng.github.io/boat-edge-clean/';
const API='https://boat-edge-clean.onrender.com/api/clean-racecard';
const days=['20261101','20261106','20261113'];
const sources=days.map(day=>({day,record:JSON.parse(fs.readFileSync('schedule_snapshots/'+day+'.json','utf8'))}));
for(const {day,record} of sources){
 assert.equal(record.date,day.slice(0,4)+'-'+day.slice(4,6)+'-'+day.slice(6));
 assert.equal(record.phase,'PRE_RESULT');
 assert.equal(record.results_seen,false);
 assert.ok(Array.isArray(record.venues)&&record.venues.length>0);
}
const fixtures=Array.from({length:24},(_,i)=>{
 const venue=i+1;
 // Prefer actual original-exhibition source rows instead of treating one
 // missing 1R as if the entire venue did not supply original measurements.
 const preferred=venue===8?{day:'20261113',race:1}:venue===21?{day:'20261101',race:2}:null;
 const race=preferred?.race||1;
 const source=sources.find(({day,record})=>(!preferred||day===preferred.day)&&
  record.venues.some(v=>Number(v.jcd)===venue&&v.races?.some(r=>Number(r.race_no)===race)));
 assert.ok(source,'No recorded real race for venue '+venue+' in the 3-day source window');
 return {day:source.day,venue,race};
});
assert.equal(new Set(fixtures.map(f=>f.venue)).size,24);
const pad=n=>String(n).padStart(2,'0');
const raceKey=f=>f.day+'-'+pad(f.venue)+'-'+pad(f.race);
const report=[];
const sleep=ms=>new Promise(resolve=>setTimeout(resolve,ms));
// Independently retrieve the real upstream CSV, rather than interpreting
// Render's own original-exhibition status as proof of its numerical values.
const sourceCache=new Map();
function parseCsv(line){
 const fields=[];let value='',quoted=false;
 for(let i=0;i<line.length;i++){
  const ch=line[i];
  if(ch==='"'){
   if(quoted&&line[i+1]==='"'){value+='"';i++;}
   else quoted=!quoted;
  }else if(ch===','&&!quoted){fields.push(value);value='';}
  else value+=ch;
 }
 fields.push(value);return fields;
}
async function originalCsv(ctx,day){
 if(!sourceCache.has(day)){
  const promise=(async()=>{
   const url='https://boatracecsv.github.io/data/previews/original_exhibition/'+
    day.slice(0,4)+'/'+day.slice(4,6)+'/'+day.slice(6,8)+'.csv';
   const response=await ctx.get(url,{timeout:35000});
   assert.equal(response.status(),200,'Original source CSV unavailable '+day);
   const bytes=await response.body();
   const lines=bytes.toString('utf8').replace(/^\uFEFF/,'').split(/\r?\n/).filter(Boolean);
   const header=parseCsv(lines.shift()||'');
   assert.ok(header.length===34&&new Set(header).size===34,'Original CSV column schema changed '+day);
   return {columns:Object.fromEntries(header.map((x,i)=>[x,i])),
    rows:lines.map(parseCsv),sha256:crypto.createHash('sha256').update(bytes).digest('hex')};
  })();
  sourceCache.set(day,promise);
 }
 return sourceCache.get(day);
}
async function getCard(ctx,f){
 const url=API+'?hd='+f.day+'&jcd='+f.venue+'&rno='+f.race;
 let res;
 for(let attempt=0;attempt<3;attempt++){
  try{res=await ctx.get(url,{timeout:25000});}
  catch(e){if(attempt===2)throw e;await sleep(800*(attempt+1));continue;}
  if(![429,500,502,503,504].includes(res.status())||attempt===2)break;
  await sleep(800*(attempt+1));
 }
 const status=res.status();
 let body=null;
 if(status===200){body=await res.json();
  assert.equal(body.race_key,raceKey(f),'Render returned a different race');
 }
 return {status,body};
}
async function inspect(browser,ctx,engine,f){
 const expected=raceKey(f);
 const {status:http,body:card}=await getCard(ctx,f);
 const page=await browser.newPage({viewport:{width:390,height:844},isMobile:true,hasTouch:true});
 const errors=[];
 page.on('pageerror',error=>errors.push(String(error).slice(0,200)));
 try{
  const url=new URL(PAGE);
  for(const [k,v] of [['date',f.day.slice(0,4)+'-'+f.day.slice(4,6)+'-'+f.day.slice(6)],['venue',pad(f.venue)],['race',String(f.race)],['view','exhibit']])url.searchParams.set(k,v);
  const response=await page.goto(url.href,{waitUntil:'domcontentloaded',timeout:45000});
  assert.equal(response?.status(),200,'Published Pages HTTP '+expected);
  await page.evaluate(()=>{datePinned=true;venueTouched=true;venueSpecified=true;setView('exhibit');render();});
  await page.waitForFunction(key=>{
   const root=document.querySelector('#exhibitionGrid');
   const count=root?.querySelectorAll('.exhibition-boat').length||0;
   const status=document.querySelector('#raceDataStatus')?.textContent||'';
   const original=document.querySelector('#originalExhibitionStatus')?.dataset.originalState||'';
   return sameRaceKey()===key&&activeView==='exhibit'&&(
    (count===6&&original.length>0)||
    (count===0&&/取得できません|検証に失敗|開催されていません|未取得/.test(status))
   );
  },expected,{timeout:50000});
  const shown=await page.evaluate(()=>({
   race:sameRaceKey(),view:activeView,
   status:document.querySelector('#raceDataStatus')?.textContent||'',
   original:document.querySelector('#originalExhibitionStatus')?.dataset.originalState||null,
   cards:[...document.querySelectorAll('#exhibitionGrid .exhibition-boat')].map(c=>({
    lane:Number(c.querySelector('.lane-badge')?.textContent),
    name:c.querySelector('.exhibition-name')?.textContent||'',
    metrics:Object.fromEntries([...c.querySelectorAll('.exhibition-metric')].map(x=>[
     x.querySelector('span')?.textContent||'',x.querySelector('strong')?.textContent||''
    ])),
    originals:[...c.querySelectorAll('.exhibition-original-metric')].map(x=>({
     label:x.querySelector('span')?.textContent||'',
     state:x.dataset.sourceValueState,
     value:x.querySelector('strong')?.textContent||''
    })),
    missing:c.querySelector('.exhibition-original-pending')?.textContent||''
   })),
   overflow:document.documentElement.scrollWidth-document.documentElement.clientWidth
  }));
  assert.equal(shown.race,expected);
  assert.equal(shown.view,'exhibit');
  assert.ok(shown.overflow<=1,'390px horizontal overflow '+expected+' '+shown.overflow);
  let originalCompared=0,originalSha=null;
  if(http===200&&card?.source_audit?.race_card?.status==='ok'){
   assert.equal(shown.cards.length,6,'Valid Render racecard not displayed as six boats '+expected);
   for(let i=0;i<6;i++){
    const boat=shown.cards[i];
    assert.equal(boat.lane,i+1,'Boat lane/order mismatch '+expected);
    assert.ok(boat.name&&boat.name!=='未提供','Invalid racer display '+expected);
    assert.deepEqual(Object.keys(boat.metrics).sort(),
      ['展示タイム','展示ST','展示進入','チルト','平均ST'].sort(),'Missing official field labels '+expected);
    if(card.source_audit?.beforeinfo?.status!=='ok'){
     for(const key of ['展示タイム','展示ST','展示進入','チルト'])
      assert.equal(boat.metrics[key],'—','Unverified official measurement displayed '+expected+' boat '+(i+1)+' '+key);
    }
   }
   assert.ok(shown.original,'Original-source status not classified '+expected);
   const original=await originalCsv(ctx,f.day);
   originalSha=original.sha256;
   const c=original.columns;
   const code=f.day+pad(f.venue)+pad(f.race);
   const matched=original.rows.filter(row=>row[c['レースコード']]===code);
   if(f.venue===3){
    assert.equal(matched.length,0,'Edogawa unexpectedly has upstream originals');
    assert.equal(shown.original,'non_provided','Edogawa structurally non-provided mislabelled');
    assert.ok(shown.cards.every(x=>x.missing==='オリ展：非提供'));
   }else{
    assert.equal(matched.length,1,'Original source race absent/duplicated '+code);
    const row=matched[0],count=Number(row[c['計測数']]);
    assert.ok(Number.isInteger(count)&&count>=1&&count<=3,'Invalid original measurement count '+code);
    assert.equal(row[c['レース日']],f.day.slice(0,4)+'-'+f.day.slice(4,6)+'-'+f.day.slice(6,8));
    assert.equal(Number(row[c['レース場']]),f.venue);
    assert.equal(Number(String(row[c['レース回']]).replace(/R$/i,'')),f.race);
    let anyMissing=false;
    for(let lane=1;lane<=6;lane++){
     const shownBoat=shown.cards[lane-1];
     assert.equal(shownBoat.originals.length,count,'Missing original columns '+code+' boat '+lane);
     for(let k=1;k<=count;k++){
      const label=String(row[c['計測項目'+k]]||'').trim();
      const raw=String(row[c['艇'+lane+'_値'+k]]??'').trim();
      const displayed=shownBoat.originals[k-1];
      assert.ok(label,'Empty original column label '+code);
      assert.equal(displayed.label,label,'Original label mismatch '+code+' boat '+lane+' metric '+k);
      assert.equal(displayed.value,raw||'—','Original value mismatch '+code+' boat '+lane+' metric '+k);
      assert.equal(displayed.state,raw?'present':'missing','Original missingness mismatch '+code+' boat '+lane+' metric '+k);
      if(!raw)anyMissing=true;
      originalCompared++;
     }
    }
    assert.ok(anyMissing?shown.original.startsWith('partial_'):['verified','deadline_mismatch'].includes(shown.original),
     'Original source status inconsistent '+code+' '+shown.original);
   }
  }else{
   assert.equal(shown.cards.length,0,'Unverified/failed source fabricated six boats '+expected);
  }
  assert.deepEqual(errors,[],'Browser JS errors '+expected);
  const result={
   engine,venue:pad(f.venue),race:expected,renderHttp:http,boats:shown.cards.length,
   original:shown.original||'unavailable',originalCompared,originalSha,
   missing:shown.cards.length===0,mobileOverflowPx:shown.overflow,noMocks:true
  };
  report.push(result);
  console.log('PUBLIC_P2_24VENUE_CASE '+JSON.stringify(result));
 }finally{await page.close();}
}
(async()=>{
 const ctx=await request.newContext({timeout:35000});
 try{
  for(const [name,engine] of [['chromium',chromium],['webkit',webkit]]){
   const browser=await engine.launch({headless:true});
   try{
    // Limit requests: too many parallel Render/CSV reads can create
    // false 502s and is unsuitable for a real production acceptance gate.
    for(const fixture of fixtures){
     try{await inspect(browser,ctx,name,fixture);}
     catch(error){
      const failed={engine:name,venue:pad(fixture.venue),race:raceKey(fixture),
       boats:0,error:String(error?.message||error).slice(0,300),noMocks:true};
      report.push(failed);
      console.error('PUBLIC_P2_24VENUE_CASE_ERROR '+JSON.stringify(failed));
     }
    }
   }finally{await browser.close();}
  }
  const good=report.filter(x=>x.boats===6);
  const missing=report.filter(x=>x.boats!==6);
  const originalCases=report.filter(x=>x.originalCompared>0);
  const summary={venues:24,cases:report.length,browsers:['chromium','webkit'],
   sixBoatCases:good.length,originalCsvCases:originalCases.length,
   originalCsvFieldComparisons:originalCases.reduce((n,x)=>n+x.originalCompared,0),
   unavailableCases:missing.length,
   uncovered:missing.map(x=>({engine:x.engine,race:x.race,http:x.renderHttp||null,error:x.error||null})),
   noMocks:true,formalT12:false,liveOfficial24Certified:false};
  assert.equal(report.length,48,'Not all 24 venues inspected in both browsers');
  assert.equal(originalCases.length,46,'23 providing venues were not independently checked in both browsers');
  console.log('PUBLIC_P2_24VENUE_DIAGNOSTIC '+JSON.stringify(summary));
  // Keep the P2 gate red until EVERY held historical race has real source
  // and six-boat display. No fake racer, exhibition, or result backfill.
  assert.equal(missing.length,0,'24-venue source/display coverage incomplete');
 }finally{await ctx.dispose();}
})().catch(error=>{
 console.error('PUBLIC_P2_24VENUE_GATE_FAIL '+(error.stack||String(error)));
 process.exitCode=1;
});
