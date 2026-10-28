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
  const tabs=await page.locator('.view-tabs [role="tab"]').count();
  if(tabs!==4)throw Error('Expected 4 tabs; found '+tabs);
  const raceButtons=await page.locator('.races button').count();
  if(raceButtons!==12)throw Error('Expected 12 race selector buttons; found '+raceButtons);
  const selectedVenue=page.locator('#venueChooser .grid button').nth(3);
  await selectedVenue.click();
  if(await selectedVenue.getAttribute('aria-pressed')!=='true')throw Error('Venue selection did not update');
  const secondRace=page.locator('.races button').nth(1);
  await secondRace.click();
  if(await secondRace.getAttribute('aria-pressed')!=='true')throw Error('Race selection did not update');
  let destination=new URL(page.url());
  if(destination.searchParams.get('venue')!=='4'||destination.searchParams.get('race')!=='2')throw Error('Selected race URL not synchronized');
  for(const view of ['card','exhibit','forecast','result']){
   const tab=page.locator('.view-tabs [role="tab"][data-view="'+view+'"]');
   await tab.click();
   if(await tab.getAttribute('aria-selected')!=='true')throw Error(view+' tab did not become selected');
   if(new URL(page.url()).searchParams.get('view')!==view)throw Error(view+' URL view parameter not synchronized');
   const panel=view==='forecast'?'#forecast':view==='result'?'#resultSection':'#raceDataSection';
   if(!await page.locator(panel).isVisible())throw Error(view+' panel not visible');
   if(view==='exhibit' && await page.locator('#exhibitionGrid').evaluate(el=>el.hidden))throw Error('Exhibition grid hidden attribute remains set');
  }
  destination=new URL(page.url());
  if(destination.searchParams.get('venue')!=='4'||destination.searchParams.get('race')!=='2')throw Error('Tabs changed selected race');
  await page.reload({waitUntil:'domcontentloaded'});
  if(new URL(page.url()).searchParams.get('view')!=='result')throw Error('View query lost on reload');
  const selectedResultTab=page.locator('.view-tabs [role="tab"][data-view="result"]');
  await selectedResultTab.waitFor();
  if(await selectedResultTab.getAttribute('aria-selected')!=='true')throw Error('Result view not restored on reload');
  if(await page.locator('#venueChooser .grid button').nth(3).getAttribute('aria-pressed')!=='true')throw Error('Venue not restored on reload');
  if(await page.locator('.races button').nth(1).getAttribute('aria-pressed')!=='true')throw Error('Race not restored on reload');
  // Verify small-screen geometry rather than only static CSS declarations.
  for(const width of [320,360,375,390]){
   await page.setViewportSize({width,height:844});
   await page.goto(new URL('/card',site).toString(),{waitUntil:'domcontentloaded',timeout:45000});
   await page.locator('#mobileRaceMatrix').waitFor();
   // Source data may be unavailable. Assert the matrix geometry whenever a table exists.
   const geometry=await page.evaluate(()=>{
    const panel=document.querySelector('#mobileRaceMatrix');
    const table=panel?.querySelector('table');
    const rect=table?.getBoundingClientRect();
    return {viewport:document.documentElement.clientWidth,documentWidth:document.documentElement.scrollWidth,
      table:rect?{left:rect.left,right:rect.right,width:rect.width}:null,
      matrixRows:table?[...table.querySelectorAll('tbody tr th')].map(x=>x.textContent.trim()):[]};
   });
   if(geometry.table){
    if(geometry.table.right>geometry.viewport+2 || geometry.table.left< -2)
     throw Error('Mobile race matrix overflow at '+width+'px: '+JSON.stringify(geometry));
    if(geometry.matrixRows.filter(x=>x==='チルト').length!==1 || geometry.matrixRows.filter(x=>x==='展示タイム').length!==1)
     throw Error('Mobile matrix duplicated tilt/exhibition at '+width+'px');
   }
   console.log('Mobile matrix geometry checked at '+width+'px; rendered='+Boolean(geometry.table));
  }
  if(errors.length)throw Error('Browser errors: '+errors.join(' | '));
  console.log('PASS: published site renders 24 venues, 12 races, 4 panels; venue/race selections and deep-link query persist');
 }catch(e){
  console.error('Live browser smoke FAILED:',e);
  await page.screenshot({path:'test-results/live-browser-failure.png',fullPage:true}).catch(()=>{});
  fs.writeFileSync('test-results/browser-errors.txt',errors.join('\n')+'\n'+String(e));
  process.exitCode=1;
 }finally{await browser.close()}
})();
