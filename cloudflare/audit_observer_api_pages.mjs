// OFFLINE acceptance of operator-retained, real-API-shaped Cloudflare
// Workers Observability telemetry/query request+response pairs.
// No account/network authentication and no deployment or GitHub dispatch.
// V2 follows the documented POST body: top-level limit (max 2000), nested
// parameters.view and parameters.filters ARRAY, result.run and result.events.
// Older V1 pseudo-API envelopes are intentionally NOT accepted as V2.
import {auditRawWorkersLogs, RAW_LOG_SCHEMA} from './audit_observer_raw_logs.mjs';
import {OBSERVER_NAME} from './audit_observer_telemetry.mjs';

export const API_SCHEMA='BOAT_EDGE_CLOUDFLARE_TELEMETRY_API_SINGLE_PAGE_V2';
const DATASET='cloudflare-workers';
const isObj = x => x!==null && typeof x==='object' && !Array.isArray(x);
function canonical(value) {
  if(Array.isArray(value))return '['+value.map(canonical).join(',')+']';
  if(isObj(value))return '{'+Object.keys(value).sort()
    .map(k=>JSON.stringify(k)+':'+canonical(value[k])).join(',')+'}';
  return JSON.stringify(value);
}
function dayWindow(day) {
  if(typeof day!=='string'|| !/^\d{4}-\d\d-\d\d$/.test(day))throw Error('invalid_utc_day');
  const from=Date.parse(day+'T00:00:00.000Z');
  if(!Number.isFinite(from)||new Date(from).toISOString().slice(0,10)!==day)throw Error('invalid_utc_day');
  return {from,to:from+86_400_000};
}
const exactScope = p => isObj(p) && Array.isArray(p.datasets) &&
  p.datasets.length===1 && p.datasets[0]===DATASET &&
  Array.isArray(p.filters) && p.filters.length===1 &&
  isObj(p.filters[0]) &&
  Object.keys(p.filters[0]).every(k=>['kind','key','value','type','operation'].includes(k)) &&
  (p.filters[0].kind===undefined||p.filters[0].kind==='filter') &&
  p.filters[0].key==='$metadata.service' &&
  p.filters[0].value===OBSERVER_NAME &&
  p.filters[0].type==='string' && p.filters[0].operation==='eq' &&
  (p.filterCombination===undefined || p.filterCombination==='and') &&
  !('needle' in p) && !('groupBys' in p) && !('havings' in p);
const sameWindow = (x, w) => isObj(x) && x.from===w.from && x.to===w.to;
const presentId = id => typeof id==='string' && id.length>0;

// Emit exact, secret-free ad-hoc queries; operators must independently retain
// the real Cloudflare API responses. This code NEVER authenticates or fetches.
export function buildObserverTelemetryQueries(utcDay) {
  const timeframe=dayWindow(utcDay);
  const parameters=view=>({
    view, datasets:[DATASET],
    filters:[{kind:'filter',key:'$metadata.service',value:OBSERVER_NAME,
      type:'string',operation:'eq'}],
    ...(view==='calculations' ? {calculations:[{operator:'count'}]} : {}),
  });
  return {
    schema:'BOAT_EDGE_CLOUDFLARE_TELEMETRY_QUERY_REQUESTS_V1',
    utc_day:utcDay,
    events_request:{
      queryId:'boat-edge-observer-events-'+utcDay,
      timeframe:{...timeframe},limit:2000,parameters:parameters('events'),
    },
    sampling_request:{
      queryId:'boat-edge-observer-sampling-'+utcDay,
      timeframe:{...timeframe},chartType:'aggregate',
      parameters:parameters('calculations'),
    },
    authenticated_to_cloudflare:false,
    actually_executed:false,
    account_evidence_proven:false,
    recovery_approved:false,
  };
}
const exactCount = p => Array.isArray(p?.calculations) &&
  p.calculations.length===1 && p.calculations[0]?.operator==='count' &&
  p.calculations[0]?.key===undefined;
const unsampledQuery = statistics => statistics===undefined || statistics===null ||
  (isObj(statistics) && (statistics.abr_level===undefined ||
    statistics.abr_level===null || statistics.abr_level===1));

