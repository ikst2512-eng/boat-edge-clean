"""Independent pre-cutoff prospective prediction capture.

This is *not* a validated formal forecast: publication, remote Git first-add
attestation and out-of-sample accuracy promotion are separate gates.
Never uses old boat-edge or post-result snapshots.
"""
import argparse
import hashlib
import json
import os
import sys
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path
from research_model import JST, BASE, read_rows, probabilities, model_provenance

ROOT = Path(__file__).resolve().parent
STORE = ROOT / "prospective_predictions"
VERSION = "clean-prospective-national-beta0.4-v1"

def build(day, titles, cards, title_received, cards_received, title_digest, card_digest, now, provenance):
    counts = Counter(r.get("レースコード") for r in titles if isinstance(r, dict))
    card_counts = Counter(r.get("レースコード") for r in cards if isinstance(r, dict))
    by_card = {r["レースコード"]: r for r in cards if isinstance(r, dict) and card_counts[r.get("レースコード")] == 1 and r.get("レースコード")}
    items = {}
    for row in titles:
        code = row.get("レースコード") if isinstance(row, dict) else None
        if not isinstance(code, str) or len(code) != 12 or not code.isascii() or not code.isdigit() or not code.startswith(day):
            continue
        if counts[code] != 1 or card_counts[code] != 1 or code not in by_card:
            continue
        try:
            deadline = datetime.strptime(day + row["電話投票締切予定"], "%Y%m%d%H:%M").replace(tzinfo=JST)
            cutoff = deadline - timedelta(minutes=12)
            if max(now, title_received, cards_received) >= cutoff:
                continue
            rates = [float(by_card[code][f"艇{i}_全国勝率"]) for i in range(1,7)]
            # Per-race direct cards each have distinct raw HTTP bytes. Daily
            # CSV and OpenAPI retain their existing one-digest-per-file format.
            card_sha = card_digest[code] if isinstance(card_digest, dict) else card_digest
            outcomes = probabilities(rates)
            tickets = ["-".join(map(str, p)) for p, _ in outcomes[:10]]
            items[code] = {
                "race_code":code, "status":"prospective_candidate",
                "formal":False, "validated":False, "scoring":False,
                "predictions":tickets, "model_version":VERSION,
                "generated_at":now.isoformat(), "source_deadline_jst":deadline.isoformat(),
                "cutoff_jst":cutoff.isoformat(), "source_title_received_jst":title_received.isoformat(),
                "source_cards_received_jst":cards_received.isoformat(),
                "source_title_sha256":title_digest, "source_cards_sha256":card_sha,
                "input_sha256":hashlib.sha256((title_digest+":"+card_sha).encode()).hexdigest(),
                "national_win_rates":rates, **provenance,
                "attestation":"pending Git remote first-add verification",
            }
        except (ValueError, KeyError, TypeError, OverflowError):
            continue
    return items

def finalize_records(output, title_received, cards_received, completed):
    """Mark actual post-calculation time; drop any item that crossed T-12."""
    if any(t.tzinfo is None for t in (title_received,cards_received,completed)):
        raise ValueError("timezone-aware capture timestamps required")
    return {code:{**record,"generated_at":completed.isoformat()}
            for code,record in output.items()
            if max(title_received,cards_received)<=completed
            and completed<datetime.fromisoformat(record["cutoff_jst"])}

