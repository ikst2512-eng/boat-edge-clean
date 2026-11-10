#!/usr/bin/env node
// Owner-operated, explicitly opt-in Cloudflare OBSERVER TELEMETRY export.
// Query ONLY: two POSTs to the exact Cloudflare Workers Observability query
// endpoint. NO Worker deployment, GitHub traffic, capture, dispatch or retries.
// Secrets are never added to the JSON artifact or printed to stdout/stderr.
import {writeFileSync} from 'node:fs';
import {createHash} from 'node:crypto';
import {resolve,sep} from 'node:path';
import {fileURLToPath} from 'node:url';
import {buildObserverTelemetryQueries, API_SCHEMA, auditTelemetryApiPages}
  from '../cloudflare/audit_observer_api_pages.mjs';
import {OBSERVER_NAME} from '../cloudflare/audit_observer_telemetry.mjs';

const REPO_ROOT=fileURLToPath(new URL('../',import.meta.url));
const ID=/^[a-f0-9]{32}$/i;
const VERSION=/^[A-Za-z0-9_.:-]{6,128}$/;
const MAX_RESPONSE_BYTES=12*1024*1024;
const WAIT_AFTER_DAY_MS=15*60*1000;
const ENDPOINT=accountId=>
  'https://api.cloudflare.com/client/v4/accounts/'+accountId+
  '/workers/observability/telemetry/query';

function allowedOutput(outputPath){
  if(typeof outputPath!=='string'||!outputPath.startsWith('/')||outputPath.includes('\0'))
    throw Error('output_must_be_absolute_path');
  const full=resolve(outputPath);
  if(full===REPO_ROOT || full.startsWith(REPO_ROOT+sep))
    throw Error('output_inside_source_checkout_disallowed');
  return full;
}
export async function collectObserverTelemetry({
  utcDay,accountId,token,deploymentId,now=Date.now(),
  fetcher=fetch,
}){
  const planned=buildObserverTelemetryQueries(utcDay);
  if(!ID.test(accountId??''))throw Error('invalid_cloudflare_account_id');
  if(typeof token!=='string'||token.length<16||/\s/.test(token))
    throw Error('cloudflare_observability_token_required');
  if(!VERSION.test(deploymentId??''))throw Error('observer_deployment_id_required');
  if(typeof fetcher!=='function')throw Error('fetcher_required');
  if(!Number.isSafeInteger(now) || now < planned.events_request.timeframe.to+WAIT_AFTER_DAY_MS)
    throw Error('utc_day_not_complete_or_ingestion_grace');
  const endpoint=ENDPOINT(accountId);
  async function one(request){
    let response;
    try{
      response=await fetcher(endpoint,{
        method:'POST',redirect:'error',
        headers:{
          Authorization:'Bearer '+token,
          'Content-Type':'application/json',
          Accept:'application/json',
        },
        body:JSON.stringify(request),
        signal:AbortSignal.timeout(30000),
      });
    }catch{throw Error('cloudflare_query_network_or_timeout_failure')}
    if(!response||response.status!==200)throw Error('cloudflare_query_non_200');
    let raw;
    try{raw=await response.text()}catch{throw Error('cloudflare_query_body_unreadable')}
    if(typeof raw!=='string'||Buffer.byteLength(raw,'utf8')>MAX_RESPONSE_BYTES)
      throw Error('cloudflare_query_response_oversize');
    // A compromised or unexpected endpoint must not echo credentials into a
    // file. Do not inspect/emit the remote error body when this happens.
    if(raw.includes(token)||/Authorization\s*:|Bearer\s+[A-Za-z0-9]/i.test(raw))
      throw Error('cloudflare_query_response_contains_secret_pattern');
    try{return JSON.parse(raw)}catch{throw Error('cloudflare_query_invalid_json')}
  }
  // The two requests are deterministic and serial; no retries or dispatch.
  const events=await one(planned.events_request);
  const sampling=await one(planned.sampling_request);
  return {
    schema:API_SCHEMA,
    utc_day:utcDay,
    worker:OBSERVER_NAME,
    // Explicit independent dashboard/version input, NOT inferred from rows.
    deployment_id:deploymentId,
    events_query:{request:planned.events_request,response:events},
    sampling_query:{request:planned.sampling_request,response:sampling},
  };
}

