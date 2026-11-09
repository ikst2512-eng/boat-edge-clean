// OFFLINE audit of actual-shaped Cloudflare Telemetry API query responses.
// Does not make HTTP requests or authenticate Cloudflare-origin bytes.
// To avoid unverifiable cursor pagination, require a single complete events
// result (limit 2000, expected exactly 384 records) plus independent
// calculations showing sampleInterval === 1 for the same filter/timeframe.
// The normalized exporter in audit_observer_raw_logs never trusts operator-
// asserted complete_export or sample_interval when this bridge is used.
import {auditRawWorkersLogs, RAW_LOG_SCHEMA} from './audit_observer_raw_logs.mjs';
import {OBSERVER_NAME} from './audit_observer_telemetry.mjs';

export const API_SCHEMA='BOAT_EDGE_CLOUDFLARE_TELEMETRY_API_SINGLE_PAGE_V1';
const isObj = x => x && typeof x === 'object' && !Array.isArray(x);

function canonical(value) {
  if (Array.isArray(value)) return '['+value.map(canonical).join(',')+']';
  if (isObj(value)) return '{'+Object.keys(value).sort()
    .map(key=>JSON.stringify(key)+':'+canonical(value[key])).join(',')+'}';
  return JSON.stringify(value);
}

function dayWindow(day) {
  if(typeof day!=='string'|| !/^\d{4}-\d\d-\d\d$/.test(day)) throw Error('invalid_utc_day');
  const from=Date.parse(day+'T00:00:00.000Z');
  if(!Number.isFinite(from)||new Date(from).toISOString().slice(0,10)!==day)throw Error('invalid_utc_day');
  return {from,to:from+86_400_000};
}

// Returns a bounded FAIL result if API metadata is inconsistent, not an
// invented successful 192-tick audit. Only a fully verified envelope is
// passed to the existing CPU/clock/requestId raw event correlation.
export function auditTelemetryApiPages(input) {
  if(!isObj(input)) throw Error('invalid_telemetry_api_export');
  const {from,to}=dayWindow(input.utc_day);
  const issues=[];
  const bad = code => { if(issues.length<25)issues.push(code); };
  if(input.schema!==API_SCHEMA)bad('api_schema_invalid');
  if(input.worker!==OBSERVER_NAME)bad('api_worker_mismatch');
  if(typeof input.deployment_id!=='string'||!input.deployment_id)bad('deployment_id_missing');
  const e=input.events_query, s=input.sampling_query;
  if(!isObj(e)||!isObj(s)||!isObj(e.request)||!isObj(s.request)||
     !isObj(e.response)||!isObj(s.response))bad('api_queries_missing_or_malformed');

  const evt=e?.response?.events;
  const eventRows=evt?.events;
  const metadata=e?.request, calc=s?.request;
  const sameWindow = q => isObj(q?.timeframe)&&q.timeframe.from===from&&q.timeframe.to===to;
  if(!sameWindow(metadata)||!sameWindow(calc) ||
     !sameWindow(e?.response)||!sameWindow(s?.response))bad('api_window_not_complete_utc_day');
  if(metadata?.view!=='events'||metadata?.limit!==2000 ||
     (metadata.offset!==undefined && metadata.offset!==null && metadata.offset!==''))
      bad('api_event_view_limit_or_cursor_invalid');
  if(calc?.view!=='calculations')bad('api_sample_view_invalid');
  // Both real request JSONs must be retained. A caller cannot use an
  // unfiltered sampling query to attest a narrowly filtered event query.
  if(!isObj(metadata?.filters)||!isObj(calc?.filters) ||
     canonical(metadata.filters)!==canonical(calc.filters))bad('api_filter_provenance_mismatch');
  // Equal filters are not necessarily the RIGHT filters. The former equality
  // check would accept two equally unscoped queries, allowing a sampled
  // calculation for a different Worker to stand in for this Observer.
  // Require one explicit exact-service leaf; any group/OR/extra predicates
  // require separate review rather than silently changing the audit scope.
  const exactObserverFilter = f => isObj(f) &&
    Object.keys(f).every(k=>['kind','key','value','type','operation'].includes(k)) &&
    Object.keys(f).length===5 &&
    f.kind==='filter' && f.key==='$metadata.service' &&
    f.value===OBSERVER_NAME && f.type==='string' && f.operation==='eq';
  if(!exactObserverFilter(metadata?.filters)||!exactObserverFilter(calc?.filters))
    bad('api_observer_service_scope_not_proven');
  if(e?.response?.status!=='COMPLETED'||s?.response?.status!=='COMPLETED')
      bad('api_query_not_completed');
  if(!Array.isArray(eventRows)||evt?.count!==384||eventRows?.length!==384)
      bad('api_count_not_exactly_384');
  const aggreg=s?.response?.calculations;
  // We explicitly require exactly one aggregate for the identically
  // scoped query: do not select a convenient '1' from multiple groups.
  const aggregates=Array.isArray(aggreg)&&aggreg.length===1?aggreg[0]?.aggregates:null;
  if(!Array.isArray(aggregates)||aggregates.length!==1||
     aggregates[0]?.sampleInterval!==1||
     aggregates[0]?.count!==384)bad('api_sampling_not_proven_exact');
  if(issues.length) return {
    schema:'BOAT_EDGE_CLOUDFLARE_TELEMETRY_API_AUDIT_RESULT_V1',
    utc_day:input.utc_day, api_query_structure_pass:false,
    observer_day_pass:false, api_issue_count:issues.length, api_issues:issues,
    actual_cloudflare_api_authenticity_independently_proven:false,
    actual_github_dispatch_proven:false, immutable_forecast_first_add_proven:false,
    formal_t_minus_12_proven:false
  };
  const raw=auditRawWorkersLogs({
    schema:RAW_LOG_SCHEMA,utc_day:input.utc_day,worker:input.worker,
    deployment_id:input.deployment_id,complete_export:true,all_pages_fetched:true,
    sample_interval:1,total_matched_events:384,records:eventRows,
  });
  return {
    ...raw,api_schema:API_SCHEMA,api_query_structure_pass:true,
    api_issue_count:0,api_issues:[],
    actual_cloudflare_api_authenticity_independently_proven:false,
    actual_github_dispatch_proven:false,
    immutable_forecast_first_add_proven:false,
    formal_t_minus_12_proven:false
  };
}
