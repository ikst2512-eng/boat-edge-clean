'use strict';
// Public-origin browser CORS gate. No route interception, mock headers,
// altered response body, production configuration change or data writes.
const {chromium}=require('playwright');

(async()=>{
 const browser=await chromium.launch({headless:true});
 try{
  const page=await browser.newPage({viewport:{width:390,height:844}});
  const pages='https://ikst2512-eng.github.io/boat-edge-clean/';
  const endpoint='https://boat-edge-clean.onrender.com/api/four-mode-archive?code=202611061006';
  const loaded=await page.goto(pages,{waitUntil:'domcontentloaded',timeout:45000});
  if(!loaded?.ok())throw Error('REAL_CORS_GATE_PAGES_HTTP_'+(loaded?.status()??'no_response'));
  const verdict=await page.evaluate(async url=>{
   const abort=new AbortController();
   const timer=setTimeout(()=>abort.abort(),20000);
   try{
    const response=await fetch(url,{
     method:'GET',mode:'cors',credentials:'omit',cache:'no-store',
     redirect:'error',signal:abort.signal
    });
    if(!response.ok)return {origin:location.origin,http:response.status,ok:false};
    const archive=await response.json();
    return {origin:location.origin,http:response.status,ok:true,
     responseType:response.type,status:archive.status,
     race_code:archive.race_code,
     production_forecast:archive.production_forecast,
     verified_first_git_add:archive.verified_first_git_add,
     modes:Object.keys(archive.modes||{}).sort(),
     counts:Object.fromEntries(Object.entries(archive.modes||{}).map(
      ([mode,data])=>[mode,Array.isArray(data?.tickets)?data.tickets.length:null]))
    };
   }catch(e){
    return {origin:location.origin,ok:false,error:String(e).slice(0,240)};
   }finally{clearTimeout(timer)}
  },endpoint);
  const required=['balance','hit','hole','narrow'];
  const valid=verdict.origin==='https://ikst2512-eng.github.io'&&
   verdict.ok===true&&verdict.http===200&&verdict.responseType==='cors'&&
   verdict.status==='historical_research_only'&&
   verdict.race_code==='202611061006'&&
   verdict.production_forecast===false&&
   verdict.verified_first_git_add===false&&
   JSON.stringify(verdict.modes)===JSON.stringify(required)&&
   required.every(mode=>Number.isInteger(verdict.counts?.[mode])&&
    verdict.counts[mode]>0);
  if(!valid)throw Error('FAIL_UNSIMULATED_BROWSER_CORS '+JSON.stringify(verdict));
  console.log('PASS_UNSIMULATED_BROWSER_CORS '+JSON.stringify({
   ...verdict,scope:'cross-origin read-only historical archive; not production forecast',
   simulatedHeaders:false,appUnmodified:true
  }));
 }finally{await browser.close()}
})().catch(error=>{console.error(error);process.exitCode=1});
