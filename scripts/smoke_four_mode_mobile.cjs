const {chromium, webkit} = require('playwright');
(async () => {
  for(const [engineName,engine] of [['chromium',chromium],['webkit',webkit]]){
  const browser=await engine.launch({headless:true});
  try {
    const page=await browser.newPage({viewport:{width:390,height:844},isMobile:true,hasTouch:true,deviceScaleFactor:3});
    await page.goto('https://boat-edge-clean.onrender.com/forecast?date=2026-11-02&venue=2&race=11', {waitUntil:'domcontentloaded',timeout:90000});
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
    if(info.headings.length!==4 || !['絞り','本命','バランス','穴'].every((x,i)=>info.headings[i].startsWith(x)))
      throw Error('Four-mode heading/order incorrect: '+JSON.stringify(info));
    if(info.ticketCounts.length!==4||info.ticketCounts.some(n=>n<1||n>120)||!info.legacyCollapsed||info.overflow||!info.panelVisible)
      throw Error('Mobile forecast presentation incorrect: '+JSON.stringify(info));
    if(!info.status.includes('過去保存予想')) throw Error('Research-only provenance missing: '+JSON.stringify(info));
    const hierarchy=await page.evaluate(()=>{const c=document.querySelector('.four-mode-combo'),o=document.querySelector('.four-mode-odds');return {comboPx:c?parseFloat(getComputedStyle(c).fontSize):null,oddsPx:o?parseFloat(getComputedStyle(o).fontSize):null,columns:getComputedStyle(document.querySelector('#fourModeForecastRows')).gridTemplateColumns}});
    if(hierarchy.comboPx!==24||hierarchy.oddsPx!==null&&hierarchy.oddsPx>12)throw Error('Ticket hierarchy incorrect: '+JSON.stringify(hierarchy));
    console.log(JSON.stringify({publicMobileBrowser:'passed',engine:engineName,raceCode:'202611020211',...info,...hierarchy}));
  } finally {await browser.close()}
  }
})().catch(e=>{console.error(e);process.exit(1)});