def supplement_unlisted(day, titles, cards, existing_output, provenance, limit=12):
    """Add only separately received direct-source pairs for races absent in both daily files.

    No CSV/OpenAPI row is ever combined with a direct-source row. A failed
    optional supplement must not discard already valid daily candidates.
    """
    from clean_direct_sources import holding_rows, direct_cards
    title_counts=Counter(r.get("レースコード") for r in titles if isinstance(r,dict))
    card_counts=Counter(r.get("レースコード") for r in cards if isinstance(r,dict))
    # Even a malformed matched pair remains owned by its primary source:
    # never silently replace it with another vendor's values.
    # A partially malformed or duplicated primary entry must not be
    # silently repaired by a different source. Only genuinely absent pairs
    # are eligible for independent direct supplementation.
    complete={code for code in title_counts if card_counts.get(code)}
    blocked={code for code,n in title_counts.items() if n>1}
    blocked.update(code for code,n in card_counts.items() if n>1)
    primary_titles={r["レースコード"]:r for r in titles
                    if isinstance(r,dict) and r.get("レースコード")
                    and title_counts[r["レースコード"]]==1}
    frozen={p.stem for p in STORE.glob(day+"????.json")}
    try:
        holding,t1,h1=holding_rows(day)
    except (OSError,TimeoutError,ValueError,UnicodeError) as exc:
        print("PROSPECTIVE_SUPPLEMENT_UNAVAILABLE "+json.dumps({
            "day":day,"error_type":type(exc).__name__,
            "daily_candidates_retained":len(existing_output)
        },sort_keys=True),file=sys.stderr)
        if not existing_output and not (
                isinstance(exc, ValueError) and str(exc) == "no_upcoming_schedule"):
            # Source outage cannot be a healthy zero-candidate capture.
            raise ValueError("supplement_holding_source_unavailable") from exc
        return {}
    extra=[]
    conflicts=0
    for row in holding:
        code=row.get("レースコード") if isinstance(row,dict) else None
        if (not isinstance(code,str) or code in complete or code in blocked
                or code in frozen or code in existing_output):
            continue
        known=primary_titles.get(code)
        if known and known.get("電話投票締切予定")!=row.get("電話投票締切予定"):
            conflicts+=1
            continue
        extra.append(row)
    if not extra:
        return {}
    try:
        extra_cards,t2,_,card_hashes,failed=direct_cards(
            day,extra,existing_codes=frozen|set(existing_output),limit=limit)
    except (OSError,TimeoutError,ValueError,UnicodeError) as exc:
        print("PROSPECTIVE_SUPPLEMENT_UNAVAILABLE "+json.dumps({
            "day":day,"error_type":type(exc).__name__,
            "daily_candidates_retained":len(existing_output)
        },sort_keys=True),file=sys.stderr)
        if not existing_output:
            # An exception is not an empty, fully checked card list.
            raise ValueError("supplement_direct_cards_unavailable") from exc
        return {}
    # If the partial primary files yielded no valid candidate, then failed
    # attempted direct-card requests are an upstream failure, not a legitimate
    # empty eligible set. Preserve primary candidates when any survived.
    if not extra_cards and failed and not existing_output:
        raise ValueError("supplement_all_card_fetches_failed")
    later=build(day,extra,extra_cards,t1,t2,h1,card_hashes,
                datetime.now(JST),{**provenance,
                   "input_source_kind":"direct_race_specific_pre_race"})
    final=finalize_records(later,t1,t2,datetime.now(JST))
    if set(final)&set(existing_output):
        raise ValueError("source pair overlap prohibited")
    print("PROSPECTIVE_SUPPLEMENT "+json.dumps({
        "day":day,"unlisted_titles":len(extra),"direct_cards":len(extra_cards),
        "eligible":len(final),"deadline_conflicts_rejected":conflicts,
        "fetch_error_counts":failed,"formal":False
    },sort_keys=True),file=sys.stderr)
    return final