export function persistObserverEvidence(evidence,outputPath){
  const full=allowedOutput(outputPath);
  // Never overwrite a prior original. 0600 prevents casual other-user reads.
  // Caller must secure the parent directory separately.
  const bytes=Buffer.from(JSON.stringify(evidence,null,2)+'\n','utf8');
  if(bytes.length>2*MAX_RESPONSE_BYTES+100000)
    throw Error('cloudflare_export_artifact_oversize');
  try{
    writeFileSync(full,bytes,{flag:'wx',mode:0o600});
  }catch{throw Error('cloudflare_export_output_not_created')}
  const audit=auditTelemetryApiPages(evidence);
  return {
    schema:'BOAT_EDGE_CLOUDFLARE_OWNER_EXPORT_RECEIPT_V1',
    source:'owner_executed_cloudflare_api_query_unverified_by_independent_auditor',
    utc_day:evidence.utc_day,
    input_sha256:createHash('sha256').update(bytes).digest('hex'),
    bytes:bytes.length,
    local_consistency_pass:audit.observer_day_pass,
    local_issue_count:audit.api_issue_count??audit.raw_issue_count??audit.issue_count??0,
    independently_authenticated_origin:false,
    cloudflare_deployment_independently_proven:false,
    github_dispatch_or_recovery_proven:false,
    formal_t_minus_12_proven:false,
  };
}

const invoked=process.argv[1] && resolve(process.argv[1])===fileURLToPath(import.meta.url);
if(invoked){
  // No implicit live mode. Never read credentials unless --execute is
  // explicitly supplied. Output must be absolute and outside the repo.
  if(process.argv.length!==6||process.argv[2]!=='--execute'){
    console.error('usage: node scripts/collect_cloudflare_observer_telemetry.mjs --execute YYYY-MM-DD DEPLOYMENT_VERSION_ID /absolute/private/evidence.json');
    process.exitCode=2;
  }else{
    try{
      const [utcDay,deploymentId,out]=process.argv.slice(3);
      allowedOutput(out);
      const evidence=await collectObserverTelemetry({
        utcDay,deploymentId,
        accountId:process.env.CLOUDFLARE_ACCOUNT_ID,
        token:process.env.CLOUDFLARE_OBSERVABILITY_TOKEN,
      });
      const receipt=persistObserverEvidence(evidence,out);
      console.log(JSON.stringify(receipt,null,2));
      if(!receipt.local_consistency_pass)process.exitCode=1;
    }catch(error){
      // Deliberately never include user input, headers, token, raw API body,
      // account ID or file paths in errors.
      const allowed=new Set([
        'invalid_utc_day','invalid_cloudflare_account_id',
        'cloudflare_observability_token_required','observer_deployment_id_required',
        'output_must_be_absolute_path','output_inside_source_checkout_disallowed',
        'utc_day_not_complete_or_ingestion_grace','cloudflare_export_output_not_created',
        'cloudflare_export_artifact_oversize','cloudflare_query_non_200',
        'cloudflare_query_network_or_timeout_failure',
        'cloudflare_query_body_unreadable','cloudflare_query_response_oversize',
        'cloudflare_query_response_contains_secret_pattern','cloudflare_query_invalid_json',
      ]);
      const name=error instanceof Error && allowed.has(error.message)
        ?error.message:'invalid_request_or_io';
      console.error('CLOUDFLARE_OBSERVER_EXPORT_NOT_COMPLETED='+name);
      process.exitCode=2;
    }
  }
}
