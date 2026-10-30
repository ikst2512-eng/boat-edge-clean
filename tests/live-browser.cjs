const { chromium } = require('playwright');
const fs=require('node:fs');
(async()=>{
 const browser=await chromium.launch({headless:true});
 const page=await browser.newPage({viewport:{width:390,height:844}});
 const errors=[];
 fs.mkdirSync('test-results',{recursive:true});
 try{
  page.on('pageerror',e=>errors.push(e.message));
  const site=process.env.CLEAN_SITE_URL || 'https://ikst2512-eng.github.io/boat-edge-clean/';
  const isRender=new URL(site).hostname.endsWith('.onrender.com');
  let response;
  for(let attempt=1;attempt<=12;attempt++){
   response=await page.goto(site,{waitUntil:'domcontentloaded',timeout:45000});
   if(response?.status()!==703 || !isRender)break;
   console.log('Render is waking (HTTP 503), retry '+attempt+'/12');
   await page.waitForTimeout(6000);
  }
  if(!response||!response.ok())throw Error('Published site unavailable: '+response?.status());
  await page.locator('#venueChooser .grid button').first().waitFor();
  const venues=await page.locator('#venueChooser .grid button').count();
  if(venues!==24)throw Error('Expected 24 venue buttons; found '+venues);
  const raceButtons=page.locator('.races button');
  if(await raceButtons.count()!==12)throw Error('Expected twelve race selector buttons');
  if(await page.locator('#homeRaceCardList').count()!==1)throw Error('STALE_DEPLOYMENT: missing new six-boat home race cards');
  if(await page.locator('#resultList').count()!==1)throw Error('Missing result race list');
  // The upstream CSV may not be published; verify UI wiring without inventing racers.
  await page.evaluate(()=>{setView('home');});
  await page.waitForTimeout(300);
  const cardCount=await page.locator('#homeRaceCardList .clean-race-card').count();
  if(cardCount>0){
   const first=page.locator('#homeRaceCardList .clean-race-card').first();
   if(await first.locator('.clean-race-lane').count()!==6)throw Error('A home race card must show exactly six boats');
   if(await first.locator('.clean-race-actions button').count()<1)throw Error('Home race card must provide a navigation action');
  }
  console.log('HOME_RACE_CARDS '+cardCount+' (zero may mean schedule/CSV not published)');
  // Independently published 2026-10-28 snapshot contains 01/1R.
  // Verify actual CSV-derived names/classes and rendered text, not synthetic boat names.
  await page.evaluate(()=>{datePinned=true;venueTouched=true;s.date='2026-10-28';s.venue=0;s.race=1;setView('home');render();});
  const published=await page.evaluate(async()=>{const rows=await cleanListRaceCards('2026-10-28',1);const record=rows.get(1);return record?{name:record['艇1_選手名'],grade:record['艇1_級別'],count:rows.size}:null;});
  if(published?.name&&published.name!=='未提供'){
   await page.waitForFunction(name=>[...document.querySelectorAll('#homeRaceCardList .clean-racer-name')].some(el=>el.textContent===name),published.name,{timeout:15000});
   const first=page.locator('#homeRaceCardList .clean-race-card').first();
   if(await first.locator('.clean-race-lane').count()!==6)throw Error('Published six-boat racecard incomplete');
   if((await first.locator('.clean-racer-name').first().innerText())!==published.name)throw Error('Racer name mismatch with published CSV');
   if((await first.locator('.clean-racer-class').first().innerText())!==(published.grade||'—'))throw Error('Racer grade mismatch with published CSV');
   const expected=await page.evaluate(async()=>{
    const [titles,cards]=await Promise.all([cleanListRaceTitles('2026-10-28',1),cleanListRaceCards('2026-10-28',1)]);
    const title=titles.get(1),racer=cards.get(1);
    return {title:title?.['レース名']||null,grade:title?.['グレード']||null,branch:racer?.['艇1_支部']||null,st:racer?.['艇1_全国平均ST']||null};
   });
   if(expected.title){
    await page.waitForFunction(name=>[...document.querySelectorAll('#homeRaceCardList .clean-race-tag')].some(el=>el.textContent===name),expected.title,{timeout:15000});
    const rendered=await first.locator('.clean-race-tag').allInnerTexts();
    if(!rendered.includes(expected.title))throw Error('Published race name mismatch: '+JSON.stringify({expected,rendered}));
   }
   if(expected.grade&&expected.grade!=='IP'&&expected.title){
    if((await first.locator('.clean-race-grade').first().innerText())!==expected.grade)throw Error('Published grade mismatch');
   }
   const extra=await first.locator('.clean-racer-extra').first().innerText();
   if(expected.branch&&!extra.includes('支部 '+expected.branch))throw Error('Published racer branch mismatch');
   if(expected.st&&Number.isFinite(Number(expected.st))&&!extra.includes('ST '+Number(expected.st).toFixed(2)))throw Error('Published average ST mismatch');
   console.log('PUBLISHED_RACE_TAGS '+JSON.stringify({title:expected.title?'verified':'not_published',grade:expected.grade?'verified':'not_published',branch:expected.branch?'verified':'not_published',st:expected.st?'verified':'not_published'}));
   console.log('PUBLISHED_RACE_CARD_PASS 20261028 01 1R source_rows='+published.count);
  }else{
   console.log('PUBLISHED_RACE_CARD_UNVERIFIED CSV unavailable; do not claim live racer data passed');
  }
  if(isRender){
   for(const date of ['invalid-date',new Date().toLocaleDateString('en-CA',{timeZone:'Asia/Tokyo'}).replaceAll('-','')]){
    const response=await page.request.get(new URL('/api/clean-schedule?date='+date,site).href,{timeout:20000});
    const data=await response.json();
    if(date==='invalid-date'){
     if(response.status()!==400||data.status!=='invalid_date')throw Error('Invalid schedule date must be 400');
    }else{
     const allowed={200:'published_schedule',404:'schedule_not_published',502:'source_invalid',503:'source_unavailable',500:'internal_error'};
     if(allowed[response.status()]!==data.status)throw Error('Schedule classification mismatch: '+response.status()+'/'+data.status);
     console.log('LIVE_SCHEDULE '+date+' '+response.status()+' '+data.status);
    }
   }
  }
  // Certified 2026-10-28 Karatsu 12R: saved before-deadline verified hit,
  // official finish 1-4-5. Inspect real rendered verdict rather than a mock.
  await page.evaluate(()=>{datePinned=true;venueTouched=true;s.date='2026-10-28';s.venue=22;s.race=12;setView('result');render();});
  const hitCard=page.locator('#resultList .clean-race-card').nth(11);
  await hitCard.locator('.clean-race-verdict').waitFor({timeout:60000});
  if((await hitCard.locator('.clean-race-verdict').innerText())!=='◎ 予想的中')throw Error('Verified Karatsu 12R hit badge missing');
  if((await hitCard.locator('.clean-race-state').innerText())!=='結果確定')throw Error('Confirmed result must be independently labelled');
  if(!(await hitCard.locator('.clean-race-foot').innerText()).includes('1 - 4 - 5'))throw Error('Wrong official finish on hit card');
  console.log('PUBLISHED_VERIFIED_HIT_PASS 20261028 23 12R: 1-4-5');
  // Unverified labels must never be rendered as a verified hit.
  const labels=await page.locator('#resultList .clean-race-verdict').allInnerTexts();
  if(labels.some(x=>!['◎ 予想的中','予想不的中','予想未検証'].includes(x)))throw Error('Unknown result verification badge');
  // Actual archived, independently verified miss: Karatsu 9R on 2026-10-28.
  const missCard=page.locator('#resultList .clean-race-card').nth(8);
  const missProof=await page.evaluate(async()=>{
   const key='20261028-23-09';
   try{const proof=await verifiedFourModeRace(key);return {status:'valid',finish:proof.official_finish,modes:Object.values(proof.modes).map(m=>m.hit)}}
   catch(e){return {status:'error',error:String(e)}}
  });
  const actualMiss=await missCard.locator('.clean-race-verdict').innerText();
  const missDisplay=await missCard.evaluate(el=>({state:el.querySelector('.clean-race-state')?.textContent,foot:el.querySelector('.clean-race-foot')?.textContent}));
  console.log('MISS_PROOF_DIAGNOSTIC '+JSON.stringify({missProof,actualMiss,missDisplay}));
  if(actualMiss==='◎ 予想的中')throw Error('False hit displayed for verified miss Karatsu 9R');
  if(actualMiss==='予想不的中')console.log('PUBLISHED_VERIFIED_MISS_PASS 20261028 23 9R');
  else throw Error('Verified miss not rendered: '+JSON.stringify({missProof,actualMiss,missDisplay}));
  if((await missCard.locator('.clean-race-state').innerText())!=='結果確定')throw Error('Confirmed Karatsu 9R result missing');
  // A date whose result has not happened must remain pending, not a miss.
  await page.evaluate(()=>{datePinned=true;venueTouched=true;s.date='2026-11-05';s.venue=22;s.race=1;setView('result');render();});
  await page.locator('#resultList .clean-race-verdict').first().waitFor({timeout:60000});
  const future=await page.locator('#resultList .clean-race-card').first().evaluate(el=>({
   status:el.querySelector('.clean-race-state')?.textContent,
   verdict:el.querySelector('.clean-race-verdict')?.textContent
  }));
  if(future.verdict!=='予想未検証'||future.status==='結果確定')throw Error('Future unconfirmed result falsely classified: '+JSON.stringify(future));
  console.log('PENDING_RESULT_PASS '+JSON.stringify(future));
  // Deliberately synthetic forecast data: measure real published CSS, not model accuracy.
  await page.setViewportSize({width:375,height:844});
  await page.evaluate(()=>{
   setView('forecast');
   predictionModes={hit:{tickets:['1-2-3','1-3-2'],probabilities:{'1-2-3':28.25,'1-3-2':16.5},odds:{}},balance:{tickets:[],probabilities:{},odds:{}},hole:{tickets:[],probabilities:{},odds:{}},narrow:{tickets:[],probabilities:{},odds:{}}};
   selectedPredictionMode='hit';applyPredictionMode();
  });
  const compact=await page.locator('#predictionRows .prediction-row').first().evaluate(el=>{
   const row=el.getBoundingClientRect(),boats=el.querySelector('.ticket-boats'),text=el.querySelector('.prediction-ticket'),odds=el.querySelector('.prediction-odds');
   return {height:row.height,width:row.width,right:row.right,viewport:document.documentElement.clientWidth,
     colored:boats&&getComputedStyle(boats).display!=='none',duplicateHidden:text&&getComputedStyle(text).display==='none',
     probability:odds?.textContent?.includes('28.25%'),stake:odds?.textContent?.includes('円')};
  });
  if(compact.height>78||compact.right>compact.viewport+2||!compact.colored||!compact.duplicateHidden||!compact.probability||!compact.stake)
   throw Error('Forecast tickets not compact/complete at 375px: '+JSON.stringify(compact));
  console.log('COMPACT_FORECAST_PASS '+JSON.stringify(compact));
  // Test the current single-document UI without assuming server-side route rewrites.
  for(const width of [320,360,375,390]){
   await page.setViewportSize({width,height:844});
   await page.goto(site,{waitUntil:'domcontentloaded',timeout:45000});
   await page.evaluate(()=>setView('card'));
   await page.locator('#mobileRaceMatrix').waitFor({state:'visible'});
   // Test the actual CSS with a synthetic six-boat matrix if no race feed is available.
   const geometry=await page.evaluate(()=>{
    const panel=document.querySelector('#mobileRaceMatrix');
    let table=panel.querySelector('table'),synthetic=false;
    if(!table){
     synthetic=true;
     table=document.createElement('table');table.className='boat-matrix-table';
     const thead=document.createElement('thead'),heading=document.createElement('tr');
     ['項目','1','2','3','4','5','6'].forEach(value=>{const cell=document.createElement('th');cell.textContent=value;heading.append(cell)});
     thead.append(heading);table.append(thead);
     const tbody=document.createElement('tbody');
     for(const label of ['選手','全国勝率','展示タイム','チルト']){
      const tr=document.createElement('tr'),th=document.createElement('th');th.textContent=label;tr.append(th);
      for(let n=0;n<6;n++){const td=document.createElement('td');td.textContent=label==='選手'?'テスト選手名':'—';tr.append(td)}
      tbody.append(tr);
     }
     table.append(tbody);panel.replaceChildren(table);
    }
    const rect=table.getBoundingClientRect();
    const parent=panel.getBoundingClientRect();
    const rows=[...table.querySelectorAll('tbody tr th')].map(x=>x.textContent.trim());
    const tableStyle=getComputedStyle(table),panelStyle=getComputedStyle(panel);
    return {viewport:document.documentElement.clientWidth,documentWidth:document.documentElement.scrollWidth,
      bounds:{left:rect.left,right:rect.right},parent:{left:parent.left,right:parent.right,width:parent.width},rows,synthetic,
      style:{tableLayout:tableStyle.tableLayout,width:tableStyle.width,minWidth:tableStyle.minWidth,maxWidth:tableStyle.maxWidth,panelOverflow:panelStyle.overflowX},
      sourceHasFitRule:[...document.styleSheets].some(sheet=>{try{return [...sheet.cssRules].some(rule=>rule.cssText.includes('#mobileRaceMatrix .boat-matrix-table'))}catch(_){return false}})};
   });
   console.log('MATRIX_DIAGNOSTIC '+width+'px '+JSON.stringify(geometry));
   if(!geometry.sourceHasFitRule)
    throw Error('STALE_DEPLOYMENT: published HTML lacks #mobileRaceMatrix .boat-matrix-table mobile fit CSS at '+site+'; inspect deployed commit/build before editing CSS');
   if(geometry.bounds.right>geometry.viewport+2||geometry.bounds.left< -2)
    throw Error('Mobile race matrix overflow at '+width+'px: '+JSON.stringify(geometry));
   if(geometry.rows.filter(x=>x==='チルト').length!==1||geometry.rows.filter(x=>x==='展示タイム').length!==1)
    throw Error('Duplicated exhibition fields at '+width+'px');
   console.log('PASS matrix '+width+'px; synthetic fixture='+geometry.synthetic);
  }
  if(errors.length)throw Error('Browser errors: '+errors.join(' | '));
  console.log('PASS: current page navigation and matrix CSS geometry checks; fixture runs are not proof of live race data');
 }catch(e){
  console.error('Live browser smoke FAILED:',e);
  await page.screenshot({path:'test-results/live-browser-failure.png',fullPage:true}).catch(()=>{});
  fs.writeFileSync('test-results/browser-errors.txt',errors.join('\n')+'\n'+String(e));
  process.exitCode=1;
 }finally{await browser.close()}
})();
