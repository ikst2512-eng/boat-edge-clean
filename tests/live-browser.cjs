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
  await page.locator('#venueChooser .grid button').nth(3).click();
  await page.locator('.races button').nth(1).click();
  for(const tab of await page.locator('.view-tabs [role="tab"]').all()){
   await tab.click();
   if(await tab.getAttribute('aria-selected')!=='true')throw Error('Tab did not become selected');
  }
  if(errors.length)throw Error('Browser errors: '+errors.join(' | '));
  console.log('PASS: published site renders 24 venues, 12 races, 4 tabs; tab switching works without JS errors');
 }catch(e){
  console.error('Live browser smoke FAILED:',e);
  await page.screenshot({path:'test-results/live-browser-failure.png',fullPage:true}).catch(()=>{});
  fs.writeFileSync('test-results/browser-errors.txt',errors.join('\n')+'\n'+String(e));
  process.exitCode=1;
 }finally{await browser.close()}
})();
