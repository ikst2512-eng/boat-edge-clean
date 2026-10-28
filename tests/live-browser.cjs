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
   if(response?.status()!==503 || !isRender)break;
   console.log('Render is waking (HTTP 503), retry '+attempt+'/12');
   await page.waitForTimeout(6000);
  }
  if(!response||!response.ok())throw Error('Published site unavailable: '+response?.status());
  await page.locator('#venueChooser .grid button').first().waitFor();
  const venues=await page.locator('#venueChooser .grid button').count();
  if(venues!==24)throw Error('Expected 24 venue buttons; found '+venues);
  const links=page.locator('.view-tabs a[data-page]');
  if(await links.count()!==5)throw Error('Expected five page links in current navigation');
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
   if(await first.locator('.clean-race-actions button').count()!==6)throw Error('Home race card must have six navigation actions');
  }
  console.log('HOME_RACE_CARDS '+cardCount+' (zero may mean schedule/CSV not published)');
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
  // Test the current single-document UI without assuming server-side route rewrites.
  if(await page.locator('.view-tabs a[data-page]').count()!==5)throw Error('Five current page links missing');
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
