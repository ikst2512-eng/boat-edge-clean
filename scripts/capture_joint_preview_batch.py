"""Bounded current-day official source pairs, isolated from all forecasts."""
import json
import os
import re
from datetime import datetime, timedelta
from pathlib import Path

from research_model import JST
from clean_schedule import clean_schedule
from scripts.capture_official_beforeinfo_json import capture as capture_before
from scripts.capture_official_odds_receipt import capture as capture_odds
from scripts.audit_joint_official_receipts import audit_pair
from scripts.joint_t12_decision import decision


def candidates(schedule, now):
    day = now.strftime('%Y%m%d')
    if schedule.get('ok') is not True or schedule.get('date') != day:
        raise ValueError('current schedule unavailable')
    found = {}
    for row in schedule.get('races', []):
        try:
            code = row['race_code']
            if not re.fullmatch(day+r'(0[1-9]|1[0-9]|2[0-4])(0[1-9]|1[0-2])', code):
                continue
            if row['venue_code'] != code[8:10] or row['race_no'] != int(code[10:]):
                continue
            close = datetime.fromisoformat(row['deadline_jst'])
            if close.utcoffset() != timedelta(hours=9) or close.strftime('%Y%m%d') != day:
                continue
            found.setdefault(code, set()).add(close)
        except (KeyError, TypeError, ValueError):
            continue
    # A schedule is discovery only: actual odds cutoff comes from official JSON.
    return [code for close,code in sorted((next(iter(times)),code) for code,times in found.items()
            if len(times)==1 and now+timedelta(minutes=12,seconds=40)<next(iter(times))<now+timedelta(hours=1))[:2]]


def collect(root, identifier, *, clock=None, schedule_fetch=None,
            before=None, odds=None, auditor=None, event=None):
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]{0,31}', identifier):
        raise ValueError('invalid observation identifier')
    clock = clock or (lambda: datetime.now(JST))
    now = clock()
    if now.utcoffset() != timedelta(hours=9):
        raise ValueError('JST clock required')
    root = Path(root)
    if root.is_symlink():
        raise ValueError('receipt root must not be a symlink')
    report_path = root/'batch_report.json'
    if report_path.exists():
        raise FileExistsError('batch report must not overwrite prior evidence')
    root.mkdir(parents=True,exist_ok=True)
    report = {'event': event or os.environ.get('GITHUB_EVENT_NAME') or 'local_manual',
              'checked_at_jst': now.isoformat(), 'date': now.strftime('%Y%m%d'),
              'formal': False, 'forecast_usable': False, 'full_t12_source_certified': False,
              'eligible_candidates': 0, 'beforeinfo_originals_saved': 0,
              'official_odds_originals_saved': 0, 'complete_pairs_before_t12': 0, 'observations': []}
    try:
        status, schedule = (schedule_fetch or clean_schedule)(report['date'])
        if status != 200:
            raise ValueError('schedule HTTP unavailable')
        codes = candidates(schedule, now)
        report['eligible_candidates'] = len(codes)
        for code in codes:
            item = {'race_code': code, 'status': 'unavailable', 'forecast_usable': False}
            report['observations'].append(item)
            try:
                before_id, odds_id = 'before_'+identifier, 'odds_'+identifier
                a = (before or capture_before)(code, root, before_id)
                item['beforeinfo'] = a
                if a.get('status') != 'official_json_observed_not_t12_certified':
                    item['status'] = 'beforeinfo_failed'
                    continue
                report['beforeinfo_originals_saved'] += 1
                # This deadline comes from race-matched archived official bytes.
                deadline = code[:4]+'-'+code[4:6]+'-'+code[6:8]+'T'+a['deadline_display']+':00+09:00'
                gate = decision(a['received_at_jst'], deadline, clock().isoformat())
                item['cutoff_gate'] = gate
                if gate['status'] != 'fetch_odds':
                    item['status'] = gate['status']
                    continue
                b = (odds or capture_odds)(code, deadline, root, odds_id)
                item['odds'] = b
                if b.get('status') != 'official_odds_observed_research_only':
                    item['status'] = 'odds_failed'
                    continue
                report['official_odds_originals_saved'] += 1
                result = (auditor or audit_pair)(
                    root/'observations'/before_id/code[:8]/code,
                    root/'observations'/odds_id/code[:8]/code)
                item['joint_audit'] = result
                item['status'] = 'pair_complete' if result.get('both_complete_before_t12') is True else 'pair_not_ready'
                report['complete_pairs_before_t12'] += item['status'] == 'pair_complete'
            except (OSError, ValueError, KeyError, TypeError, AttributeError) as exc:
                item.update(status='capture_or_audit_failed',error_type=type(exc).__name__)
        report['status'] = ('no_pre_t12_candidate' if not codes else
                            'source_capture_failed' if not report['beforeinfo_originals_saved'] else
                            'complete_pairs_observed' if report['complete_pairs_before_t12'] else
                            'sources_saved_pair_not_ready')
    except (OSError, ValueError, KeyError, TypeError, AttributeError) as exc:
        report.update(status='source_capture_failed',error_type=type(exc).__name__)
    with report_path.open('x',encoding='utf-8') as out:
        json.dump(report,out,ensure_ascii=False,indent=2)
    return report


if __name__ == '__main__':
    identifier = 'run'+os.environ['GITHUB_RUN_ID'] if os.environ.get('GITHUB_RUN_ID') else datetime.now(JST).strftime('local_%Y%m%d_%H%M%S_%f')
    report = collect('official_joint_evidence',identifier)
    print('OFFICIAL_JOINT_BATCH '+json.dumps(report,ensure_ascii=False),flush=True)
    if os.environ.get('GITHUB_STEP_SUMMARY'):
        with open(os.environ['GITHUB_STEP_SUMMARY'],'a') as out:
            out.write('\n### Official raw preview/odds pairs (research only)\n'+
                      f"Status: {report['status']}; eligible: {report['eligible_candidates']}; beforeinfo originals: {report['beforeinfo_originals_saved']}; odds originals: {report['official_odds_originals_saved']}; complete before T-12: {report['complete_pairs_before_t12']}.\n"+
                      'This does not certify racecard, final entry, forecasts or accuracy.\n')
    if report['status']=='source_capture_failed':
        raise SystemExit(1)
