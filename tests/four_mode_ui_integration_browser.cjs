'use strict';
// Draft-only integrated visual check: actual index/navigation and unmodified
// local Python Handler + repository archive files. Pages/API hosts are routed
// locally, other external requests are blocked. NOT published Pages evidence.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const {spawn} = require('node:child_process');
const {chromium,webkit} = require('playwright');

const PAGES = 'https://ikst2512-eng.github.io';
const RENDER = 'https://boat-edge-clean.onrender.com';
const FIXTURES = [
  {code:'202611061006',date:'2026-11-06',venue:10,race:6},
  {code:'202611071006',date:'2026-11-07',venue:10,race:6},
];
// Latest main data after the original PR base; checked by synthetic-merge CI.
const RECENT = {code:'202611100401',date:'2026-11-10',venue:4,race:1};
const MODES = [['narrow','絞り'],['hit','本命'],['balance','バランス'],['hole','穴']];
const key = r=>r.code.slice(0,8)+'-'+r.code.slice(8,10)+'-'+r.code.slice(10);

const html=fs.readFileSync('index.html','utf8');
const navigation=fs.readFileSync('navigation.js','utf8');
function expectedCards(r){
  const archive=JSON.parse(fs.readFileSync('four_mode_forecasts/'+r.code+'.json','utf8'));
  assert.equal(archive.race_code,r.code,'Fixture code mismatch');
  return MODES.map(([id,label])=>({
    label:label+'（保存 '+archive.modes[id].tickets.length+'点）',
    tickets:archive.modes[id].tickets.map(v=>({
      combo:v.combo,p:v.p.toFixed(2)+'%'
    }))
  }));
}
async function localHandler(){
  const code=[
    'from http.server import ThreadingHTTPServer',
    'from server import Handler',
    "s=ThreadingHTTPServer(('127.0.0.1',0),Handler)",
    "print('LOCAL_PORT='+str(s.server_port),flush=True)",
    's.serve_forever()',
  ].join('\n');
  const child=spawn('python',['-u','-c',code],{stdio:['ignore','pipe','pipe']});
  let err='';
  child.stderr.on('data',chunk=>{err+=String(chunk).slice(-5000)});
  const port=await new Promise((resolve,reject)=>{
    let buf='';
    const timer=setTimeout(()=>reject(Error('Handler startup timeout '+err)),12000);
    child.stdout.on('data',chunk=>{
      buf+=String(chunk);
      const match=buf.match(/LOCAL_PORT=(\d+)/);
      if(match){clearTimeout(timer);resolve(Number(match[1]));}
    });
    child.once('exit',n=>{clearTimeout(timer);reject(Error('Handler exited '+n+' '+err));});
  });
  return {child,port};
}
async function verify(page,r){
  const expected=expectedCards(r);
  await page.waitForFunction(k=>{
    const el=document.getElementById('fourModeForecastRows');
    const status=document.getElementById('fourModeForecastStatus');
    return activeView==='forecast' &&
      document.getElementById('forecast')?.hidden===false &&
      status?.dataset.loaded==='true' && el?.dataset.raceKey===k &&
      el.querySelectorAll('.four-mode-forecast-item').length===4;
  },key(r),{timeout:24000});
  const data=await page.evaluate(()=>({
    key:sameRaceKey(),
    storedKey:document.getElementById('fourModeForecastRows')?.dataset.raceKey,
    cards:[...document.querySelectorAll('#fourModeForecastRows .four-mode-forecast-item')]
      .map(card=>({
        label:card.querySelector('strong')?.textContent,
        tickets:[...card.querySelectorAll('[data-four-mode-combo]')].map(row=>({
          combo:row.dataset.fourModeCombo,p:row.querySelector('.four-mode-prob')?.textContent
        }))
      })),
    status:document.getElementById('fourModeForecastStatus')?.textContent,
  }));
  assert.equal(data.key,key(r));
  assert.equal(data.storedKey,key(r));
  assert.deepEqual(data.cards,expected,'UI must match unchanged source tickets and probabilities');
  assert.match(data.status,/正式予想として使用しないでください|正式予想とは区別/,
    'Historical research must not be misrepresented as attested forecast');
  return {race:r.code,counts:data.cards.map(card=>card.tickets.length)};
}
(async()=>{
  const recentSource='four_mode_forecasts/'+RECENT.code+'.json';
  const hasRecent=fs.existsSync(recentSource);
  if(process.env.GITHUB_EVENT_NAME==='pull_request')
    assert.ok(hasRecent,'PR synthetic-merge CI must contain latest main archive '+recentSource);
  if(!hasRecent)console.log('DIRECT_DRAFT_CHECKOUT_RECENT_MAIN_ARCHIVE_ABSENT '+RECENT.code);
  const {child,port}=await localHandler();
  try{
    // Verify the exact production Handler static routes which will be
    // compared against both deployed hosts by the manual postrelease gate.
    for(const [asset,route] of [['index.html','/index.html'],['navigation.js','/navigation.js']]){
      const r=await fetch('http://127.0.0.1:'+port+route,{
        signal:AbortSignal.timeout(10000),cache:'no-store'
      });
      assert.equal(r.status,200,'Handler must serve '+asset);
      assert.deepEqual(Buffer.from(await r.arrayBuffer()),fs.readFileSync(asset),
        'Handler served bytes must equal checked-out '+asset);
    }
    console.log('DRAFT_RENDER_HANDLER_FRONTEND_BYTES_MATCH source=index.html,navigation.js');
    // These are real Handler headers from a real HTTP response, even though
    // Playwright transports the response to a synthetic Pages-origin document.
    const check=await fetch('http://127.0.0.1:'+port+
      '/api/four-mode-archive?code='+FIXTURES[0].code,{headers:{Origin:PAGES}});
    assert.equal(check.status,200,'Local production Handler must serve saved archive');
    assert.equal(check.headers.get('access-control-allow-origin'),PAGES,
      'Local Handler must authorize Pages without header injection');
    for(const [name,engine] of [['chromium',chromium],['webkit',webkit]]){
      const browser=await engine.launch({headless:true});
      try{
        const page=await browser.newPage({viewport:{width:390,height:844}});
        let archiveCalls=0;
        // Hold only the transport of one genuine Handler response to simulate
        // an older race finishing after a new race has rendered.
        let deferredArchive=null;
        await page.route('**/*',async route=>{
          const request=route.request(),url=new URL(request.url());
          if(url.origin===PAGES && url.pathname==='/boat-edge-clean/navigation.js')
            return route.fulfill({status:200,contentType:'application/javascript',body:navigation});
          if(url.origin===PAGES && (url.pathname==='/boat-edge-clean/'||url.pathname==='/boat-edge-clean'))
            return route.fulfill({status:200,contentType:'text/html',body:html});
          if(url.origin===RENDER && url.pathname==='/api/four-mode-archive'){
            archiveCalls++;
            if(deferredArchive && !deferredArchive.blocked &&
               url.searchParams.get('code')===deferredArchive.code){
              deferredArchive.blocked=true;
              deferredArchive.notify();
              await deferredArchive.gate;
            }
            const headers=await request.allHeaders();
            const raw=await fetch('http://127.0.0.1:'+port+
              url.pathname+url.search,{headers:headers.origin?{Origin:headers.origin}:{}});
            const forwarded={};
            for(const h of ['content-type','access-control-allow-origin','cache-control']){
              const value=raw.headers.get(h);
              if(value!==null)forwarded[h]=value;
            }
            return route.fulfill({status:raw.status,headers:forwarded,
              body:Buffer.from(await raw.arrayBuffer())});
          }
          // Do not fetch public data, invoke a collector, or fake archive data.
          return route.fulfill({status:404,contentType:'application/json',body:'{}'});
        });
        const first=FIXTURES[0];
        const response=await page.goto(PAGES+'/boat-edge-clean/?date='+first.date+
          '&venue='+first.venue+'&race='+first.race+'&screen=forecast',{
            waitUntil:'domcontentloaded',timeout:24000
          });
        assert.equal(response?.status(),200);
        await page.waitForFunction(()=>document.documentElement.dataset.cleanNavigationInit==='1' &&
          window.__boatEdgeNavigationOwnsHistory===true,{timeout:15000});
        const initial=await verify(page,first);
        const firstCount=archiveCalls;
        assert.ok(firstCount>=1,'No actual Handler archive HTTP requests');
        const second=FIXTURES[1];
        await page.evaluate(r=>{
          datePinned=true;venueTouched=true;
          s.date=r.date;s.venue=r.venue-1;s.race=r.race;render();
        },second);
        const switched=await verify(page,second);
        assert.ok(archiveCalls>firstCount,'Race change did not fetch the second archive');
        const href=await page.evaluate(()=>({
          date:new URL(location.href).searchParams.get('date'),
          venue:new URL(location.href).searchParams.get('venue'),
          race:new URL(location.href).searchParams.get('race'),
          snapshot:history.state?.snapshot
        }));
        assert.equal(href.date,second.date);
        assert.equal(href.venue,String(second.venue));
        assert.equal(href.race,String(second.race));
        assert.equal(href.snapshot?.date,second.date);
        assert.equal(href.snapshot?.race,second.race);
        const back=await page.evaluate(()=>{history.back();return true;});
        assert.equal(back,true);
        await page.waitForFunction(k=>sameRaceKey()===k &&
          history.state?.snapshot?.date==='2026-11-06',key(first),{timeout:15000});
        const restored=await verify(page,first);

        // Delayed first-race HTTP must not overwrite a later selected race.
        // This keeps the original Handler response unmodified; only its
        // transport completion is deliberately scheduled out of order.
        let markSeen,release;
        const seen=new Promise(resolve=>{markSeen=resolve});
        const gate=new Promise(resolve=>{release=resolve});
        deferredArchive={code:first.code,blocked:false,notify:markSeen,gate};
        await page.evaluate(()=>render());
        await Promise.race([seen,new Promise((_,reject)=>{
          const id=setTimeout(()=>reject(Error('First-race delayed HTTP never started')),6000);
          seen.then(()=>clearTimeout(id));
        })]);
        await page.evaluate(r=>{
          datePinned=true;venueTouched=true;
          s.date=r.date;s.venue=r.venue-1;s.race=r.race;render();
        },second);
        const fastSwitched=await verify(page,second);
        const late=page.waitForResponse(res=>res.url().includes(
          '/api/four-mode-archive?code='+first.code),{timeout:15000});
        release();
        await late;
        await page.waitForTimeout(300);
        const afterLate=await verify(page,second);
        assert.deepEqual(afterLate,fastSwitched,
          'Late response from old race must never replace latest visible race');
        deferredArchive=null;
        console.log('DRAFT_INTEGRATED_FOUR_MODE_STALE_HTTP_'+name.toUpperCase()+'_PASS '+
          JSON.stringify({held:first.code,visible:second.code,sourceUnmodified:true}));

        if(hasRecent){
          await page.evaluate(r=>{
            datePinned=true;venueTouched=true;
            s.date=r.date;s.venue=r.venue-1;s.race=r.race;render();
          },RECENT);
          const newest=await verify(page,RECENT);
          await page.evaluate(()=>history.back());
          await page.waitForFunction(previous=>sameRaceKey()===previous,
            key(second),{timeout:15000});
          await verify(page,second);
          console.log('DRAFT_INTEGRATED_NEW_MAIN_ARCHIVE_'+name.toUpperCase()+'_PASS '+
            JSON.stringify({newest,restored:second.code,mainSourceUnmodified:true}));
        }
        console.log('DRAFT_INTEGRATED_FOUR_MODE_UI_'+name.toUpperCase()+'_PASS '+
          JSON.stringify({original:initial,switched,restored,
            realLocalHandler:true,sourceFilesUnchanged:true,
            syntheticPagesOrigin:true,archiveCalls}));
      }finally{await browser.close();}
    }
    console.log('PUBLISHED_PAGES_RENDER_FOUR_MODE_UI_NOT_YET_VERIFIED');
  }finally{child.kill('SIGTERM');}
})().catch(e=>{console.error(e.stack||String(e));process.exitCode=1});