def collect(day=None):
    now = datetime.now(JST)
    day = day or now.strftime("%Y%m%d")
    datetime.strptime(day, "%Y%m%d")
    path=f"{day[:4]}/{day[4:6]}/{day[6:]}.csv"
    try:
        titles,t1,h1=read_rows(BASE+"title/"+path)
        cards,t2,h2=read_rows(BASE+"race_cards/"+path)
        # Both files can be nonempty yet contain disjoint race sets while
        # the publisher is updating the day's archives. Never mix their rows
        # or silently report zero saved forecasts in that case.
        title_codes={row.get("レースコード") for row in titles if isinstance(row,dict)}
        card_codes={row.get("レースコード") for row in cards if isinstance(row,dict)}
        if not titles or not cards or not (title_codes & card_codes):
            raise OSError("incomplete daily pre-race CSV coverage")
        source_kind="public_pre_race_csv"
    except (OSError, TimeoutError, ValueError) as exc:
        if isinstance(exc,ValueError) and str(exc)!="source unavailable":
            raise
        # Fail over only to the existing strictly pre-race day source.
        # A missing or malformed alternate source is a failed capture, never a
        # result-derived forecast or a fabricated successful candidate.
        from clean_openapi_sources import load
        try:
            titles,cards,received,digest,source=load(day)
            t1=t2=received
            h1=h2=digest
            source_kind=source["source"]
        except (OSError, TimeoutError, ValueError) as alternate_error:
            # Never bypass a malformed secondary source: only a documented
            # unavailable/empty-day response may try the bounded direct feed.
            if (isinstance(alternate_error, ValueError)
                    and str(alternate_error) not in ("no_valid_races", "source unavailable")):
                raise
            from clean_direct_sources import holding_rows, direct_cards
            try:
                titles,t1,h1=holding_rows(day)
                already_saved={p.stem for p in STORE.glob(day+"????.json")}
                cards,t2,_,card_shas,card_failures=direct_cards(
                    day,titles,existing_codes=already_saved,limit=18)
                # A complete/no-op run is distinct from an upstream outage.
                # Already-frozen and past-cutoff races produce no eligible
                # card request; do not make subsequent scheduled runs red.
                # Failed attempted card fetches still fail closed.
                if not cards and card_failures:
                    raise ValueError("direct_pre_race_cards_unavailable")
                h2=card_shas
                source_kind="direct_race_specific_pre_race"
            except (OSError, TimeoutError, ValueError, UnicodeError) as direct_error:
                raise ValueError("all_pre_race_sources_unavailable") from direct_error
    provenance={**model_provenance(),"input_source_kind":source_kind}
    # A prospective forecast cannot predate its own input receipts. The first
    # timestamp above is only the capture-run start, not generation evidence.
    started_generation=datetime.now(JST)
    output=build(day,titles,cards,t1,t2,h1,h2,started_generation,provenance)
    # This timestamp is after all model calculations; do not backdate a frozen
    # record to the beginning of a fetch or a long-running batch.
    completed_generation=datetime.now(JST)
    output=finalize_records(output,t1,t2,completed_generation)
    # A daily publication can include one valid race while omitting many
    # upcoming cards. A missing pair gets an entirely independent direct
    # holding-list + six-racer card receipt, never mixed-source fields.
    if source_kind in ("public_pre_race_csv","nonofficial_openapi_v1"):
        # Do not delay Git first-add for a primary record nearing T-12.
        nearest=min((datetime.fromisoformat(r["cutoff_jst"]) for r in output.values()),
                    default=None)
        if nearest is None or nearest-datetime.now(JST)>timedelta(minutes=4):
            output.update(supplement_unlisted(day,titles,cards,output,provenance))
    if not output:
        # Diagnostic only. A zero eligible count must not be reported as a
        # successful immutable freeze or as certified forecast availability.
        codes=lambda rows: {r.get("レースコード") for r in rows if isinstance(r,dict)}
        print("PROSPECTIVE_CAPTURE_ZERO "+json.dumps({
            "day":day,"source_kind":source_kind,
            "title_rows":len(titles),"card_rows":len(cards),
            "matching_race_codes":len(codes(titles)&codes(cards)),
            "reason":"no_pre_cutoff_eligible_races",
            "formal":False,
        },sort_keys=True),file=sys.stderr)
    saved=0
    for code,record in sorted(output.items()):
        STORE.mkdir(exist_ok=True)
        target=STORE/(code+".json")
        if target.is_symlink():
            raise ValueError("symlink candidate prohibited")
        try:
            with target.open("x",encoding="utf-8") as f:
                json.dump(record,f,ensure_ascii=False,sort_keys=True)
                f.flush()
                os.fsync(f.fileno())
            saved+=1
        except FileExistsError:
            if json.loads(target.read_text(encoding="utf-8")).get("race_code")!=code:
                raise ValueError("existing candidate conflict")
    return {"date":day,"saved":saved,"eligible":len(output),
            "formal_predictions":0,"scoring_enabled":False}

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--date")
    print(json.dumps(collect(p.parse_args().date),ensure_ascii=False))
