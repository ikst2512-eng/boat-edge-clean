// RESEARCH-ONLY static contract audit for native GitHub capture publication.
// Never import into deployed recovery or observer Workers. No network, secrets,
// Git mutation, YAML interpreter, shell interpreter, or remote proof.
// These are conservative source patterns, not evidence of execution.
export const RECEIPT_SCHEMA = 'BOAT_EDGE_NATIVE_PUBLISHER_REMOTE_RECEIPT_LAB_V1';

const PUSH = /^[ \t]*if git push origin HEAD:main; then[ \t]*(?:#.*)?$/m;
const SUCCESS_EXIT = /^[ \t]*exit 0[ \t]*(?:#.*)?$/m;
const REMOTE_FETCH = /^[ \t]*git fetch origin main[ \t]*(?:#.*)?$/gm;
const REMOTE_ANCESTRY = /^[ \t]*git merge-base --is-ancestor HEAD FETCH_HEAD[ \t]*(?:#.*)?$/gm;
// Real 4-mode source uses Python's subprocess.check_output([...]). A viable
// future CLEAN publisher may do the same. A naked "git rev-parse HEAD" or an
// echo of those words must NOT count as storing the commit identity.
const SHA_ASSIGN = /(?:^|\n)[ \t]*sha[ \t]*=[ \t]*subprocess\.check_output\([ \t\r\n]*\[[ \t\r\n]*["']git["'][ \t]*,[ \t]*["']rev-parse["'][ \t]*,[ \t]*["']HEAD["']/m;
const COMMIT_JSON_KEY = /["']commit_sha["'][ \t]*:[ \t]*sha\b/;
const JSON_WRITE = /\btarget\.write_text\([ \t\r\n]*json\.dumps\(/;
const TARGETS = Object.freeze({
  clean: /\btarget\s*=\s*Path\(\s*["']clean-capture-evidence\/publication\.json["']\s*\)/,
  four_mode: /\btarget\s*=\s*Path\(\s*["']four-mode-evidence\/publication\.json["']\s*\)/,
});

export function auditNativePublisherPostPush(workflowYaml, kind) {
  if (!Object.hasOwn(TARGETS, kind) || typeof workflowYaml !== 'string')
    throw new Error('invalid_native_publisher_source');

  // The markers must be actual statement lines rather than comments, quotes,
  // grep patterns, or copied prose. Ignore comment-only shell/Python lines.
  const source = workflowYaml.split('\n').filter(line=>!/^[ \t]*#/.test(line)).join('\n');
  const push=PUSH.exec(source);
  if (!push) throw new Error('native_publisher_push_block_missing');
  const remaining=source.slice(push.index+push[0].length);
  const end=SUCCESS_EXIT.exec(remaining);
  if(!end) throw new Error('native_publisher_push_success_exit_missing');
  // Conservative: inspect only the first successful push branch. It does NOT
  // prove whether nested shell conditions or heredoc Python actually execute.
  const block=remaining.slice(0,end.index);

  const fetch=[...block.matchAll(REMOTE_FETCH)];
  const ancestry=[...block.matchAll(REMOTE_ANCESTRY)];
  const ancestryAfterPush=fetch.some(f=>ancestry.some(a=>a.index>f.index));
  const shaCaptured=SHA_ASSIGN.test(block);
  const receiptPersisted=TARGETS[kind].test(block) && JSON_WRITE.test(block) && COMMIT_JSON_KEY.test(block);
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
    // Even all source checks passing cannot prove an actual remote first-add.
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
    schema:RECEIPT_SCHEMA, clean,four_mode,
    both_source_contracts_present:clean.source_level_receipt_contract_present &&
      four_mode.source_level_receipt_contract_present,
    live_evidence_available:false,
    cross_provider_recovery_release_approved:false,
  };
}
