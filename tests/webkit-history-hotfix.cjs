'use strict';
// Isolated navigation hotfix regression: real local WebKit, no published Pages/Render traffic.
const fs = require('node:fs');
const path = require('node:path');
const http = require('node:http');
const {webkit} = require('playwright');

const root = path.resolve(__dirname, '..');
const assetTypes = {
  '/': ['index.html', 'text/html; charset=utf-8'],
  '/index.html': ['index.html', 'text/html; charset=utf-8'],
  '/navigation.js': ['navigation.js', 'text/javascript; charset=utf-8'],
  '/entry_scenario.js': ['entry_scenario.js', 'text/javascript; charset=utf-8'],
  '/secondary_navigation.js': ['secondary_navigation.js', 'text/javascript; charset=utf-8']
};
const html = fs.readFileSync(path.join(root, 'index.html'), 'utf8');
const guarded = html.match(/if\(url\.href!==location\.href&&!window\.__boatEdgeNavigationOwnsHistory\)history\.replaceState\(null,'',url\);/g) || [];
if (guarded.length !== 2) {
  throw Error('DRAFT_URL_WRITES_MUST_BE_IDEMPOTENT: both the race render and view change must guard their base URL writes');
}

const server = http.createServer((request, response) => {
  const pathname = new URL(request.url, 'http://localhost').pathname;
  const asset = assetTypes[pathname];
  if (!asset) {
    response.writeHead(404, {'content-type': 'text/plain'});
    response.end('not found');
    return;
  }
  response.writeHead(200, {'content-type': asset[1], 'cache-control': 'no-store'});
  response.end(fs.readFileSync(path.join(root, asset[0])));
});

