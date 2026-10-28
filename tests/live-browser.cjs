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
    return {viewport:document.documentElement.clientWidth,documentWidth:document.documentElement.scrollWidth,
      bounds:{left:rect.left,right:rect.right},parent:{left:parent.left,right:parent.right,width:parent.width},rows,synthetic};
   });
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
