const {chromium, webkit} = require('playwright');
(async () => {
  for(const [engineName,engine] of [['chromium',chromium],['webkit',webkit]]){
  const browser=await engine.launch({headless:true});
  try {
    const page=await browser.newPage({viewport:{width:390,height:844},isMobile:true,hasTouch:true,deviceScaleFactor:3});
    await page.goto('https://boat-edge-clean.onrender.com/forecast?date=2026-11-02&venue=2&race=11', {waitUntil:'domcontentloaded',timeout:90000});
    // Scenario-first is the default presentation. The immutable V2 baseline
    // is a comparison that the user explicitly opens, not the primary model.
    const primary=page.locator('#restoredScenarioPanel');
    await primary.waitFor({state:'visible',timeout:60000});
    const comparator=page.locator('#v2Comparator');
    await comparator.waitFor({state:'visible',timeout:60000});
    if(await comparator.evaluate(el=>el.open))throw Error('V2 baseline must be collapsed by default');
    await comparator.locator('summary').click();
    await page.locator('#fourModeForecastRows .four-mode-forecast-item').first().waitFor({state:'visible',timeout:60000});
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
    if(!(hierarchy.comboPx>=14&&hierarchy.comboPx<=18)||hierarchy.oddsPx!==null&&hierarchy.oddsPx>12)throw Error('Ticket hierarchy incorrect for compact 390px mobile UI: '+JSON.stringify(hierarchy));
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
    // Bounded read-only public odds API sampling on three real archived races.
    const samples=await page.evaluate(async()=>{
      const rows=[];
      for(const race of [10,11,12]){
        const start=performance.now();
        try{
          const res=await fetch('/api/odds?hd=20261102&jcd=02&rno='+race,{cache:'no-store',signal:AbortSignal.timeout(12000)});
          const latencyMs=Math.round(performance.now()-start);
          let valid=false;
          if(res.status===200){const feed=await res.json();valid=feed.ok===true&&Number(feed.rno)===race&&feed.hd==='20261102'&&Object.keys(feed.odds||{}).length===120}
          rows.push({race,status:res.status,latencyMs,valid});
        }catch(e){rows.push({race,status:'network-error',latencyMs:Math.round(performance.now()-start),error:String(e)})}
      }
      return rows;
    });
    if(samples.length!==3||samples.some(s=>s.status===200&&!s.valid))throw Error('Invalid actual odds sample '+JSON.stringify(samples));
    console.log(JSON.stringify({publicOddsMultiRace:engineName,samples}));
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

    // On actual published GitHub Pages, the Nov 10 Biwako 6R original
    // exhibition CSV contains six genuinely empty per-lane lap values.
    // Verify WebKit (Safari engine, not a physical iPhone) preserves all
    // remaining measurements and clearly explains source missingness.
    // This is unmocked and intentionally distinct from local fixture tests.
    if(engineName==='webkit'){
      const pages=await browser.newPage({viewport:{width:390,height:844},isMobile:true,hasTouch:true,deviceScaleFactor:3});
      try{
        const res=await pages.goto('https://ikst2512-eng.github.io/boat-edge-clean/?date=2026-11-10&venue=11&race=6&view=exhibit',
          {waitUntil:'domcontentloaded',timeout:45000});
        if(res?.status()!==200)throw Error('Published Pages unavailable in WebKit: '+res?.status());
        await pages.evaluate(()=>{datePinned=true;venueTouched=true;s.date='2026-11-10';s.venue=10;s.race=6;setView('exhibit');render()});
        try{
          await pages.waitForFunction(()=>sameRaceKey()==='20261110-11-06'&&
            document.querySelectorAll('#exhibitionGrid .exhibition-boat').length===6&&
            document.querySelector('#originalExhibitionStatus')?.dataset.originalState==='partial_missing',
            null,{timeout:25000});
        }catch(error){
          const state=await pages.evaluate(()=>({
            selected:sameRaceKey(),view:activeView,
            raceStatus:document.querySelector('#raceDataStatus')?.textContent,
            original:document.querySelector('#originalExhibitionStatus')?.textContent,
            boats:document.querySelectorAll('#exhibitionGrid .exhibition-boat').length
          }));
          throw Error('LIVE_PUBLIC_WEBKIT_SPARSE_EXHIBITION_UNVERIFIED '+JSON.stringify(state));
        }
        const proof=await pages.evaluate(()=>({
          notice:document.querySelector('#originalExhibitionStatus')?.textContent||'',
          counts:[...document.querySelectorAll('#exhibitionGrid .exhibition-boat')].map(c=>({
            lane:Number(c.querySelector('.lane-badge')?.textContent),
            metrics:[...c.querySelectorAll('.exhibition-original-metric')].map(m=>({
              label:m.querySelector('span')?.textContent,
              value:m.querySelector('strong')?.textContent,
              missing:m.dataset.sourceValueState==='missing'
            }))
          })),
          overflow:document.documentElement.scrollWidth-document.documentElement.clientWidth
        }));
        if(!proof.notice.includes('一部欠測：6/18項目')||proof.counts.length!==6||proof.overflow>1)
          throw Error('LIVE_PUBLIC_WEBKIT_SPARSE_EXHIBITION_LAYOUT '+JSON.stringify(proof));
        for(let lane=1;lane<=6;lane++){
          const c=proof.counts[lane-1];
          if(c.lane!==lane||c.metrics.length!==3||c.metrics[0].label!=='一周'||
             c.metrics[0].value!=='—'||!c.metrics[0].missing||
             c.metrics.slice(1).some(m=>m.missing||!m.value||m.value==='—'))
            throw Error('LIVE_PUBLIC_WEBKIT_SPARSE_EXHIBITION_LANE '+JSON.stringify(c));
        }
        console.log('LIVE_PUBLIC_WEBKIT_SPARSE_EXHIBITION_PASS '+JSON.stringify({
          race:'202611101106',lanes:6,originalFields:18,missing:6,
          present:12,viewportWidth:390,overflowPx:proof.overflow,
          source:'real public CSV through actual Pages DOM',physicalSafari:false
        }));
      }finally{await pages.close()}
    }
    console.log(JSON.stringify({publicMobileBrowser:'passed',engine:engineName,raceCode:'202611020211',...info,...hierarchy}));
  } finally {await browser.close()}
  }
})().catch(e=>{console.error(e);process.exit(1)});
