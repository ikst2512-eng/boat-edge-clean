// Strict OFFLINE bridge from Cloudflare Workers Observability event records into
// the existing 192-tick CPU/Cron audit. No API, filesystem, or dispatch code.
// Based on official Workers Logs telemetry fields: $metadata.requestId/type,
// $workers.cpuTimeMs/outcome/scriptName/scriptVersion and timestamp.
// It must fail closed on unknown versions, missing CPU, duplicate records,
// missing invocation/custom log, partial/paginated export, and sampled exports.
// THIS IS NOT proof that operator-supplied JSON is authentic Cloudflare data.
import {auditObserverTelemetry, AUDIT_SCHEMA, OBSERVER_NAME} from './audit_observer_telemetry.mjs';
import {ALLOWED_CRON} from './independent_capture_slots.mjs';

export const RAW_LOG_SCHEMA='BOAT_EDGE_CLOUDFLARE_RAW_WORKERS_LOGS_V1';
const isObj = v => v !== null && typeof v === 'object' && !Array.isArray(v);
const validId = v => typeof v === 'string' && /^[a-zA-Z0-9_.:-]{6,128}$/.test(v);

function reportFromCustomRecord(record) {
  const meta=record?.$metadata;
  const message = typeof meta?.message === 'string' ? meta.message
    : typeof record?.source === 'string' ? record.source
    : typeof record?.source?.message === 'string' ? record.source.message : null;
  const prefix='CLOUDFLARE_CAPTURE_OBSERVER_ONLY=';
  if (!message || !message.startsWith(prefix)) return null;
  try {
    const output=JSON.parse(message.slice(prefix.length));
    return isObj(output) ? output : null;
  } catch { return null; }
}

function parseJstDate(value) {
  if(typeof value!=='string' || !/^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d(?:\.\d{1,3})?\+09:00$/.test(value)) return null;
  const ms=Date.parse(value);
  return Number.isFinite(ms) ? ms : null;
}

export function auditRawWorkersLogs(input) {
  if (!isObj(input)) throw new Error('invalid_raw_log_input');
  const issues=[];
  const add = issue => { if(issues.length<30) issues.push(issue); };
  if(input.schema!==RAW_LOG_SCHEMA) add('raw_schema_mismatch');
  if(input.worker!==OBSERVER_NAME) add('raw_worker_mismatch');
  if(!validId(input.deployment_id)) add('raw_deployment_id_missing');
  if(input.complete_export!==true) add('raw_export_not_complete');
  if(input.all_pages_fetched!==true) add('raw_pagination_not_complete');
  if(input.sample_interval!==1) add('raw_sampling_not_exact');
  if(!Number.isSafeInteger(input.total_matched_events) || input.total_matched_events<0) add('raw_total_count_missing');
  if(!Array.isArray(input.records)) add('raw_records_missing');
  const records=Array.isArray(input.records)?input.records:[];
  if(input.total_matched_events!==records.length) add('raw_total_count_mismatch');
  if(records.length>2000) add('raw_unexpected_volume');

  const groups=new Map();
  for(const [i, row] of records.entries()){
    const prefix='record['+i+']';
    if(!isObj(row) || !isObj(row.$metadata) || !isObj(row.$workers)){
      add(prefix+':missing_cloudflare_metadata');continue;
    }
    const meta=row.$metadata,worker=row.$workers,reqId=meta.requestId;
    if(!validId(reqId)){add(prefix+':invalid_request_id');continue;}
    if(meta.service!==OBSERVER_NAME || worker.scriptName!==OBSERVER_NAME){
      add(prefix+':wrong_worker_identity');continue;
    }
    if(worker.truncated===true || row.$cloudflare?.truncated===true) add(prefix+':truncated_log');
    if(!Number.isSafeInteger(row.timestamp) || row.timestamp<0) add(prefix+':invalid_timestamp');
    if(!groups.has(reqId))groups.set(reqId,{invocations:[],custom:[]});
    const g=groups.get(reqId);
    if(meta.type==='cf-worker-event'){
      g.invocations.push(row);
    }else if(meta.type==='cf-worker-log'){
      g.custom.push(row);
    }else add(prefix+':unexpected_cloudflare_record_type');
  }
  const normalized=[];
  for(const [id,group] of groups){
    if(group.invocations.length!==1 || group.custom.length!==1){
      add('request_record_cardinality_invalid');continue;
    }
    const event=group.invocations[0],custom=group.custom[0],e=event.$workers,c=custom.$workers;
    const version=e.scriptVersion?.id;
    if(version!==input.deployment_id){add('invocation_version_mismatch');continue;}
    if(c.scriptVersion?.id && c.scriptVersion.id!==version){add('custom_version_mismatch');continue;}
    if(!['scheduled','cron'].includes(e.eventType)){add('not_a_cron_invocation');continue;}
    // Official invocation logs describe Cron events by their cron expression;
    // some telemetry formats also place it under $workers.event.cron.
    const cron = typeof e.event?.cron==='string' ? e.event.cron : event.$metadata.message;
    if(cron!==ALLOWED_CRON){add('cron_not_from_invocation_metadata');continue;}
    const report=reportFromCustomRecord(custom);
    if(!report){add('missing_or_malformed_observer_console_log');continue;}
    if(typeof report.checked_at_jst!=='string' || typeof report.scheduled_at_jst!=='string'){
      add('missing_observer_clock_fields');continue;
    }
    const scheduled=parseJstDate(report.scheduled_at_jst),observed=parseJstDate(report.checked_at_jst);
    if(scheduled===null || observed===null){add('invalid_observer_clock_fields');continue;}
    if(!Number.isSafeInteger(event.timestamp) || !Number.isSafeInteger(custom.timestamp) ||
       Math.abs(custom.timestamp-observed)>10000 || event.timestamp<scheduled ||
       event.timestamp>observed+15000){
      add('cloudflare_event_clock_mismatch');continue;
    }
    normalized.push({
      request_id:id,cron,
      scheduled_at_utc:new Date(scheduled).toISOString(),
      observed_at_utc:new Date(observed).toISOString(),
      cpu_time_ms:e.cpuTimeMs,outcome:e.outcome,
      custom_report:report,
    });
  }
  const day=auditObserverTelemetry({
    schema:AUDIT_SCHEMA, worker:input.worker, deployment_id:input.deployment_id,
    utc_day:input.utc_day, source:'cloudflare_workers_invocation_and_custom_logs',
    complete_export:input.complete_export===true && input.all_pages_fetched===true &&
      input.sample_interval===1 && input.total_matched_events===records.length,
    samples:normalized,
  });
  return {
    ...day,
    raw_schema:RAW_LOG_SCHEMA,
    supplied_raw_records:records.length,
    correlated_invocations:normalized.length,
    raw_issues:issues,
    raw_issue_count:issues.length,
    observer_day_pass:day.observer_day_pass && issues.length===0,
    original_cloudflare_log_authenticity_independently_proven:false,
    actual_github_dispatch_proven:false,
    immutable_forecast_first_add_proven:false,
    formal_t_minus_12_proven:false,
  };
}
