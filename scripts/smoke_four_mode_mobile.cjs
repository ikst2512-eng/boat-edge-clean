const {chromium} = require('playwright');
(async () => {
  const browser=await chromium.launch({headless:true});
  try {
    const page=await browser.newPage({viewport:{width:390,height:844},isMobile:true,hasTouch:true,deviceScaleFactor:3});
    await page.goto('https://boat-edge-clean.onrender.com/forecast?date=2026-10-28&venue=1&race=1', {waitUntil:'domcontentloaded',timeout:90000});
    await page.locator('#fourModeForecastRows .four-mode-forecast-item').first().waitFor({timeout:60000});
    const info=await page.evaluate(()=>{
      const root=document.querySelector('#fourModeForecastRows');
      const cards=[...root.querySelectorAll('.four-mode-forecast-item')];
      return {headings:cards.map(x=>x.querySelector('strong')?.textContent||''),
        ticketCounts:cards.map(x=>x.querySelectorAll('.four-mode-forecast-ticket').length),
        status:document.querySelector('#fourModeForecastStatus')?.textContent,
        legacyCollapsed:!document.querySelector('#legacyTopnResearch')?.open,
        overflow:document.documentElement.scrollWidth>innerWidth+1,
        panelVisible:!!document.querySelector('#fourModeForecastPanel')?.getClientRects().length};
    });
    if(info.headings.length!==4 || !['本命','バランス','穴','絞り'].every((x,i)=>info.headings[i].startsWith(x)))
      throw Error('Four-mode heading/order incorrect: '+JSON.stringify(info));
    if(info.ticketCounts.some(x=>x<1)||!info.legacyCollapsed||info.overflow||!info.panelVisible)
      throw Error('Mobile forecast presentation incorrect: '+JSON.stringify(info));
    if(!info.status.includes('過去保存予想')) throw Error('Research-only provenance missing: '+JSON.stringify(info));
    console.log(JSON.stringify({publicMobileBrowser:'passed',...info}));
  } finally {await browser.close()}
})().catch(e=>{console.error(e);process.exit(1)});
