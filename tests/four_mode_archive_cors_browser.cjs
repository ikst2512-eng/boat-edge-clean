// Controlled cross-origin browser test for the Draft server.py CORS hotfix.
// The browser uses synthetic Pages-origin HTML and the exact HTTP headers from
// a real local Python Handler. This is NOT published Pages/Render live E2E.
const assert = require('node:assert/strict');
const {spawn} = require('node:child_process');
const {chromium, webkit} = require('playwright');

const py = [
  'import four_mode_archive_api as a',
  'a.archived_four_modes = lambda code: (200, {"ok": True, "race_code": code}) if code == "202611061006" else (422, {"ok": False})',
  'from server import Handler',
  'from http.server import ThreadingHTTPServer',
  'srv = ThreadingHTTPServer(("127.0.0.1", 0), Handler)',
  'print("LOCAL_PORT="+str(srv.server_port), flush=True)',
  'srv.serve_forever()',
].join('\n');

async function startHandler(){
  const child=spawn('python',['-u','-c',py],{stdio:['ignore','pipe','pipe']});
  let diagnostics='';
  child.stderr.on('data',chunk=>{diagnostics+=String(chunk).slice(-3000);});
  const port=await new Promise((resolve,reject)=>{
    let buf='';
    const timer=setTimeout(()=>reject(Error('Local Handler startup timeout '+diagnostics)),10000);
    child.stdout.on('data',chunk=>{
      buf+=String(chunk);
      const found=buf.match(/LOCAL_PORT=(\d+)/);
      if(found){clearTimeout(timer);resolve(Number(found[1]));}
    });
    child.once('exit',code=>{clearTimeout(timer);reject(Error('Local Handler exited '+code+' '+diagnostics));});
  });
  return {child,port};
}

async function runCase(browser,port,origin,code,path='/api/four-mode-archive'){
  const page=await browser.newPage();
  try{
    await page.route(origin+'/**',route=>route.fulfill({
      status:200,contentType:'text/html',
      body:'<!doctype html><html><head><meta charset="utf-8"></head><body>local CORS origin fixture</body></html>'
    }));
    await page.route('https://boat-edge-clean.onrender.com/**',async route=>{
      const requested=new URL(route.request().url());
      const headers=await route.request().allHeaders();
      const local=await fetch('http://127.0.0.1:'+port+requested.pathname+requested.search,{
        headers:headers.origin?{Origin:headers.origin}:{}
      });
      const replyHeaders={};
      for(const name of ['content-type','access-control-allow-origin','cache-control']){
        const value=local.headers.get(name);
        if(value!==null)replyHeaders[name]=value;
      }
      await route.fulfill({status:local.status,headers:replyHeaders,body:Buffer.from(await local.arrayBuffer())});
    });
    await page.goto(origin+'/boat-edge-clean/cors-fixture',{waitUntil:'domcontentloaded'});
    return await page.evaluate(async ({code,path})=>{
      try {
        const response=await fetch('https://boat-edge-clean.onrender.com'+path+'?code='+code,{cache:'no-store'});
        return {blocked:false,status:response.status,body:await response.text()};
      }catch(error){
        return {blocked:true,errorName:error.name};
      }
    },{code,path});
  }finally{await page.close();}
}

(async()=>{
  const {child,port}=await startHandler();
  try {
    for(const [name,engine] of [['chromium',chromium],['webkit',webkit]]){
      const browser=await engine.launch({headless:true});
      try{
        const pages='https://ikst2512-eng.github.io';
        const ok=await runCase(browser,port,pages,'202611061006');
        assert.equal(ok.blocked,false,name+' Pages 200 blocked: '+JSON.stringify(ok));
        assert.equal(ok.status,200,name+' Pages 200 status');
        assert.equal(JSON.parse(ok.body).race_code,'202611061006');
        const err=await runCase(browser,port,pages,'invalid');
        assert.equal(err.blocked,false,name+' Pages 422 blocked: '+JSON.stringify(err));
        assert.equal(err.status,422,name+' Pages 422 status');
        const bad=await runCase(browser,port,'https://untrusted-site.example','202611061006');
        assert.equal(bad.blocked,true,name+' unexpected cross-origin access: '+JSON.stringify(bad));
        // Playwright's synthetic route.fulfill can let a missing-header
        // response through despite browser CORS; test raw Handler headers
        // rather than assuming a mocked no-ACAO response is blocked.
        const health=await fetch('http://127.0.0.1:'+port+'/healthz',{
          headers:{Origin:pages}
        });
        assert.equal(health.status,200,name+' local health status');
        assert.equal(health.headers.get('access-control-allow-origin'),null,
          name+' local health must not expose CORS');
        assert.equal(await health.text(),'ok',name+' local health body');
        console.log('DRAFT_LOCAL_BROWSER_CORS_'+name.toUpperCase()+'_PASS allowed200=200 allowed422=422 untrusted=blocked health_raw_header=absent');
      }finally{await browser.close();}
    }
    console.log('PUBLISHED_PAGES_RENDER_CORS_NOT_YET_VERIFIED');
  }finally{child.kill('SIGTERM');}
})().catch(error=>{console.error(error.stack||String(error));process.exitCode=1;});
