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
    if(!info.status.includes('過去保存予想')&&!info.status.includes('正式予想として使用しないでください')) throw Error('Research-only provenance missing: '+JSON.stringify(info));
    const hierarchy=await page.evaluate(()=>{const c=document.querySelector('.four-mode-combo'),o=document.querySelector('.four-mode-odds');return {comboPx:c?parseFloat(getComputedStyle(c).fontSize):null,oddsPx:o?parseFloat(getComputedStyle(o).fontSize):null,columns:getComputedStyle(document.querySelector('#fourModeForecastRows')).gridTemplateColumns}});
    if(hierarchy.comboPx!==24||hierarchy.oddsPx!==null&&hierarchy.oddsPx>12)throw Error('Ticket hierarchy incorrect: '+JSON.stringify(hierarchy));
    // Fetch real API odds for the selected race. Never mistake historical/current odds.
    const oddsEvidence=await page.evaluate(async()=>{
      const key='202611020211';const url='/api/odds?hd=20261102&jcd=02&rno=11';
      try{const res=await fetch(url,{cache:'no-store'}),feed=await res.json();
        const rows=[...document.querySelectorAll('#fourModeForecastRows [data-four-mode-combo]')];
        const rendered=rows.filter(r=>r.querySelector('.four-mode-odds')).map(r=>({combo:r.dataset.fourModeCombo,label:r.querySelector('.four-mode-odds').textContent}));
        const valid=feed?.ok===true&&feed?.hd==='20261102'&&String(feed?.jcd).padStart(2,'0')==='02'&&Number(feed?.rno)===11&&feed?.odds&&Object.keys(feed.odds).length===120;
        if(valid){for(const row of rendered){const expected='オッズ '+Number(feed.odds[row.combo]).toLocaleString('ja-JP')+'倍';if(row.label!==expected)throw Error('ODDS_RENDER_MISMATCH '+row.combo+' '+row.label+' != '+expected)}}
        return {http:res.status,apiValid:!!valid,renderedCount:rendered.length,comparison:valid?'matched':'not-eligible'};
      }catch(e){return {error:String(e)}}
    });
    if(oddsEvidence.error?.startsWith('Error: ODDS_RENDER_MISMATCH'))throw Error(oddsEvidence.error);
    console.log(JSON.stringify({publicOddsEvidence:oddsEvidence,engine:engineName}));
    // Deterministically simulate the first HTTP 202 followed by real HTTP 200/202,
    // then measure whether UI retries and correctly resolves or remains pending.
    await page.evaluate(()=>{s.race=11;render()});
    let oddsCalls=0;
    await page.route('**/api/odds?**',async route=>{
      oddsCalls++;
      if(oddsCalls===1){await route.fulfill({status:202,contentType:'application/json',body:JSON.stringify({ok:false,status:'pending'})});return}
      await route.continue();
    });
    await page.evaluate(()=>{s.race=11;render()});
    await page.waitForTimeout(5500);
    const retryState=await page.evaluate(()=>({key:document.querySelector('#fourModeForecastRows')?.dataset.raceKey||'',oddsCount:document.querySelectorAll('#fourModeForecastRows .four-mode-odds').length,status:document.querySelector('#fourModeForecastRows')?.innerText?.slice(0,160)||''}));
    if(oddsCalls<2||retryState.key!=='20261102-02-11')throw Error('Pending odds retry failed '+JSON.stringify({oddsCalls,retryState}));
    console.log(JSON.stringify({pendingOddsTransition:'passed',engine:engineName,oddsCalls,oddsCount:retryState.oddsCount,status:retryState.status}));
    await page.unroute('**/api/odds?**');
    // Check selected race label and available result/odds UI without fabricating unavailable values.
    const evidence=await page.evaluate(()=>({selected:document.querySelector('#activeRaceLabel')?.textContent||'',resultStatus:document.querySelector('#resultStatus')?.textContent||'',result:document.querySelector('#resultDetail')?.textContent||'',oddsNotice:document.querySelector('#fourModeForecastRows')?.textContent||''}));
    if(!evidence.selected.includes('11R'))throw Error('Selected race label mismatch: '+JSON.stringify(evidence));
    if(!evidence.resultStatus)throw Error('Confirmed result status missing');
    if(/undefined|NaN倍/.test(evidence.result))throw Error('Invalid result rendered: '+JSON.stringify(evidence));
    await page.evaluate(()=>{s.race=12;render()});
    await page.waitForTimeout(1200);
    const switched=await page.evaluate(()=>({selected:document.querySelector('#activeRaceLabel')?.textContent||'',archiveKey:document.querySelector('#fourModeForecastRows')?.dataset.raceKey||'',result:document.querySelector('#resultDetail')?.textContent||'',resultKey:displayedResultKey}));
    if(!switched.selected.includes('12R')||switched.archiveKey&&switched.archiveKey!=='20261102-02-12'||switched.resultKey&&switched.resultKey!=='20261102-02-12')throw Error('Cross-race stale display after switch: '+JSON.stringify(switched));
    // Exercise repeated forward/back navigation and ensure the race identity remains coherent.
    for(const race of [10,11,12,11]){
      await page.evaluate(race=>{s.race=race;render()},race);
      await page.waitForTimeout(400);
      const state=await page.evaluate(()=>({selected:document.querySelector('#activeRaceLabel')?.textContent||'',archive:document.querySelector('#fourModeForecastRows')?.dataset.raceKey||'',resultKey:displayedResultKey||''}));
      const expected='20261102-02-'+String(race).padStart(2,'0');
      if(!state.selected.includes(race+'R')||state.archive&&state.archive!==expected||state.resultKey&&state.resultKey!==expected)throw Error('Multi-race navigation leakage '+JSON.stringify({race,state}));
    }
    // Read-only live odds observations for separate race numbers; no synthetic HTTP results.
    const liveOdds=[];
    for(const race of [10,11,12]){
      const started=Date.now();
      try{
        const response=await page.request.get('https://boat-edge-clean.onrender.com/api/odds?hd=20261102&jcd=02&rno='+race,{timeout:30000});
        const elapsedMs=Date.now()-started;
        const body=await response.json().catch(()=>null);
        liveOdds.push({race,http:response.status(),elapsedMs,valid:body?.ok===true&&body?.hd==='20261102'&&Number(body?.rno)===race&&body?.odds&&Object.keys(body.odds).length===120});
      }catch(e){liveOdds.push({race,error:String(e),elapsedMs:Date.now()-started})}
    }
    console.log(JSON.stringify({publicOddsMultiRaceObservation:liveOdds,engine:engineName}));
    console.log(JSON.stringify({multiRaceNavigation:'passed',engine:engineName,sequence:[10,11,12,11]}));
    console.log(JSON.stringify({publicRaceSwitch:'passed',engine:engineName,initialResultStatus:evidence.resultStatus,switched}));
    console.log(JSON.stringify({publicMobileBrowser:'passed',engine:engineName,raceCode:'202611020211',...info,...hierarchy}));
  } finally {await browser.close()}
  }
})().catch(e=>{console.error(e);process.exit(1)});
