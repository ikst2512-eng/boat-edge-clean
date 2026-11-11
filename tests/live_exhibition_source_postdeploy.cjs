'use strict';
// Production-only read-only acceptance: actual archived original CSV vs
// actual 390px Pages DOM in Chromium and WebKit. No routes, fixtures or mocks.
// Distinguish historical Render->DOM replay from official real-time source proof.
const {chromium,webkit,request}=require('playwright');
const assert=require('node:assert/strict');
const crypto=require('node:crypto');
const PAGE='https://ikst2512-eng.github.io/boat-edge-clean/';
const API='https://boat-edge-clean.onrender.com/api/clean-racecard';
const fixtures=[
  {day:'2026-10-28',venue:'01',race:1},
  {day:'2026-10-31',venue:'07',race:8},
  {day:'2026-11-02',venue:'19',race:5},
  {day:'2026-11-03',venue:'19',race:11},
  {day:'2026-11-10',venue:'11',race:6,missingSix:true},
];
const code=f=>f.day.replaceAll('-','')+f.venue+String(f.race).padStart(2,'0');
const key=f=>f.day.replaceAll('-','')+'-'+f.venue+'-'+String(f.race).padStart(2,'0');
function parseCsv(line){
 const out=[];let value='',quoted=false;
 for(let i=0;i<line.length;i++){const ch=line[i];
  if(ch==='"'){if(quoted&&line[i+1]==='"'){value+='"';i++}else quoted=!quoted;}
  else if(ch===','&&!quoted){out.push(value);value='';}
  else value+=ch;
 }
 out.push(value);return out;
}
const csvCache=new Map();
async function sourceCsv(ctx,day){
 if(csvCache.has(day))return csvCache.get(day);
 const url='https://boatracecsv.github.io/data/previews/original_exhibition/'+day.replaceAll('-','/')+'.csv';
 let res;
 for(let i=0;i<3;i++){try{res=await ctx.get(url,{timeout:35000});
   if(res.status()===200)break;
 }catch(e){if(i===2)throw e;}if(i<2)await new Promise(resolve=>setTimeout(resolve,1000*(i+1)));}
 assert.equal(res?.status(),200,'Independent original CSV unavailable '+day);
 const buffer=await res.body(),raw=buffer.toString('utf8').replace(/^\uFEFF/,'');
 const rows=raw.split(/\r?\n/).filter(Boolean).map(parseCsv);
 const header=rows.shift();
 assert.ok(header&&header.length===34&&header.length===new Set(header).size,'Original source schema invalid '+day);
 const columns=Object.fromEntries(header.map((h,i)=>[h,i]));
 const source={rows,columns,sha256:crypto.createHash('sha256').update(buffer).digest('hex')};
 csvCache.set(day,source);return source;
}
async function showExhibit(page,f){
 const url=new URL(PAGE);
 for(const [k,v] of [['date',f.day],['venue',f.venue],['race',String(f.race)],['view','exhibit']])url.searchParams.set(k,v);
 const res=await page.goto(url.href,{waitUntil:'domcontentloaded',timeout:45000});
 assert.equal(res?.status(),200,'Published Pages unavailable '+code(f));
 await page.evaluate(()=>{datePinned=true;venueTouched=true;venueSpecified=true;setView('exhibit');render()});
 await page.waitForFunction(expected=>
    sameRaceKey()===expected&&activeView==='exhibit'&&
    document.querySelectorAll('#exhibitionGrid .exhibition-boat').length===6 &&
    document.querySelector('#originalExhibitionStatus')?.dataset.originalState,
    key(f),{timeout:45000});
 return page.evaluate(()=>({
   key:sameRaceKey(),
   status:document.querySelector('#originalExhibitionStatus')?.textContent||'',
   state:document.querySelector('#originalExhibitionStatus')?.dataset.originalState||'',
   boats:[...document.querySelectorAll('#exhibitionGrid .exhibition-boat')].map(boat=>({
     lane:Number(boat.querySelector('.lane-badge')?.textContent),
     racer:boat.querySelector('.exhibition-name')?.textContent||'',
     official:Object.fromEntries([...boat.querySelectorAll('.exhibition-metric')].map(e=>
       [e.querySelector('span')?.textContent||'',e.querySelector('strong')?.textContent||''])),
     original:[...boat.querySelectorAll('.exhibition-original-metric')].map(e=>({
       label:e.querySelector('span')?.textContent||'',
       value:e.querySelector('strong')?.textContent||'',
       state:e.dataset.sourceValueState
     })),
     unavailable:boat.querySelector('.exhibition-original-pending')?.textContent||''
   }))
 }));
}
async function checkOriginal(page,ctx,f,engine){
 const source=await sourceCsv(ctx,f.day),{rows,columns:c}=source;
 const matched=rows.filter(row=>row[c['レースコード']]===code(f));
 assert.equal(matched.length,1,'Independent source does not have exactly one race '+code(f));
 const row=matched[0],count=Number(row[c['計測数']]);
 assert.ok(Number.isInteger(count)&&count>=1&&count<=3,'Invalid source measurements '+code(f));
 assert.equal(row[c['レース日']],f.day,'CSV date mismatch');
 assert.equal(Number(row[c['レース場']]),Number(f.venue),'CSV venue mismatch');
 assert.equal(Number(String(row[c['レース回']]).replace(/R$/i,'')),f.race,'CSV race mismatch');
 const got=await showExhibit(page,f);
 assert.equal(got.key,key(f));
 assert.equal(got.boats.length,6);
 let missing=0;
 for(let lane=1;lane<=6;lane++){
   const boat=got.boats[lane-1];
   assert.equal(boat.lane,lane,'Wrong display lane '+code(f));
   assert.equal(Object.keys(boat.official).length,5,'Five official display fields missing');
   assert.equal(boat.original.length,count,'Source measurement count differs '+code(f));
   for(let k=1;k<=count;k++){
     const label=String(row[c['計測項目'+k]]||'').trim();
     const sourceValue=String(row[c['艇'+lane+'_値'+k]]??'').trim();
     assert.ok(label,'Missing source label '+code(f));
     const shown=boat.original[k-1];
     assert.equal(shown.label,label,'Original item label incorrect '+code(f));
     assert.equal(shown.value,sourceValue||'—','Original boat reading incorrect '+code(f)+' lane '+lane+' metric '+k);
     assert.equal(shown.state,sourceValue?'present':'missing','Source missingness altered '+code(f));
     if(!sourceValue)missing++;
   }
 }
 const expectedPartial=missing>0;
 assert.ok(expectedPartial?got.state.startsWith('partial_'):['verified','deadline_mismatch'].includes(got.state),
   'Wrong original source state '+code(f)+' '+got.state);
 if(f.missingSix)assert.equal(missing,6,'Known real blank-cells case changed '+code(f));
 assert.ok(got.status.includes('初回保存証明は未検証'),'Must not imply formal T-12 original source '+code(f));
 console.log('PUBLIC_P2_ORIGINAL_SIX_BOAT_PASS '+JSON.stringify({
   engine,race:code(f),boats:6,labelsPerBoat:count,compared:6*count,
   missing,sourceSha256:source.sha256,state:got.state,noMocks:true
 }));
}
async function checkEdogawa(page,engine){
 // Actual published six-racer race, not a fabricated API or a route stub.
 const f={day:'2026-10-28',venue:'03',race:1};
 const got=await showExhibit(page,f);
 assert.equal(got.state,'non_provided','Edogawa must mean upstream structurally unavailable, not HTTP 404');
 assert.ok(got.status.includes('江戸川')&&got.status.includes('計測対象外'));
 for(let i=0;i<6;i++){
   assert.equal(got.boats[i].lane,i+1);
   assert.equal(got.boats[i].original.length,0,'Invented Edogawa original measures');
   assert.equal(got.boats[i].unavailable,'オリ展：非提供');
   assert.equal(Object.keys(got.boats[i].official).length,5,'Normal exhibition fields missing in Edogawa');
 }
 console.log('PUBLIC_P2_EDOGAWA_NOT_PROVIDED_PASS '+JSON.stringify({engine,race:code(f),boats:6,noMocks:true}));
}
async function checkOfficialReplay(page,ctx,engine){
 // This compares historical Render's audited beforeinfo with the currently
 // published DOM. It is NOT a new independent official network observation.
 const f={day:'2026-11-11',venue:'24',race:10};
 const url=API+'?hd=20261111&jcd=24&rno=10';
 let response;
 for(let attempt=1;attempt<=3;attempt++){
   try{response=await ctx.get(url,{timeout:40000});}
   catch(e){if(attempt===3)throw e;console.log('PUBLIC_P2_HISTORICAL_API_RETRY '+JSON.stringify({attempt,error:String(e).slice(0,120)}));continue;}
   if(response.status()===200)break;
   if(![429,500,502,503,504].includes(response.status())||attempt===3)break;
   console.log('PUBLIC_P2_HISTORICAL_API_RETRY '+JSON.stringify({attempt,status:response.status()}));
 }
 assert.equal(response?.status(),200,'Historical Render racecard unavailable; no official inference');
 const card=await response.json();
 assert.equal(card.race_key,key(f));
 const observedStatus=card.source_audit?.beforeinfo?.status;
 const got=await showExhibit(page,f);
 if(observedStatus==='not_verified_historical'){
   assert.equal(got.boats.length,6);
   let withheld=0;
   for(const boat of got.boats)for(const name of ['展示タイム','チルト','展示ST','展示進入']){
     assert.equal(boat.official[name],'—','Unverified historical official value leaked '+name+' boat '+boat.lane);
     withheld++;
   }
   assert.equal(withheld,24);
   console.log('PUBLIC_P2_HISTORICAL_OFFICIAL_WITHHELD_PASS '+JSON.stringify({
     engine,race:code(f),audit:observedStatus,withheld,source:'real public Render response and Pages DOM',noMocks:true,notOfficial24Pass:true
   }));
   return 'withheld';
 }
 assert.equal(observedStatus,'ok','Unknown historical official audit state');
 const observed=Date.parse(card.source_audit.beforeinfo.fetched_at);
 const deadline=Date.parse(f.day+'T'+card.meta.deadline+':00+09:00');
 assert.ok(Number.isFinite(observed)&&observed<deadline,'Historical official receipt not predeadline');
 assert.equal(card.beforeinfo?.racers?.length,6);
 assert.equal(card.beforeinfo?.start_exhibition?.length,6);
 let match=0;
 for(let lane=1;lane<=6;lane++){
   const official=card.beforeinfo.racers.find(x=>Number(x.lane)===lane);
   const start=card.beforeinfo.start_exhibition.find(x=>Number(x.lane)===lane);
   assert.ok(official&&start,'Missing historical official lane '+lane);
   const shown=got.boats[lane-1].official;
   for(const [label,val] of [
     ['展示タイム',String(official.exhibition_time)],
     ['チルト',String(official.tilt)],
     ['展示ST',String(start.st)],
     ['展示進入',String(start.course)+'C']
   ]){
     assert.equal(shown[label],val,'Published official field mismatch '+label+' lane '+lane);
     match++;
   }
 }
 assert.equal(match,24);
 console.log('PUBLIC_P2_HISTORICAL_OFFICIAL_RENDER_DOM_PASS '+JSON.stringify({
   engine,race:code(f),boats:6,fields:24,source:'audited historical Render record vs published DOM',notLiveOfficial:true,noMocks:true
 }));
}
(async()=>{
 const ctx=await request.newContext({timeout:35000});
 try{
   for(const [engineName,engine] of [['chromium',chromium],['webkit',webkit]]){
     const browser=await engine.launch({headless:true});
     try{
       const page=await browser.newPage({viewport:{width:390,height:844},isMobile:true,hasTouch:true});
       const errors=[];page.on('pageerror',e=>errors.push(e.message));
       for(const fixture of fixtures)await checkOriginal(page,ctx,fixture,engineName);
       await checkEdogawa(page,engineName);
       await checkOfficialReplay(page,ctx,engineName);
       assert.deepEqual(errors,[],'Page JS errors '+engineName);
     }finally{await browser.close();}
   }
   console.log('PUBLIC_P2_SIX_BOAT_CROSS_ENGINE_VERIFIED '+JSON.stringify({
     browsers:['chromium','webkit'],historicalOriginalRaces:fixtures.length,
     originalMeasurementsPerEngine:fixtures.length*18,
     nonProvided:'Edogawa',historicalOfficialFieldsCheckedPerEngine:24,mayBeWithheld:true,
     noMocks:true,formalT12:false
   }));
 }finally{await ctx.dispose();}
})().catch(e=>{console.error('PUBLIC_P2_SOURCE_GATE_FAIL',e.stack||String(e));process.exitCode=1});
