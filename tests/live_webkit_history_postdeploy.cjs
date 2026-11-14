'use strict';
// Strict post-deploy check: the real published GitHub Pages HTML/JS is loaded
// through actual network requests in WebKit. No page.route/route.fulfill,
// HAR replays, injected application assets, CORS shims or API response mocks.
// Navigation-only acceptance: not live odds, six racers, prediction accuracy,
// Render Free cold-start reliability, or a physical iPhone Safari device.
const assert = require('node:assert/strict');
const {webkit} = require('playwright');

const SITE = 'https://ikst2512-eng.github.io/boat-edge-clean/';
(async () => {
  const browser = await webkit.launch({headless: true});
  try {
    const page = await browser.newPage({viewport: {width: 390, height: 844}});
    const errors = [];
    page.on('pageerror', err => errors.push(String(err).slice(0, 250)));
    await page.addInitScript(() => {
      window.__publicHistoryWrites = {replace: 0, push: 0};
      for (const name of ['replaceState', 'pushState']) {
        const raw = history[name].bind(history);
        history[name] = (...args) => {
          window.__publicHistoryWrites[name === 'replaceState' ? 'replace' : 'push']++;
          return raw(...args);
        };
      }
    });
    const response = await page.goto(SITE + '?date=2026-10-30&venue=1&race=1', {
      waitUntil: 'domcontentloaded', timeout: 45000,
    });
    assert.equal(response && response.status(), 200, 'Published Pages is not HTTP 200');
    assert.match(await page.title(), /BOAT EDGE CLEAN/, 'Wrong public UI');
    await page.waitForFunction(() =>
      document.documentElement.dataset.cleanNavigationInit === '1' &&
      typeof setView === 'function' && typeof render === 'function' &&
      document.querySelectorAll('.race-detail-shortcuts button').length === 4,
    null, {timeout: 20000});
    // Ensure this is the released navigation owner, rather than quietly
    // passing the old published assets while exercising a synthetic fixture.
    assert.equal(await page.evaluate(() => window.__boatEdgeNavigationOwnsHistory),
      true, 'Published navigation.js hotfix has NOT reached GitHub Pages');
    // The public page starts at HOME; enter a race panel before clicking its
    // shortcuts, which are intentionally hidden on home.
    await page.evaluate(async () => {
      setView('forecast');
      render();
      await Promise.resolve();
    });
    await page.waitForFunction(() =>
      activeView === 'forecast' && !document.querySelector('.race-detail-shortcuts').hidden,
    null, {timeout: 15000});
    const baseline = await page.evaluate(() => ({...window.__publicHistoryWrites}));
    // A few genuine UI tab actions should not multiply history writes; the
    // exhaustive 130/40 stress belongs in OFFLINE WebKit CI to avoid live API load.
    for (const view of ['card', 'exhibit', 'result', 'forecast']) {
      await page.locator('.race-detail-shortcuts button[data-race-view="'+view+'"]').click();
      await page.waitForFunction(expected => activeView === expected &&
        history.state?.snapshot?.view === expected &&
        new URL(location.href).searchParams.get('screen') === expected, view,
      {timeout: 15000});
    }
    const afterTabs = await page.evaluate(() => ({...window.__publicHistoryWrites}));
    assert.equal(afterTabs.replace, baseline.replace,
      'Published tab navigation amplified replaceState');
    assert.equal(afterTabs.push-baseline.push, 4,
      'Published tab navigation must record exactly four view changes');

    const beforeRace = await page.evaluate(() => ({
      counts: {...window.__publicHistoryWrites},
      currentRace: s.race,
    }));
    await page.evaluate(async () => {
      s.race = s.race === 1 ? 2 : 1;
      render();
      await Promise.resolve(); // let the navigation queueMicrotask flush
    });
    const afterRace = await page.evaluate(() => ({
      counts: {...window.__publicHistoryWrites},
      race: s.race,
      urlRace: new URL(location.href).searchParams.get('race'),
      historyRace: history.state?.snapshot?.race,
    }));
    assert.equal(afterRace.urlRace, String(afterRace.race), 'Published race URL stale');
    assert.equal(afterRace.historyRace, afterRace.race, 'Published race history stale');
    assert.equal(afterRace.counts.replace, beforeRace.counts.replace,
      'Published race change amplified replaceState');
    assert.equal(afterRace.counts.push-beforeRace.counts.push, 1,
      'Published race change must push one history entry');

    await page.evaluate(() => history.back());
    await page.waitForFunction(old => s.race === old &&
      history.state?.snapshot?.race === old &&
      Number(new URL(location.href).searchParams.get('race')) === old,
    beforeRace.currentRace, {timeout: 15000});
    const afterBack = await page.evaluate(() => ({...window.__publicHistoryWrites}));
    await page.evaluate(() => history.forward());
    await page.waitForFunction(expected => s.race === expected &&
      history.state?.snapshot?.race === expected &&
      Number(new URL(location.href).searchParams.get('race')) === expected,
    afterRace.race, {timeout: 15000});
    const afterForward = await page.evaluate(() => ({...window.__publicHistoryWrites}));
    assert.deepEqual(afterBack, afterForward,
      'History back/forward introduced extra writes');
    assert.equal(afterBack.replace, afterRace.counts.replace,
      'Back/forward introduced redundant replaceState');
    assert.equal(afterBack.push, afterRace.counts.push,
      'Back/forward introduced redundant pushState');
    if (errors.some(x => /SecurityError|history\.replaceState|history\.pushState/.test(x)))
      throw Error('Published WebKit history pageerror ' + JSON.stringify(errors));
    console.log('LIVE_PUBLISHED_WEBKIT_HISTORY_PASS ' + JSON.stringify({
      realPublicPages: true, realWebKit: true, noMocks: true,
      tabChanges: 4, raceChanges: 1, backForward: true,
      tabWrites: afterTabs, raceWrites: afterRace.counts,
      nonHistoryPageErrors: errors.length,
    }));
    console.log('DO_NOT_INFER: physical_iPhone_Safari, archive_CORS, full_live_API, stable_idle_wake');
  } finally { await browser.close(); }
})().catch(error => {
  console.error('LIVE_PUBLISHED_WEBKIT_HISTORY_FAIL ' + (error.stack || String(error)));
  process.exitCode = 1;
});
