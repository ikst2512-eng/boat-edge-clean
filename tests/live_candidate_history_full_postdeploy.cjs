'use strict';
// Actual public Pages historical-candidate acceptance with BOTH browser engines.
// Not a forecast/backfill. Rebuild every manifest from untouched Git originals,
// prove byte identity to public Pages, and check that "全保存履歴" renders every
// saved candidate including unverified/missing results and payout disclosures.
const fs=require('node:fs');
const crypto=require('node:crypto');
const assert=require('node:assert/strict');
const {spawnSync}=require('node:child_process');
const {chromium,webkit}=require('playwright');
const SITE='https://ikst2512-eng.github.io/boat-edge-clean/';
const names=fs.readdirSync('prospective_predictions')
  .filter(name=>/^20\d{10}\.json$/.test(name)).sort();
const days=[...new Set(names.map(name=>name.slice(0,8)))].sort();
assert.ok(days.length>=10,'Historical source days unexpectedly absent');
const digest=bytes=>crypto.createHash('sha256').update(bytes).digest('hex');
const datestring=day=>day.slice(0,4)+'-'+day.slice(4,6)+'-'+day.slice(6);
const py=[
  'import json,hashlib,sys',
  'from candidate_history import daily_candidate_history',
  'out={}',
  'for day in sys.argv[1:]:',
  ' status,record=daily_candidate_history(day)',
  ' if status!=200 or not record.get("ok"): raise SystemExit("SOURCE_MANIFEST_INVALID "+day)',
  ' data=json.dumps(record,ensure_ascii=False,separators=(",",":"))+"\\n"',
  ' out[day]={"sha256":hashlib.sha256(data.encode("utf-8")).hexdigest(),"count":record["candidate_count"],"confirmed":record["confirmed_result_count"],"payout":record["payout_verified_count"]}',
  'print(json.dumps(out,separators=(",",":")))',
].join('\n');
const generated=spawnSync('python3',['-c',py,...days],{encoding:'utf8',maxBuffer:16*1024*1024,timeout:120000});
if(generated.status!==0)throw Error('SOURCE_MANIFEST_BUILD_FAIL '+String(generated.stderr).slice(0,500));
const source=JSON.parse(generated.stdout);
async function checkPublicManifest(request,day){
  const url=SITE+'candidate_history/'+day+'.json';
  const response=await request.get(url,{timeout:35000,headers:{'Cache-Control':'no-cache'}});
  assert.equal(response.status(),200,'Public manifest HTTP '+day);
  const bytes=await response.body();
  assert.equal(digest(bytes),source[day].sha256,'Public manifest bytes differ from Git-backed regeneration '+day);
  const record=JSON.parse(bytes.toString('utf8'));
  assert.equal(record.date,day);
  assert.equal(record.schema,'CLEAN_CANDIDATE_HISTORY_V1');
  assert.equal(record.production_forecast,false);
  assert.equal(record.first_git_add_verified,false);
  assert.equal(record.candidate_count,source[day].count);
  assert.equal(record.confirmed_result_count,source[day].confirmed);
  assert.equal(record.payout_verified_count,source[day].payout);
  const expected=names.filter(n=>n.startsWith(day)).map(n=>n.slice(0,12)).sort();
  const found=record.races.map(x=>x.race_code).sort();
  assert.deepEqual(found,expected,'Published race codes missing, duplicated, or post-hoc invented '+day);
  for(const row of record.races){
    const path='prospective_predictions/'+row.race_code+'.json';
    const raw=JSON.parse(fs.readFileSync(path,'utf8'));
    if(row.forecast_status==='saved_research_unattested'){
      assert.deepEqual(row.tickets,raw.predictions,'Frozen ticket order changed '+row.race_code);
      assert.equal(row.generated_at_jst,raw.generated_at,'Saved forecast time changed '+row.race_code);
    }else{
      assert.equal(row.forecast_status,'unverified');
      assert.deepEqual(row.tickets,[],'Invalid source gained fabricated tickets '+row.race_code);
    }
    if(row.result_status==='confirmed_archive'){
      const confirmed=JSON.parse(fs.readFileSync('confirmed_results/'+row.race_code+'.json','utf8'));
      assert.equal(row.finish,confirmed.finish_order.join('-'),'Saved confirmed finish differs '+row.race_code);
    }else assert.equal(row.finish,null,'Unverified result gained invented finish '+row.race_code);
    if(row.payout_status==='verified_independent'){
      assert.equal(row.result_status,'confirmed_archive','Payout without confirmed result '+row.race_code);
      assert.ok(Number.isInteger(row.payout_yen_per_100)&&row.payout_yen_per_100>=100);
    }else assert.equal(row.payout_yen_per_100,null,'Unverified payout gained amount '+row.race_code);
  }
  console.log('PUBLIC_P1_ORIGINAL_MANIFEST_PASS '+JSON.stringify({day,rows:record.candidate_count,confirmed:record.confirmed_result_count,payout:record.payout_verified_count,sha256:source[day].sha256}));
  return record;
}
async function checkBrowser(engine,name,records){
  const browser=await engine.launch({headless:true});
  try{
    const page=await browser.newPage({viewport:{width:390,height:844},isMobile:true,hasTouch:true});
    const errors=[];
    page.on('pageerror',e=>errors.push(String(e).slice(0,240)));
    const first=days[0];
    const response=await page.goto(SITE+'candidates.html?date='+datestring(first),{waitUntil:'domcontentloaded',timeout:45000});
    assert.equal(response?.status(),200,'Public candidate HTML HTTP '+name);
    for(let i=0;i<days.length;i++){
      const day=days[i],date=datestring(day),record=records[day];
      if(i>0){
        await page.locator('#candidateHistoryDate').fill(date);
        await page.locator('#candidateHistoryDate').dispatchEvent('change');
      }
      await page.waitForFunction(({date,count})=>
        new URLSearchParams(location.search).get('date')===date&&
        document.querySelector('#candidateStatus')?.textContent?.startsWith('保存候補 '+count+'件'),
        {date,count:record.candidate_count},{timeout:35000});
      await page.locator('#candidateHistoryFilters button[data-candidate-filter="all"]').click();
      await page.waitForFunction(count=>
        document.querySelectorAll('#candidateCards > details.candidate-history-card').length===count,
        record.candidate_count,{timeout:35000});
      const visible=await page.evaluate(()=>
        [...document.querySelectorAll('#candidateCards > details.candidate-history-card')].map(n=>({
          code:n.dataset.raceCode,
          summary:n.querySelector('summary')?.textContent||'',
          detail:n.querySelector('.candidate-detail')?.textContent||''
        })));
      assert.deepEqual(visible.map(x=>x.code),record.races.map(x=>x.race_code),
        'Browser list omitted or reordered retained rows '+name+' '+day);
      for(let j=0;j<record.races.length;j++){
        const row=record.races[j],shown=visible[j];
        assert.ok(shown.summary.includes('買い未認定'),'Unsafe purchase verdict '+row.race_code);
        if(row.result_status==='confirmed_archive'){
          assert.ok(shown.summary.includes('確定 '+row.finish),'Confirmed result not visible '+row.race_code);
        }else if(row.result_status==='unverified'){
          assert.ok(shown.summary.includes('結果原本の検証待ち'),'Unverified result misrepresented '+row.race_code);
        }else{
          assert.ok(shown.summary.includes('結果未保存'),'Missing result misrepresented '+row.race_code);
        }
        if(row.forecast_status==='saved_research_unattested')
          assert.ok(shown.detail.includes(row.tickets.join(' ／ ')),'Frozen forecast tickets not shown '+row.race_code);
        if(row.payout_status==='verified_independent')
          assert.ok(shown.detail.includes(row.payout_yen_per_100.toLocaleString('ja-JP')+'円'),'Verified payout not shown '+row.race_code);
        else assert.ok(shown.detail.includes('3連単払戻：未確認')||row.result_status!=='confirmed_archive',
          'Unverified payout should remain blank '+row.race_code);
        assert.ok(shown.detail.includes('正式認定'),'Research disclaimer missing '+row.race_code);
      }
      console.log('LIVE_P1_FULL_HISTORY_DOM_PASS '+JSON.stringify({
        engine:name,day,sourceRows:record.candidate_count,browserRows:visible.length,
        saved:record.races.filter(x=>x.forecast_status==='saved_research_unattested').length,
        payouts:record.payout_verified_count,noMocks:true
      }));
    }
    assert.deepEqual(errors,[],'Published candidate page JavaScript errors '+name);
  }finally{await browser.close();}
}
(async()=>{
  const browser=await chromium.launch({headless:true});
  let request;
  try{request=await browser.newContext();const records={};
    for(const day of days)records[day]=await checkPublicManifest(request.request,day);
    await checkBrowser(chromium,'chromium',records);
    await checkBrowser(webkit,'webkit',records);
    const total=days.reduce((n,d)=>n+records[d].candidate_count,0);
    console.log('LIVE_P1_ALL_SAVED_CANDIDATES_VERIFIED '+JSON.stringify({
      days:days.length,rows:total,engines:['chromium','webkit'],
      source:'Git source regenerated + byte-identical public manifests + all DOM records',
      noMocks:true,formalPredictionsCertified:false
    }));
  }finally{if(request)await request.close();await browser.close();}
})().catch(error=>{console.error('LIVE_P1_HISTORY_FAIL '+(error.stack||String(error)));process.exitCode=1;});
