'use strict';
// Manual postdeploy gate: compare actual public Pages AND Render asset BYTES
// with the checked-out release candidate. No browser hooks, proxying or mocks.
// It proves served frontend parity, NOT deployed Render server.py commit SHA,
// physical iPhone hardware or long-term uptime.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const crypto = require('node:crypto');

const PAGES = 'https://ikst2512-eng.github.io/boat-edge-clean/';
const RENDER = 'https://boat-edge-clean.onrender.com/';
const ASSETS = [
  {path:'index.html', urls:[PAGES,RENDER]},
  {path:'navigation.js', urls:[PAGES+'navigation.js',RENDER+'navigation.js']},
];
const hash = bytes => crypto.createHash('sha256').update(bytes).digest('hex');
function assertEqualBytes(name, expected, actual) {
  assert.ok(Buffer.isBuffer(expected)&&Buffer.isBuffer(actual),
    name+' must compare binary bytes');
  assert.ok(expected.length>0&&actual.length>0,
    name+' must not be empty');
  assert.equal(hash(actual),hash(expected),
    name+' public Pages bytes differ from checked-out release source');
  return hash(expected);
}
async function fetchBytes(url, releaseId) {
  const u=new URL(url);
  // Bypass stale edge caches without changing the published static asset.
  u.searchParams.set('release_asset_check',releaseId);
  let lastError;
  for(let attempt=1;attempt<=3;attempt++) {
    try {
      const response=await fetch(u,{cache:'no-store',signal:AbortSignal.timeout(30000)});
      assert.equal(response.status,200,
        'Published asset HTTP '+response.status+' '+u.pathname);
      const bytes=Buffer.from(await response.arrayBuffer());
      assert.ok(bytes.length>0,'Published asset is empty '+u.pathname);
      return bytes;
    }catch(error) {
      lastError=error;
      if(attempt<3)await new Promise(resolve=>setTimeout(resolve,1500));
    }
  }
  throw lastError;
}
async function verifyPublishedAssets() {
  const release=process.env.GITHUB_SHA;
  assert.match(release||'',/^[a-f0-9]{40}$/,
    'Explicit checked-out 40-hex GitHub release SHA required');
  for(const asset of ASSETS){
    const expected=fs.readFileSync(asset.path);
    for(const url of asset.urls){
      const actual=await fetchBytes(url,release);
      const digest=assertEqualBytes(asset.path+' '+new URL(url).hostname,expected,actual);
      console.log('PUBLIC_FRONTEND_ASSET_BYTE_IDENTICAL host='+new URL(url).hostname+
        ' path='+asset.path+' sha256='+digest+' checked_out_commit='+release);
    }
  }
  console.log('PUBLIC_PAGES_RENDER_FRONTEND_PARITY_VERIFIED');
  console.log('DO_NOT_INFER: Render_server_code_SHA, physical_iPhone, full_uptime, accuracy');
}
function selfTest() {
  const good=Buffer.from('candidate-asset');
  const same=Buffer.from('candidate-asset');
  const stale=Buffer.from('previous-asset');
  assert.equal(assertEqualBytes('self-test',good,same),hash(good));
  assert.throws(()=>assertEqualBytes('self-test',good,stale),
    /public Pages bytes differ/);
  assert.throws(()=>assertEqualBytes('self-test',Buffer.alloc(0),same),
    /must not be empty/);
  console.log('PUBLIC_PAGES_ASSET_GATE_SELF_TEST_PASS matching=accepted stale=rejected empty=rejected');
}
if(process.argv.slice(2).includes('--self-test')){
  selfTest();
}else {
  verifyPublishedAssets().catch(error=>{
    console.error('PUBLIC_PAGES_ASSET_GATE_FAIL '+(error.stack||String(error)));
    process.exitCode=1;
  });
}
