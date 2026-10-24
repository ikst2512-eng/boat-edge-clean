const { chromium } = require('playwright');
const fs=require('node:fs');
(async()=>{
 const browser=await chromium.launch({headless:true});
 const page=await browser.newPage({viewport:{width:390,height:844}});
 const errors=[];
 fs.mkdirSync('test-results',{recursive:true});
 try{
  page.on('pageerror',e=>errors.push(e.message));
  const response=await page.goto('https://ikst2512-eng.github.io/boat-edge-clean/',{waitUntil:'domcontentloaded',timeout:45000});
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
   const panel=view==='forecast'?'#forecast':view==='result'?'#resultSection':'#raceDataSection';
   if(!await page.locator(panel).isVisible())throw Error(view+' panel not visible');
   if(view==='exhibit'&&!await page.locator('#exhibitionGrid').isVisible())throw Error('Exhibition grid hidden');
  }
  destination=new URL(page.url());
  if(destination.searchParams.get('venue')!=='4'||destination.searchParams.get('race')!=='2')throw Error('Tabs changed selected race');
  if(errors.length)throw Error('Browser errors: '+errors.join(' | '));
  console.log('PASS: published site renders 24 venues, 12 races, 4 panels; venue/race selections and deep-link query persist');
 }catch(e){
  console.error('Live browser smoke FAILED:',e);
  await page.screenshot({path:'test-results/live-browser-failure.png',fullPage:true}).catch(()=>{});
  fs.writeFileSync('test-results/browser-errors.txt',errors.join('\n')+'\n'+String(e));
  process.exitCode=1;
 }finally{await browser.close()}
})();
