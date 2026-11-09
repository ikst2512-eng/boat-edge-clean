// RESEARCH-ONLY static contract audit for native GitHub capture publication.
// No external network, secrets, git mutation, YAML parsing/execution, or
// production importer. This checks only whether source contains post-push
// remote ancestry evidence. It cannot prove actual publication or T-12.
export const RECEIPT_SCHEMA = 'BOAT_EDGE_NATIVE_PUBLISHER_REMOTE_RECEIPT_LAB_V1';

export function auditNativePublisherPostPush(workflowYaml, kind) {
  if (!['clean','four_mode'].includes(kind) || typeof workflowYaml !== 'string')
    throw new Error('invalid_native_publisher_source');
  const marker='if git push origin HEAD:main; then';
  const start=workflowYaml.indexOf(marker);
  if(start<0) throw new Error('native_publisher_push_block_missing');
  const tail=workflowYaml.slice(start+marker.length);
  const end=tail.search(/\bexit 0\b/);
  if(end<0) throw new Error('native_publisher_push_success_exit_missing');
  // Only the actual SUCCESS branch between push and return counts.
  // A check BEFORE the push, or after its success exit, proves nothing.
  const block=tail.slice(0,end);
  const fetch=block.indexOf('git fetch origin main');
  const ancestry=block.indexOf('git merge-base --is-ancestor HEAD FETCH_HEAD');
  const ancestryAfterPush=fetch>=0 && ancestry>fetch;
  const shaCaptured=block.includes('"rev-parse", "HEAD"') || block.includes('git rev-parse HEAD');
  const receiptPersisted=kind==='four_mode'
    ? block.includes('four-mode-evidence/publication.json') && block.includes('"commit_sha"')
    : block.includes('clean-capture-evidence/publication.json') && block.includes('"commit_sha"');
  const missing=[];
  if(!ancestryAfterPush)missing.push('remote_main_ancestry_after_push_not_checked');
  if(!shaCaptured)missing.push('exact_published_commit_sha_not_recorded_in_success_path');
  if(!receiptPersisted)missing.push('published_commit_receipt_artifact_not_found');
  return {
    schema:RECEIPT_SCHEMA,
    publisher:kind,
    source_contains_main_push:true,
    post_push_remote_main_ancestry_check:ancestryAfterPush,
    exact_published_commit_sha_captured:shaCaptured,
    publication_receipt_artifact_emitted:receiptPersisted,
    source_level_receipt_contract_present:missing.length===0,
    missing_contracts:missing,
    // Source inspection alone never proves the remote HEAD or source cutoff.
    remote_publication_independently_observed:false,
    publication_immutable_first_add_proven:false,
    formal_t_minus_12_proven:false,
    cross_provider_recovery_release_approved:false,
  };
}

export function auditNativePublisherPair(cleanYaml,fourModeYaml) {
  const clean=auditNativePublisherPostPush(cleanYaml,'clean');
  const four_mode=auditNativePublisherPostPush(fourModeYaml,'four_mode');
  return {
    schema:RECEIPT_SCHEMA,
    clean,four_mode,
    both_source_contracts_present:clean.source_level_receipt_contract_present &&
      four_mode.source_level_receipt_contract_present,
    live_evidence_available:false,
    cross_provider_recovery_release_approved:false,
  };
}
