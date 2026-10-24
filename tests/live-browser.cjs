const { chromium } = require('playwright');
(async()=>{
 const browser=await chromium.launch({headless:true});
 const page=await browser.newPage({viewport:{width:390,height:844}});
 const errors=[];
 page.on('pageerror',e=>errors.push(e.message));
 await page.goto('https://ikst2512-eng.github.io/boat-edge-clean/',{waitUntil:'domcontentloaded',timeout:45000});
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
 console.log('PASS: public mobile page renders 24 venues, 12 races, 4 tabs, switches selections; no JS page errors');
 await browser.close();
})().catch(e=>{console.error(e);process.exitCode=1});
