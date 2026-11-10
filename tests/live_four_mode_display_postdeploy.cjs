'use strict';
// Post-release, public Pages->Render acceptance. No routing/mocks/response injections.
// Historical saved tickets are display fixtures, not attested predeadline forecasts.
const assert = require('node:assert/strict');
const {chromium, webkit} = require('playwright');
const SITE = 'https://ikst2512-eng.github.io/boat-edge-clean/';
const API = 'https://boat-edge-clean.onrender.com/api/four-mode-archive';
const MODES = [['narrow','絞り'],['hit','本命'],['balance','バランス'],['hole','穴']];
const RACES = [
  {code:'202611061006', date:'2026-11-06', venue:10, race:6},
  {code:'202611071006', date:'2026-11-07', venue:10, race:6},
  // Newly saved main archive from November 10; must be visible after release.
  {code:'202611100401', date:'2026-11-10', venue:4, race:1},
];
const key = r => r.code.slice(0,8)+'-'+r.code.slice(8,10)+'-'+r.code.slice(10);

async function verify(page, engine, race) {
  const raceKey = key(race);
  // Only the real cross-origin browser fetch can populate these four cards.
  await page.waitForFunction(expected => {
    const status = document.getElementById('fourModeForecastStatus');
    const root = document.getElementById('fourModeForecastRows');
    return activeView==='forecast' &&
      document.getElementById('forecast')?.hidden===false &&
      status?.dataset.loaded==='true' && root?.dataset.raceKey===expected &&
      root.querySelectorAll('.four-mode-forecast-item').length===4;
  },raceKey,{timeout:45000});
  // Compare all rendered ticket codes and two-decimal probabilities with
  // the untouched actual archived API response, not a locally generated value.
  const res = await page.request.get(API+'?code='+race.code,{
    timeout:30000,headers:{Origin:'https://ikst2512-eng.github.io'}
  });
  assert.equal(res.status(),200,'Live four-mode API unavailable '+race.code);
  assert.equal(res.headers()['access-control-allow-origin'],
    'https://ikst2512-eng.github.io','Actual Pages-origin CORS header missing');
  const saved=await res.json();
  assert.equal(saved.race_code,race.code);
  assert.equal(saved.status,'historical_research_only');
  assert.equal(saved.production_forecast,false);
  assert.equal(saved.verified_first_git_add,false);
  const shown=await page.evaluate(()=>({
    key:sameRaceKey(),
    dataKey:document.getElementById('fourModeForecastRows')?.dataset.raceKey,
    status:document.getElementById('fourModeForecastStatus')?.textContent,
    cards:[...document.querySelectorAll('#fourModeForecastRows .four-mode-forecast-item')]
      .map(card=>({
        heading:card.querySelector('strong')?.textContent,
        tickets:[...card.querySelectorAll('[data-four-mode-combo]')].map(row=>({
          combo:row.dataset.fourModeCombo,
          probability:row.querySelector('.four-mode-prob')?.textContent
        }))
      }))
  }));
  assert.equal(shown.key,raceKey,'Race selection stale');
  assert.equal(shown.dataKey,raceKey,'Old-race forecast retained');
  assert.match(shown.status,/正式予想として使用しないでください|正式予想とは区別/,
    'Historical research disclosure missing');
  assert.deepEqual(shown.cards,MODES.map(([id,label])=>({
    heading:label+'（保存 '+saved.modes[id].tickets.length+'点）',
    tickets:saved.modes[id].tickets.map(t=>({
      combo:t.combo,probability:t.p.toFixed(2)+'%'
    }))
  })),'Published ticket or probability differs from saved source');
  console.log('LIVE_PUBLISHED_FOUR_MODE_DISPLAY_PASS '+JSON.stringify({
    engine,race:race.code,cardCount:shown.cards.length,
    counts:shown.cards.map(c=>c.tickets.length),probabilitiesMatch:true,
    noMocks:true,historicalOnly:true
  }));
}
(async()=>{
  for(const [engine,launcher] of [['chromium',chromium],['webkit',webkit]]){
    const browser=await launcher.launch({headless:true});
    try{
      const page=await browser.newPage({viewport:{width:390,height:844}});
      const errors=[];page.on('pageerror',e=>errors.push(String(e)));
      const first=RACES[0];
      const response=await page.goto(SITE+'?date='+first.date+
        '&venue='+first.venue+'&race='+first.race+'&screen=forecast',{
          waitUntil:'domcontentloaded',timeout:45000
        });
      assert.equal(response?.status(),200,'Published Pages not reachable');
      assert.match(await page.title(),/BOAT EDGE CLEAN/);
      await page.waitForFunction(()=>
        document.documentElement.dataset.cleanNavigationInit==='1' &&
        window.__boatEdgeNavigationOwnsHistory===true && activeView==='forecast',
        null,{timeout:20000});
      await verify(page,engine,first);
      // Four live shortcuts; exercise real buttons for two views.
      assert.equal(await page.locator('.race-detail-shortcuts button').count(),4);
      await page.locator('.race-detail-shortcuts button[data-race-view="result"]').click();
      await page.waitForFunction(()=>activeView==='result' &&
        !document.getElementById('resultSection').hidden,null,{timeout:20000});
      await page.locator('.race-detail-shortcuts button[data-race-view="forecast"]').click();
      await verify(page,engine,first);
      // Real app render/navigation wrapper must not retain first race's DOM.
      const second=RACES[1];
      await page.evaluate(({date,venue,race})=>{
        datePinned=true;venueTouched=true;
        s.date=date;s.venue=venue-1;s.race=race;render();
      },second);
      await verify(page,engine,second);
      const nav=await page.evaluate(()=>({
        date:new URL(location.href).searchParams.get('date'),
        venue:new URL(location.href).searchParams.get('venue'),
        race:new URL(location.href).searchParams.get('race'),
        saved:history.state?.snapshot
      }));
      assert.equal(nav.date,second.date);
      assert.equal(nav.venue,String(second.venue));
      assert.equal(nav.race,String(second.race));
      assert.equal(nav.saved?.date,second.date);
      assert.equal(nav.saved?.race,second.race);
      assert.equal(nav.saved?.view,'forecast');

      // Newest committed day: verify the display is not limited to old fixtures.
      const newest=RACES[2];
      await page.evaluate(({date,venue,race})=>{
        datePinned=true;venueTouched=true;
        s.date=date;s.venue=venue-1;s.race=race;render();
      },newest);
      await verify(page,engine,newest);
      const latestNav=await page.evaluate(()=>({
        date:new URL(location.href).searchParams.get('date'),
        venue:new URL(location.href).searchParams.get('venue'),
        race:new URL(location.href).searchParams.get('race'),
        state:history.state?.snapshot
      }));
      assert.equal(latestNav.date,newest.date);
      assert.equal(latestNav.venue,String(newest.venue));
      assert.equal(latestNav.race,String(newest.race));
      assert.equal(latestNav.state?.date,newest.date);
      assert.equal(latestNav.state?.race,newest.race);
      // Real history back must restore the previous day without retaining
      // the newer race's ticket/probability rows.
      await page.evaluate(()=>history.back());
      await page.waitForFunction(previous=>sameRaceKey()===previous &&
        history.state?.snapshot?.date==='2026-11-07',key(second),{timeout:20000});
      await verify(page,engine,second);
      console.log('LIVE_PUBLISHED_RECENT_ARCHIVE_AND_BACK_PASS '+
        JSON.stringify({engine,newest:newest.code,restored:second.code,sourceUnmodified:true}));
      assert.ok(!errors.some(e=>/SecurityError|history\.replaceState|history\.pushState/.test(e)),
        'Navigation history error '+JSON.stringify(errors.slice(-5)));
      console.log('LIVE_PUBLISHED_FOUR_MODE_NAVIGATION_PASS '+JSON.stringify({
        engine,views:['result','forecast'],raceKeys:RACES.map(r=>key(r)),
        noMocks:true
      }));
      await page.close();
    }finally{await browser.close();}
  }
  console.log('LIVE_PUBLISHED_FOUR_MODE_DISPLAY_VERIFIED');
  console.log('DO_NOT_INFER: physical_iPhone_Safari, idle_wake, accuracy, T-12');
})().catch(error=>{
  console.error('LIVE_PUBLISHED_FOUR_MODE_DISPLAY_FAIL '+(error.stack||String(error)));
  process.exitCode=1;
});