export function auditTelemetryApiPages(input) {
  if(!isObj(input))throw Error('invalid_telemetry_api_export');
  const w=dayWindow(input.utc_day),issues=[];
  const bad=x=>{if(issues.length<30)issues.push(x);};
  if(input.schema!==API_SCHEMA)bad('api_schema_invalid');
  if(input.worker!==OBSERVER_NAME)bad('api_worker_mismatch');
  if(!presentId(input.deployment_id))bad('deployment_id_missing');
  const e=input.events_query,s=input.sampling_query;
  const er=e?.request,cr=s?.request;
  const ep=er?.parameters,cp=cr?.parameters;
  if(!isObj(e)||!isObj(s)||!isObj(er)||!isObj(cr)||
     !isObj(ep)||!isObj(cp)||!isObj(e.response)||!isObj(s.response))
    bad('api_queries_missing_or_malformed');

  // Cloudflare's *top-level* limit allows up to 2000 event rows, so exactly
  // 384 events can be captured in one query. parameters.limit is a DIFFERENT
  // setting (max 100) and must not be used as the event page size.
  if(er?.limit!==2000||er?.offset!==undefined||er?.offsetBy!==undefined||
     er?.offsetDirection!==undefined||ep?.limit!==undefined)
    bad('api_event_limit_or_cursor_invalid');
  if(ep?.view!=='events'||cp?.view!=='calculations'||cp?.limit!==undefined)
    bad('api_view_or_parameter_limit_invalid');
  if(!sameWindow(er?.timeframe,w)||!sameWindow(cr?.timeframe,w))
    bad('api_request_window_invalid');
  if(!exactScope(ep)||!exactScope(cp))
    bad('api_observer_dataset_and_service_scope_invalid');
  if(!presentId(er?.queryId)||!presentId(cr?.queryId)||er.queryId===cr.queryId)
    bad('api_query_identity_invalid');
  if(ep?.calculations!==undefined||!exactCount(cp))
    bad('api_aggregate_request_invalid');
  // Reject comparison queries and dry results even when a correct-looking
  // 384-row envelope was attached. These are not the unmodified raw-day pair.
  if(er?.compare===true||cr?.compare===true||er?.dry===true||cr?.dry===true)
    bad('api_request_compare_or_dry_not_allowed');

  const ee=e?.response,ss=s?.response;
  if(ee?.success!==true||ss?.success!==true||
     !Array.isArray(ee?.errors)||ee.errors.length!==0||
     !Array.isArray(ss?.errors)||ss.errors.length!==0)
    bad('api_response_not_successful');
  const eres=ee?.result,sres=ss?.result;
  const eRun=eres?.run,sRun=sres?.run;
  if(eRun?.status!=='COMPLETED'||sRun?.status!=='COMPLETED'||
     !sameWindow(eRun?.timeframe,w)||!sameWindow(sRun?.timeframe,w))
    bad('api_run_incomplete_or_wrong_window');
  if(eRun?.dry===true||sRun?.dry===true)
    bad('api_result_dry_run_not_accepted');
  // ABR query sampling is different from head-sampling during ingestion.
  // Cloudflare documents abr_level=1 if absent; any non-1 present value
  // means the query's sample population is not a complete source of proof.
  if(!unsampledQuery(eres?.statistics)||!unsampledQuery(sres?.statistics)||
     !unsampledQuery(eRun?.statistics)||!unsampledQuery(sRun?.statistics))
    bad('api_adaptive_query_sampling_not_exact');
  if(!presentId(eRun?.accountId)||eRun.accountId!==sRun?.accountId||
     !presentId(eRun?.id)||!presentId(sRun?.id)||eRun.id===sRun.id)
    bad('api_run_identity_or_account_mismatch');
  // The run's server-echoed *effective* query must still be scoped to the
  // Observer. Validating only the sent request would miss a saved queryId or
  // changed effective parameters that actually queried another dataset.
  const erp=eRun?.query?.parameters,srp=sRun?.query?.parameters;
  if(!exactScope(erp)||!exactScope(srp)||erp?.view!=='events'||
     srp?.view!=='calculations'||canonical(erp?.filters)!==canonical(ep?.filters)||
     canonical(srp?.filters)!==canonical(cp?.filters))
    bad('api_effective_query_scope_or_view_mismatch');
  // An in-scope query can still compute something other than the requested
  // count. Its server-echoed effective calculation must itself be COUNT.
  if(!exactCount(srp)||erp?.calculations!==undefined)
    bad('api_effective_aggregate_not_count');
  const ev=eres?.events;
  if(!Array.isArray(ev?.events)||ev.count!==384||ev.events.length!==384)
    bad('api_count_not_exactly_384');
  const rows=Array.isArray(ev?.events)?ev.events:[];
  if(rows.some(row=>!isObj(row)||row.dataset!==DATASET))
    bad('api_event_dataset_mismatch');
  const all=sres?.calculations;
  const aggregates=Array.isArray(all)&&all.length===1?all[0]?.aggregates:null;
  if(!Array.isArray(aggregates)||aggregates.length!==1||
     aggregates[0]?.count!==384||aggregates[0]?.sampleInterval!==1)
    bad('api_sampling_not_proven_exact');

  if(issues.length)return {
    schema:'BOAT_EDGE_CLOUDFLARE_TELEMETRY_API_AUDIT_RESULT_V2',
    utc_day:input.utc_day,api_query_structure_pass:false,observer_day_pass:false,
    api_issue_count:issues.length,api_issues:issues,
    actual_cloudflare_api_authenticity_independently_proven:false,
    actual_github_dispatch_proven:false,immutable_forecast_first_add_proven:false,
    formal_t_minus_12_proven:false,
  };
  const raw=auditRawWorkersLogs({
    schema:RAW_LOG_SCHEMA,utc_day:input.utc_day,worker:input.worker,
    deployment_id:input.deployment_id,complete_export:true,all_pages_fetched:true,
    sample_interval:1,total_matched_events:384,records:rows,
  });
  return {...raw,api_schema:API_SCHEMA,api_query_structure_pass:true,
    api_issue_count:0,api_issues:[],
    actual_cloudflare_api_authenticity_independently_proven:false,
    actual_github_dispatch_proven:false,immutable_forecast_first_add_proven:false,
    formal_t_minus_12_proven:false};
}
