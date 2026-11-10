// No actual Cloudflare or GitHub network. These tests intercept ALL requests.
import test from 'node:test';
import assert from 'node:assert/strict';
import {mkdtempSync,readFileSync,rmSync,statSync,symlinkSync} from 'node:fs';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
import {spawnSync} from 'node:child_process';
import {fileURLToPath} from 'node:url';
import {collectObserverTelemetry,persistObserverEvidence}
  from '../scripts/collect_cloudflare_observer_telemetry.mjs';
import {API_SCHEMA} from '../cloudflare/audit_observer_api_pages.mjs';

const ACCOUNT='a'.repeat(32),TOKEN='MOCK_NONLIVE_SECRET_TEST_ONLY_123456';
const DEPLOYMENT='OFFLINE-VERSION-ID';
const NOW=Date.parse('2026-11-11T01:00:00Z');
const ENDPOINT='https://api.cloudflare.com/client/v4/accounts/'+ACCOUNT+
  '/workers/observability/telemetry/query';
function mockedApi(){
  const calls=[];
  const fetcher=async(url,opts)=>{
    calls.push({url,method:opts.method,headers:opts.headers,
      request:JSON.parse(opts.body),redirect:opts.redirect});
    return {status:200, text:async()=>JSON.stringify({
      success:true,errors:[],
      result:{run:{status:'STARTED',id:'NOT-LIVE-'+calls.length,
        accountId:ACCOUNT,query:{parameters:JSON.parse(opts.body).parameters}}},
    })};
  };
  return {calls,fetcher};
}
const request=({fetcher,now=NOW,token=TOKEN,utcDay='2026-11-09',
  accountId=ACCOUNT,deploymentId=DEPLOYMENT}={})=>
  collectObserverTelemetry({fetcher,now,token,utcDay,accountId,deploymentId});

test('explicit owner query collector makes exactly two scoped non-dispatch Cloudflare POSTs',async()=>{
  const {calls,fetcher}=mockedApi();
  const out=await request({fetcher});
  assert.equal(calls.length,2);
  for(const call of calls){
    assert.equal(call.url,ENDPOINT);
    assert.equal(call.method,'POST');
    assert.equal(call.redirect,'error');
    assert.equal(call.headers.Authorization,'Bearer '+TOKEN);
    assert.deepEqual(call.request.parameters.datasets,['cloudflare-workers']);
    assert.deepEqual(call.request.parameters.filters,
      [{kind:'filter',key:'$metadata.service',
        value:'boat-edge-clean-independent-observer',type:'string',operation:'eq'}]);
    assert.equal(call.request.timeframe.from,Date.parse('2026-11-09T00:00:00Z'));
    assert.equal(call.request.timeframe.to,Date.parse('2026-11-10T00:00:00Z'));
    assert.ok(!call.url.includes('github.com')&&!call.url.includes('/dispatches'));
  }
  assert.equal(calls[0].request.limit,2000);
  assert.match(calls[0].request.queryId,
    /^boat-edge-observer-events-2026-11-09-[0-9a-f-]{36}$/);
  assert.match(calls[1].request.queryId,
    /^boat-edge-observer-sampling-2026-11-09-[0-9a-f-]{36}$/);
  assert.equal(calls[0].request.queryId.slice(-36),calls[1].request.queryId.slice(-36));
  assert.equal(calls[0].request.parameters.view,'events');
  assert.equal(calls[1].request.parameters.view,'calculations');
  assert.equal(calls[1].request.parameters.calculations[0].operator,'count');
  assert.equal(out.schema,API_SCHEMA);
  assert.equal(out.account_id,ACCOUNT);
  assert.equal(out.deployment_id,DEPLOYMENT);
  assert.equal(out.events_query.response.result.run.status,'STARTED');
  assert.doesNotMatch(JSON.stringify(out),new RegExp(TOKEN));
  assert.ok(!Object.hasOwn(out,'authenticated_to_cloudflare'));
});

test('two owner acquisitions for the same UTC day never reuse the same query pair IDs',async()=>{
  const first=mockedApi(),second=mockedApi();
  const a=await request({fetcher:first.fetcher});
  const b=await request({fetcher:second.fetcher});
  assert.notEqual(a.events_query.request.queryId,b.events_query.request.queryId);
  assert.notEqual(a.sampling_query.request.queryId,b.sampling_query.request.queryId);
  assert.equal(a.events_query.request.queryId.slice(-36),
    a.sampling_query.request.queryId.slice(-36));
  assert.equal(b.events_query.request.queryId.slice(-36),
    b.sampling_query.request.queryId.slice(-36));
  assert.equal(first.calls.length,2);
  assert.equal(second.calls.length,2);
});

