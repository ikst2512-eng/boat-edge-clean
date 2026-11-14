// Post-deploy gate only: real public GitHub Pages -> real Render HTTPS.
// Never route/mock/intercept any request. This is intentionally NOT run on PR,
// because the production fix is not yet deployed and should fail until it is.
const assert = require('node:assert/strict');
const {chromium, webkit} = require('playwright');

const PAGES_ORIGIN = 'https://ikst2512-eng.github.io';
const PAGES_URL = PAGES_ORIGIN + '/boat-edge-clean/';
const API = 'https://boat-edge-clean.onrender.com/api/four-mode-archive';
const cases = [
  {code: '202611061006', expected: 200},
  {code: '209901010101', expected: 404}, // syntactically valid, no historical archive
  {code: 'not-a-race-code', expected: 422},
];

async function checkDirectHeaders() {
  for (const {code,expected} of cases) {
    const response = await fetch(API + '?code=' + encodeURIComponent(code), {
      headers: {Origin: PAGES_ORIGIN},
      signal: AbortSignal.timeout(30000),
    });
    const acao = response.headers.get('access-control-allow-origin');
    assert.equal(response.status, expected,
      'Unexpected public archive HTTP response for ' + code);
    assert.equal(acao, PAGES_ORIGIN,
      'Production archive CORS header is absent or incorrect for ' + code);
    const data = await response.json();
    assert.ok(data && typeof data === 'object',
      'Live archive response is not a JSON object for ' + code);
    console.log('LIVE_ARCHIVE_RAW_CORS_PASS code='+code+' status='+response.status+' acao='+acao);
  }
  // Security check: never reflect an untrusted Origin back to the caller.
  const untrusted = 'https://untrusted-site.example';
  const negative = await fetch(API + '?code=not-a-race-code', {
    headers: {Origin: untrusted},
    signal: AbortSignal.timeout(30000),
  });
  assert.equal(negative.status, 422, 'Unexpected live negative-control HTTP status');
  assert.equal(negative.headers.get('access-control-allow-origin'), PAGES_ORIGIN,
    'Live archive API CORS allowlist must remain fixed to Pages, not reflect Origin');
  console.log('LIVE_ARCHIVE_UNTRUSTED_ORIGIN_NOT_REFLECTED');
}

async function checkBrowser(name, engine) {
  const browser = await engine.launch({headless: true});
  try {
    const page = await browser.newPage({viewport: {width: 390, height: 844}});
    const pageResponse = await page.goto(PAGES_URL, {
      waitUntil: 'domcontentloaded', timeout: 30000,
    });
    assert.equal(pageResponse && pageResponse.status(), 200,
      name + ' public Pages navigation failed');
    assert.match(await page.title(), /BOAT EDGE CLEAN/,
      name + ' public Pages title is unexpected');

    for (const {code,expected} of cases) {
      const result = await page.evaluate(async ({url}) => {
        try {
          const r = await fetch(url, {
            cache: 'no-store',
            signal: AbortSignal.timeout(25000),
          });
          const payload = await r.json();
          return {blocked: false, status: r.status,
            payloadOk: !!payload && typeof payload === 'object'};
        } catch (e) {
          return {blocked: true, reason: String(e).slice(0, 160)};
        }
      }, {url: API + '?code=' + encodeURIComponent(code)});
      assert.equal(result.blocked, false,
        name + ' public Pages-to-Render cross-origin fetch blocked ' + code +
        ' ' + JSON.stringify(result));
      assert.equal(result.status, expected,
        name + ' public cross-origin response status ' + code);
      assert.equal(result.payloadOk, true,
        name + ' public cross-origin JSON missing ' + code);
      console.log('LIVE_PUBLISHED_PAGES_CORS_PASS engine='+name+
        ' code='+code+' status='+expected);
    }
  } finally {
    await browser.close();
  }
}

(async () => {
  console.log('LIVE_CORS_GATE public_hosts_only=true mocks=false redirects=browser_default');
  await checkDirectHeaders();
  await checkBrowser('chromium', chromium);
  await checkBrowser('webkit', webkit);
  console.log('LIVE_PUBLISHED_PAGES_TO_RENDER_CORS_VERIFIED');
  console.log('NOTE: this does not certify 4-tab WebKit history, 6-boat data, uptime, or Safari on a physical iPhone');
})().catch(e => {
  console.error('LIVE_PUBLISHED_CORS_FAILURE ' + (e.stack || String(e)));
  process.exitCode = 1;
});