(async () => {
  let browser;
  try {
    await new Promise((resolve, reject) => {
      server.once('error', reject);
      server.listen(0, '127.0.0.1', resolve);
    });
    const localOrigin = 'http://127.0.0.1:' + server.address().port;
    browser = await webkit.launch({headless: true});
    const page = await browser.newPage({viewport: {width: 390, height: 844}});
    await page.addInitScript(() => {
      window.__historyMutationCounts = {replace: 0, push: 0};
      for (const method of ['replaceState', 'pushState']) {
        const original = history[method].bind(history);
        history[method] = (...args) => {
          window.__historyMutationCounts[method === 'replaceState' ? 'replace' : 'push']++;
          return original(...args);
        };
      }
    });
    // Preserve local asset delivery; external data is intentionally unavailable.
    // This isolates history throttling, not live exhibition, CORS, or betting accuracy.
    await page.route('**/*', route => {
      if (route.request().url().startsWith(localOrigin + '/')) return route.continue();
      return route.fulfill({
        status: 503,
        contentType: 'text/plain',
        headers: {'access-control-allow-origin': '*'},
        body: 'offline test fixture'
      });
    });
    await page.goto(localOrigin + '/?date=2026-10-30&venue=1&race=1', {
      waitUntil: 'domcontentloaded', timeout: 30000
    });
    await page.waitForFunction(() => typeof setView === 'function' && typeof render === 'function');
    const verdict = await page.evaluate(async () => {
      const initialWrites = {...window.__historyMutationCounts};
      for (let i = 0; i < 130; i++) setView('forecast');
      const afterSameView = {...window.__historyMutationCounts};
      if (afterSameView.replace !== initialWrites.replace || afterSameView.push !== initialWrites.push)
        throw Error('SAME_VIEW_MUTATED_BROWSER_HISTORY '+JSON.stringify({initialWrites,afterSameView}));
      // A repeated re-render of an unchanged race must not burn WebKit's history quota.
      render();
      await Promise.resolve();
      const stableWrites = {...window.__historyMutationCounts};
      for (let i = 0; i < 8; i++) render();
      await Promise.resolve();
      const afterRepeatedRender = {...window.__historyMutationCounts};
      if (afterRepeatedRender.replace !== stableWrites.replace || afterRepeatedRender.push !== stableWrites.push)
        throw Error('SAME_RACE_RENDER_MUTATED_BROWSER_HISTORY '+JSON.stringify({stableWrites,afterRepeatedRender}));
      const unchanged = new URL(location.href);
      if (unchanged.searchParams.get('race') !== '1') throw Error('SAME_RACE_URL_CHANGED');
      if (unchanged.searchParams.has('view')) throw Error('LEGACY_VIEW_QUERY_LEFTOVER');
      // A real race change still must update the browser address exactly once.
      s.race = 2;
      render();
      // navigation.js intentionally schedules the new history entry as a microtask.
      await Promise.resolve();
      const changed = new URL(location.href);
      if (changed.searchParams.get('race') !== '2') throw Error('RACE_CHANGE_URL_MISSING');
      if (changed.searchParams.get('venue') !== '1') throw Error('VENUE_URL_CHANGED');
      return {sameViewCalls: 130, repeatedRenders: 8, stableWrites, afterRepeatedRender, raceBefore: 1, raceAfter: Number(changed.searchParams.get('race'))};
    });
    console.log('PASS_DRAFT_WEBKIT_IDEMPOTENT_HISTORY '+JSON.stringify(verdict));
    // Back/forward must restore the selected race without burning any
    // additional replaceState/pushState calls for an already-restored entry.
    const beforeBack = await page.evaluate(() => ({...window.__historyMutationCounts}));
    await page.evaluate(() => history.back());
    await page.waitForFunction(() => s.race === 1 &&
      history.state?.snapshot?.race === 1 &&
      new URL(location.href).searchParams.get('race') === '1');
    const afterBack = await page.evaluate(() => ({...window.__historyMutationCounts}));
    if (afterBack.replace !== beforeBack.replace || afterBack.push !== beforeBack.push)
      throw Error('BACK_NAVIGATION_USED_REDUNDANT_HISTORY_WRITE '+JSON.stringify({beforeBack,afterBack}));
    await page.evaluate(() => history.forward());
    await page.waitForFunction(() => s.race === 2 &&
      history.state?.snapshot?.race === 2 &&
      new URL(location.href).searchParams.get('race') === '2');
    const afterForward = await page.evaluate(() => ({...window.__historyMutationCounts}));
    if (afterForward.replace !== afterBack.replace || afterForward.push !== afterBack.push)
      throw Error('FORWARD_NAVIGATION_USED_REDUNDANT_HISTORY_WRITE '+JSON.stringify({afterBack,afterForward}));
    // The four actual shortcut buttons must still update both view and URL
    // after history throttling protections are applied.
    for (const view of ['card', 'exhibit', 'result', 'forecast']) {
      await page.locator('.race-detail-shortcuts button[data-race-view="'+view+'"]').click();
      await page.waitForFunction(expected => activeView === expected &&
        history.state?.snapshot?.view === expected &&
        new URL(location.href).searchParams.get('screen') === expected, view);
    }
    console.log('PASS_DRAFT_WEBKIT_BACK_FORWARD_FOUR_TABS '+JSON.stringify({
      raceRestored: true, zeroHistoryWritesOnBackForward: true,
      views: ['card','exhibit','result','forecast'],
      beforeBack, afterForward
    }));
    // Forty genuine changes are below WebKit's 100-history-writes limit only
    // if a race change results in ONE pushState, not base replace + restore + push.
    const stress = await page.evaluate(async () => {
      const before = {...window.__historyMutationCounts};
      const sequence = [];
      for (let i=0; i<40; i++) {
        const race=(i%2)+1;
        s.race=race;
        render();
        await Promise.resolve();
        if (history.state?.snapshot?.race !== race ||
            Number(new URL(location.href).searchParams.get('race')) !== race)
          throw Error('RAPID_RACE_HISTORY_STALE '+JSON.stringify({race,iteration:i,actual:history.state?.snapshot}));
        sequence.push(race);
      }
      const after={...window.__historyMutationCounts};
      if (after.replace !== before.replace || after.push-before.push !== 40)
        throw Error('RACE_HISTORY_WRITE_AMPLIFICATION '+JSON.stringify({before,after}));
      return {raceChanges:sequence.length, writesPerChange:1,
        replaceWrites:after.replace-before.replace,
        pushWrites:after.push-before.push,
        finalRace:s.race};
    });
    console.log('PASS_DRAFT_WEBKIT_FORTY_RACE_CHANGES '+JSON.stringify(stress));
    console.log('UNASSESSED: published Pages, real Render transport, live CORS, predeadline exhibition, physical iPhone Safari');
  } catch (error) {
    console.error('FAIL_DRAFT_WEBKIT_IDEMPOTENT_HISTORY '+String(error));
    process.exitCode = 1;
  } finally {
    if (browser) await browser.close();
    if (server.listening) await new Promise(resolve => server.close(resolve));
  }
})();