test('collector refuses incomplete day, missing identity and token before any request',async()=>{
  for(const options of [
    {now:Date.parse('2026-11-10T00:10:00Z')},
    {utcDay:'2026-11-31'},
    {accountId:'not-an-account'},
    {token:''},
    {token:'a b c d e f g h'},
    {deploymentId:'bad'},
  ]){
    const {calls,fetcher}=mockedApi();
    await assert.rejects(()=>request({...options,fetcher}));
    assert.equal(calls.length,0);
  }
});
test('collector never retries ambiguous or HTTP error and never echoes token',async()=>{
  const calls=[];
  const fetcher=async(url,opts)=>{
    calls.push(opts);
    if(calls.length===1)return {status:200,text:async()=>JSON.stringify({success:true,result:{}})};
    return {status:403,text:async()=>TOKEN};
  };
  await assert.rejects(()=>request({fetcher}),/cloudflare_query_non_200/);
  assert.equal(calls.length,2);
  const firstCallBody=JSON.stringify(JSON.parse(calls[0].body));
  assert.ok(!firstCallBody.includes(TOKEN));
  const poison=async()=>({status:200,text:async()=>JSON.stringify({echo:TOKEN})});
  await assert.rejects(()=>request({fetcher:poison}),
    /cloudflare_query_response_contains_secret_pattern/);
});
test('Cloudflare API streaming response is bounded before buffering, even without Content-Length',async()=>{
  const urls=[];
  const fetcher=async(url)=>{
    urls.push(url);
    return new Response(new ReadableStream({
      start(controller) {
        controller.enqueue(new Uint8Array(12*1024*1024+1));
        controller.close();
      },
    }),{status:200});
  };
  await assert.rejects(()=>request({fetcher}),/cloudflare_query_response_oversize/);
  assert.deepEqual(urls,[ENDPOINT]); // No second POST or retry.
});

test('announced oversize Cloudflare response aborts before reading body',async()=>{
  let reads=0;
  const fetcher=async()=>({
    status:200,
    headers:{get:()=>String(12*1024*1024+1)},
    body:{getReader(){reads++;throw Error('must_not_read');}},
  });
  await assert.rejects(()=>request({fetcher}),/cloudflare_query_response_oversize/);
  assert.equal(reads,0);
});

test('genuine ReadableStream-shaped synthetic responses retain both original bodies',async()=>{
  let n=0;
  const fetcher=async(url,opts)=>{
    n++;
    assert.equal(url,ENDPOINT);
    return new Response(JSON.stringify({
      success:true,errors:[],
      result:{run:{status:'STARTED',id:'stream-mock-'+n,
        accountId:ACCOUNT,query:{parameters:JSON.parse(opts.body).parameters}}},
    }),{status:200,headers:{'content-type':'application/json'}});
  };
  const result=await request({fetcher});
  assert.equal(n,2);
  assert.equal(result.account_id,ACCOUNT);
  assert.equal(result.events_query.response.result.run.id,'stream-mock-1');
  assert.equal(result.sampling_query.response.result.run.id,'stream-mock-2');
  assert.doesNotMatch(JSON.stringify(result),new RegExp(TOKEN));
});

test('offline evidence is private, non-overwriting, saved unchanged, never a live success',async()=>{
  const {fetcher}=mockedApi();
  const data=await request({fetcher});
  const dir=mkdtempSync(join(tmpdir(),'boat-edge-observer-owner-export-'));
  try{
    const path=join(dir,'original.json');
    const receipt=persistObserverEvidence(data,path);
    assert.equal(receipt.local_consistency_pass,false);
    assert.equal(receipt.independently_authenticated_origin,false);
    assert.equal(receipt.cloudflare_deployment_independently_proven,false);
    assert.equal(receipt.github_dispatch_or_recovery_proven,false);
    assert.equal(receipt.formal_t_minus_12_proven,false);
    assert.match(receipt.input_sha256,/^[a-f0-9]{64}$/);
    assert.equal(statSync(path).mode&0o777,0o600);
    const raw=readFileSync(path,'utf8');
    assert.deepEqual(JSON.parse(raw),data);
    assert.ok(!raw.includes(TOKEN));
    assert.throws(()=>persistObserverEvidence(data,path),
      /cloudflare_export_output_not_created/);
  }finally{rmSync(dir,{force:true,recursive:true});}
});
test('never save an evidence artifact within source checkout or relative path',async()=>{
  const {fetcher}=mockedApi(),data=await request({fetcher});
  const local=fileURLToPath(new URL('../not-a-real-export.json',import.meta.url));
  assert.throws(()=>persistObserverEvidence(data,local),
    /output_inside_source_checkout_disallowed/);
  assert.throws(()=>persistObserverEvidence(data,'local.json'),
    /output_must_be_absolute_path/);
});
test('symlinked private export parent cannot redirect evidence into checkout',async()=>{
  const {fetcher}=mockedApi(),data=await request({fetcher});
  const dir=mkdtempSync(join(tmpdir(),'boat-edge-observer-symlink-'));
  try{
    const root=fileURLToPath(new URL('../',import.meta.url));
    symlinkSync(root,join(dir,'to-repo'),'dir');
    assert.throws(()=>persistObserverEvidence(data,join(dir,'to-repo','not-an-export.json')),
      /output_inside_source_checkout_disallowed/);
  }finally{rmSync(dir,{force:true,recursive:true});}
});

test('CLI without explicit --execute never reads secrets or contacts Cloudflare',()=>{
  const path=fileURLToPath(new URL('../scripts/collect_cloudflare_observer_telemetry.mjs',import.meta.url));
  const env={...process.env,CLOUDFLARE_ACCOUNT_ID:ACCOUNT,CLOUDFLARE_OBSERVABILITY_TOKEN:TOKEN};
  const r=spawnSync(process.execPath,[path],{encoding:'utf8',timeout:15000,env});
  assert.equal(r.status,2);
  assert.doesNotMatch(r.stderr,new RegExp(TOKEN));
  assert.doesNotMatch(r.stderr,new RegExp(ACCOUNT));
  const bad=spawnSync(process.execPath,[path,'--execute','2026-11-09',DEPLOYMENT,'relative.json'],
    {encoding:'utf8',timeout:15000,env});
  assert.equal(bad.status,2);
  assert.match(bad.stderr,/output_must_be_absolute_path/);
  assert.doesNotMatch(bad.stderr,new RegExp(TOKEN));
});
