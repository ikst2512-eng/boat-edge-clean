// Independent isolated DO runtime: never reuse the production recovery
// service config or its optional GitHub PAT. Runs in local Workerd only.
import {cloudflareTest} from '@cloudflare/vitest-plugin';
import {defineConfig} from 'vitest/config';

export default defineConfig({
  plugins:[cloudflareTest({wrangler:{configPath:'./wrangler.claim-lab.toml'}})],
  test:{
    include:['test/claim_lab.spec.mjs'],
    testTimeout:20000,
  },
});
