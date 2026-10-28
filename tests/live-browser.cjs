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
  await page.locator('#venueChooser .grid button').nth(3).click();
  await raceButtons.nth(1).click();
  const destination=new URL(page.url());
  if(destination.searchParams.get('venue')!=='4'||destination.searchParams.get('race')!=='2')
   throw Error('Venue/race selection not synchronized');
  for(const route of ['forecast','exhibition','card','results','review']){
   const target=new URL(route,site);
   target.searchParams.set('venue','4');
   target.searchParams.set('race','2');
   const response=await page.goto(target.toString(),{waitUntil:'domcontentloaded',timeout:45000});
   if(!response?.ok())throw Error('Route unavailable: '+route+' HTTP '+response?.status());
   const nav=page.locator('.view-tabs a[data-page="'+({exhibition:'exhibit',results:'result'}[route]||route)+'"]');
   if(await nav.count()!==1)throw Error('Missing navigation for '+route);
  }
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
  console.log('PASS: five navigation pages, venue/race selection and mobile geometry checks');
 }catch(e){
  console.error('Live browser smoke FAILED:',e);
  await page.screenshot({path:'test-results/live-browser-failure.png',fullPage:true}).catch(()=>{});
  fs.writeFileSync('test-results/browser-errors.txt',errors.join('\n')+'\n'+String(e));
  process.exitCode=1;
 }finally{await browser.close()}
})();
