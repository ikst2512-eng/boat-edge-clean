import {env} from 'cloudflare:workers';
import {describe,it,expect} from 'vitest';
import researchWorker from '../claim_lab_only.mjs';

const JST=9*60*60*1000;
const slot=(day,h,m)=>Date.UTC(2026,10,day,h,m)-JST;
const gate=name=>env.CLAIMS_RESEARCH.get(env.CLAIMS_RESEARCH.idFromName(name));

describe('real local Workerd SQLite Durable Object at-most-one lab (never dispatches)',()=>{
  it('32 simultaneous cloudflare-style calls reserve exactly one claimant', async()=>{
    const g=gate('claim-lab-concurrent-1');
    const s=slot(8,7,4);
    const claims=await Promise.all(Array.from({length:32},()=>g.reserve('clean',s)));
    expect(claims.filter(x=>x.acquired)).toHaveLength(1);
    expect(claims.filter(x=>!x.acquired)).toHaveLength(31);
    expect(claims.filter(x=>x.acquired)[0].claim_token).toMatch(/^[0-9a-f-]{36}$/);
    expect(claims.filter(x=>!x.acquired).every(x=>!('claim_token' in x))).toBe(true);
    expect((await g.inspect('clean',s)).claimed).toBe(true);
    expect(claims.every(x=>x.formal===false && x.forecast_saved_proven===false)).toBe(true);
  });

  it('a new stub to the same object sees the durable, non-expiring claim',async()=>{
    const name='claim-lab-new-stub';
    const s=slot(8,7,7);
    expect((await gate(name).reserve('four_mode',s)).acquired).toBe(true);
    const freshStub=gate(name);
    expect((await freshStub.reserve('four_mode',s)).acquired).toBe(false);
    const state=await freshStub.inspect('four_mode',s);
    expect(state).toMatchObject({claimed:true,reported_run_id:null,formal:false});
    expect(JSON.stringify(state)).not.toContain('claim_token');
  });

  it('a missing run ID is never mistaken for an unclaimed slot and never auto-retried',async()=>{
    const g=gate('claim-lab-ambiguous-timeout');
    const s=slot(8,7,19);
    expect((await g.reserve('clean',s)).acquired).toBe(true);
    // Represents a 204/timeout/unknown POST outcome: caller cannot safely
    // release the claim or retry merely because it lacks a run ID.
    expect((await g.inspect('clean',s)).reported_run_id).toBeNull();
    for(let i=0;i<6;i++) expect((await g.reserve('clean',s)).acquired).toBe(false);
  });

  it('independent workflow and day keys are not falsely deduplicated',async()=>{
    const g=gate('claim-lab-independent-keys');
    const values=[
      ['clean',slot(8,7,4)],
      ['four_mode',slot(8,7,7)],
      ['clean',slot(8,7,19)],
      ['clean',slot(9,7,4)],
    ];
    for(const [kind,s] of values){
      expect((await g.reserve(kind,s)).acquired).toBe(true);
      expect((await g.reserve(kind,s)).acquired).toBe(false);
    }
  });

  it('reported GitHub run ID can be attached at most once but is never formal proof',async()=>{
    const g=gate('claim-lab-run-id');
    const s=slot(8,7,34);
    const winner=await g.reserve('clean',s);
    expect(winner.acquired).toBe(true);
    const saved=await g.reportRunId('clean',s,winner.claim_token,345678901);
    expect(saved).toMatchObject({recorded:true,reported_run_id:345678901,github_run_verified:false,formal:false});
    expect((await g.reportRunId('clean',s,winner.claim_token,987654321)).recorded).toBe(false);
    const state=await g.inspect('clean',s);
    expect(state).toMatchObject({claimed:true,reported_run_id:345678901,
      github_run_verified:false,forecast_saved_proven:false,formal:false});
    expect((await g.reserve('clean',s)).acquired).toBe(false);
    expect(JSON.stringify(state)).not.toContain(winner.claim_token);
  });

  it('cannot record a run ID for an unclaimed slot',async()=>{
    const g=gate('claim-lab-no-claim');
    const s=slot(8,7,49);
    const res=await g.reportRunId('clean',s,crypto.randomUUID(),12345);
    expect(res.recorded).toBe(false);
    expect((await g.inspect('clean',s)).claimed).toBe(false);
  });

  it('rejects invalid kind, non-planned slot, invalid run ID before SQLite writing',async()=>{
    const g=gate('claim-lab-malformed-inputs');
    const valid=slot(8,7,4);
    for(const [kind,s] of [['typo',valid],['clean',valid+60_000],
      ['four_mode',valid],['clean',NaN],['clean',0]]){
      const rejected=await g.reserve(kind,s);
      expect(rejected.acquired).toBe(false);
      expect(rejected.status).toBe('rejected_invalid_slot');
    }
    const invalidRun=await g.reportRunId('clean',valid,crypto.randomUUID(),-1);
    expect(invalidRun.recorded).toBe(false);
    expect(invalidRun.error).toBe('research_invalid_run_id');
    expect((await g.inspect('clean',valid)).claimed).toBe(false);
  });

  it('a losing claimant cannot attach a forged run ID or steal the winning token',async()=>{
    const g=gate('claim-lab-owner-token');
    const s=slot(8,8,4);
    const winner=await g.reserve('clean',s);
    const loser=await g.reserve('clean',s);
    expect(winner.acquired).toBe(true);
    expect(loser.acquired).toBe(false);
    expect(loser.claim_token).toBeUndefined();
    expect((await g.reportRunId('clean',s,crypto.randomUUID(),991122)).recorded).toBe(false);
    expect((await g.reportRunId('clean',s,'not-a-uuid',991122)).error).toBe('research_invalid_claim_token');
    expect((await g.reportRunId('clean',s,undefined,991122)).error).toBe('research_invalid_claim_token');
    expect((await g.inspect('clean',s)).reported_run_id).toBeNull();
    expect((await g.reportRunId('clean',s,winner.claim_token,991122)).recorded).toBe(true);
    const inspect=await g.inspect('clean',s);
    expect(inspect.reported_run_id).toBe(991122);
    expect(JSON.stringify(inspect)).not.toContain(winner.claim_token);
    expect((await g.reportRunId('clean',s,winner.claim_token,991123)).recorded).toBe(false);
  });

  it('a reservation token is scoped to exactly one workflow-slot and one object',async()=>{
    const a=gate('claim-lab-token-scope-a');
    const b=gate('claim-lab-token-scope-b');
    const one=slot(8,9,4),two=slot(8,9,19);
    const winner=await a.reserve('clean',one);
    const other=await a.reserve('clean',two);
    const anotherObj=await b.reserve('clean',one);
    expect(winner.acquired && other.acquired && anotherObj.acquired).toBe(true);
    expect((await a.reportRunId('clean',two,winner.claim_token,111)).recorded).toBe(false);
    expect((await b.reportRunId('clean',one,winner.claim_token,111)).recorded).toBe(false);
    expect((await a.reportRunId('four_mode',one,winner.claim_token,111)).recorded).toBe(false);
    expect((await a.reportRunId('clean',two,other.claim_token,222)).recorded).toBe(true);
    expect((await b.reportRunId('clean',one,anotherObj.claim_token,333)).recorded).toBe(true);
  });

  it('research Worker has no scheduled handler and public HTTP always returns 403',async()=>{
    expect(Object.keys(researchWorker)).toEqual(['fetch']);
    for(const method of ['GET','POST']){
      const response=await researchWorker.fetch(new Request('https://example.invalid/claim',{method}));
      expect(response.status).toBe(403);
    }
  });

  it('new distinct Durable Object names have isolated storage',async()=>{
    const s=slot(8,7,4);
    expect((await gate('claim-lab-isolated-a').reserve('clean',s)).acquired).toBe(true);
    expect((await gate('claim-lab-isolated-b').reserve('clean',s)).acquired).toBe(true);
    // IMPORTANT: To coordinate real Cloudflare invocations, EVERY caller must
    // use one stable deterministic namespace/name. Different names are NOT a
    // global lock. This lab does not bind to any live recovery Worker.
  });
});
