// Isolated RESEARCH-ONLY prototype. Never imported by production recovery or
// zero-token observer. No GitHub host, token, fetch dispatch, alarm or Cron.
// SQLite claim persistence is a candidate fix for Cloudflare-vs-Cloudflare
// duplicates ONLY: native GitHub schedules and external Render do not use it.
// Once claimed, a slot is NEVER automatically released, including when a
// potential external POST returned 204, timed out, or raised an exception.
// This trades missed recovery for at-most-one claimant (fail-closed).
import {DurableObject} from 'cloudflare:workers';
import {plannedSlots,WORKFLOWS} from './independent_capture_slots.mjs';

export class CaptureClaimResearch extends DurableObject {
  constructor(ctx,env){
    super(ctx,env);
    ctx.blockConcurrencyWhile(async()=>{
      ctx.storage.sql.exec(`CREATE TABLE IF NOT EXISTS research_claims (
        kind TEXT NOT NULL,
        slot_ms INTEGER NOT NULL,
        reported_run_id INTEGER,
        claim_token TEXT NOT NULL,
        PRIMARY KEY(kind,slot_ms)
      )`);
    });
  }

  validSlot(kind,slotMs){
    return Object.prototype.hasOwnProperty.call(WORKFLOWS,kind) &&
      Number.isSafeInteger(slotMs) && slotMs>0 &&
      plannedSlots(kind,new Date(slotMs)).includes(slotMs);
  }

  async reserve(kind,slotMs){
    if(!this.validSlot(kind,slotMs)) return {
      kind,slot_ms:slotMs,acquired:false,status:'rejected_invalid_slot',
      forecast_saved_proven:false,formal:false,
    };
    // A single SQLite INSERT with UNIQUE constraint makes winner election
    // atomic even if several Worker invocations invoke this DO concurrently.
    // No await or external I/O between existence test and insertion.
    // An unguessable one-time claimant token is stored with the atomic claim.
    // It is returned ONLY to the winning caller. Never log or expose the
    // token through inspect(); a different caller cannot attach a forged ID.
    const token=crypto.randomUUID();
    const inserted=this.ctx.storage.sql.exec(
      'INSERT INTO research_claims(kind,slot_ms,claim_token) VALUES(?,?,?) ON CONFLICT DO NOTHING RETURNING slot_ms',
      kind,slotMs,token).toArray();
    const acquired=inserted.length===1;
    return {kind,slot_ms:slotMs,acquired,
      status:acquired?'claimed_uncertain':'already_claimed',
      ...(acquired?{claim_token:token}:{}),
      forecast_saved_proven:false, formal:false};
  }

  async reportRunId(kind,slotMs,claimToken,runId){
    if(!this.validSlot(kind,slotMs)) return {recorded:false,
      error:'research_invalid_slot',github_run_verified:false,forecast_saved_proven:false,formal:false};
    if(typeof claimToken!=='string' ||
       !/^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(claimToken))
      return {recorded:false,error:'research_invalid_claim_token',
        github_run_verified:false,forecast_saved_proven:false,formal:false};
    if(!Number.isSafeInteger(runId)||runId<=0) return {recorded:false,
      error:'research_invalid_run_id',github_run_verified:false,forecast_saved_proven:false,formal:false};
    // Can record a run ID at most once. Does NOT prove GitHub run completion.
    const saved=this.ctx.storage.sql.exec(
      'UPDATE research_claims SET reported_run_id=? WHERE kind=? AND slot_ms=? AND claim_token=? AND reported_run_id IS NULL RETURNING reported_run_id',
      runId,kind,slotMs,claimToken).toArray();
    return {recorded:saved.length===1,
      reported_run_id:saved.length?runId:null,github_run_verified:false,
      forecast_saved_proven:false,formal:false};
  }

  async inspect(kind,slotMs){
    if(!this.validSlot(kind,slotMs)) return {
      claimed:false,error:'research_invalid_slot',
      github_run_verified:false,forecast_saved_proven:false,formal:false,
    };
    const rows=this.ctx.storage.sql.exec(
      'SELECT reported_run_id FROM research_claims WHERE kind=? AND slot_ms=?',kind,slotMs).toArray();
    return {claimed:rows.length===1,reported_run_id:rows[0]?.reported_run_id??null,
      github_run_verified:false,forecast_saved_proven:false,formal:false};
  }
}

// No public access, no HTTP API, no scheduled handler: cannot trigger recovery.
// Used solely by read-only PR Workerd tests via the local DO binding.
export default {
  async fetch(){return new Response('research_not_available',{status:403});},
};
