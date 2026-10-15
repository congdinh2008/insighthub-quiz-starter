#!/usr/bin/env python3
"""Stratified, seeded sampling of AI-drafted trace rows (Requirements LR-08).

Sample:   python3 scripts/trace_sample.py --seed 20261004 --size 10
Extended: python3 scripts/trace_sample.py --seed hv01 --size 5 --tier Extended
Evaluate: python3 scripts/trace_sample.py --evaluate

Sampling picks applied AC (scope != N) that are still Unverified, stratified by
function group. `--tier Core` (default) samples Core rows. `--tier Extended`
samples only Extended rows the learner drafted with AI (draft_by=AI), which is
the M2.1 LR-08 sampling exercise. Picks are appended to trace/sampling-log.csv. The learner then checks
each sampled row against the SRS and fills `result` with OK or Error (and
`error_type`). `--evaluate` computes the error rate per round: at or above the
threshold (default 20%, i.e. 2 of 10) the AI draft is not trusted, so fix the
context pack or skill prompt, regenerate the affected groups and sample again.
"""
import argparse
import datetime
import random
import sys
from collections import defaultdict
from pathlib import Path

from trace_lib import SAMPLING_COLUMNS, SAMPLING_LOG, TRACE, read_rows, write_rows


def allocate(groups, size):
    """Proportional allocation, at least one per group while size allows (largest remainder)."""
    total = sum(len(v) for v in groups.values())
    size = min(size, total)
    keys = sorted(groups, key=lambda k: (-len(groups[k]), k))
    alloc = {k: 0 for k in keys}
    for k in keys[:size]:
        alloc[k] = 1
    remaining = size - sum(alloc.values())
    if remaining > 0:
        quotas = {k: remaining * len(groups[k]) / total for k in keys}
        for k in keys:
            alloc[k] += min(int(quotas[k]), len(groups[k]) - alloc[k])
        left = size - sum(alloc.values())
        for k in sorted(keys, key=lambda k: (-(quotas[k] - int(quotas[k])), k)):
            if left <= 0:
                break
            if alloc[k] < len(groups[k]):
                alloc[k] += 1
                left -= 1
    return alloc


def in_population(r, tier):
    if r["scope"] == "N" or r["verification"] != "Unverified":
        return False
    if tier == "Extended":
        return r["tier"] == "Extended" and r["draft_by"] == "AI"
    return r["tier"] != "Extended"


def sample(rows, seed, size, tier="Core"):
    population = [r for r in rows if in_population(r, tier)]
    groups = defaultdict(list)
    for r in population:
        groups[r["group"]].append(r)
    rng = random.Random(str(seed))
    picked = []
    for group, n in allocate(groups, size).items():
        members = sorted(groups[group], key=lambda r: r["ac_id"])
        picked.extend(rng.sample(members, n))
    return len(population), sorted(picked, key=lambda r: r["ac_id"])


def evaluate(log_rows, threshold):
    rounds = defaultdict(list)
    for r in log_rows:
        rounds[r["round"]].append(r)
    results = []
    for round_id, items in sorted(rounds.items(), key=lambda kv: int(kv[0])):
        checked = [r for r in items if r["result"] in ("OK", "Error")]
        errors = sum(r["result"] == "Error" for r in checked)
        pending = len(items) - len(checked)
        if pending:
            decision = "PENDING: còn dòng chưa ghi result"
        elif checked and errors / len(checked) >= threshold:
            decision = "EXPAND: sửa context pack hoặc prompt của skill, sinh lại nhóm lỗi, lấy mẫu vòng mới"
        else:
            decision = "ACCEPT: giữ phần còn lại ở AI-drafted; verify just-in-time trước khi giao agent"
        results.append((round_id, len(items), errors, pending, decision))
    return results


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--file", default=str(TRACE))
    parser.add_argument("--log", default=str(SAMPLING_LOG))
    parser.add_argument("--seed")
    parser.add_argument("--size", type=int, default=10)
    parser.add_argument("--tier", choices=("Core", "Extended"), default="Core")
    parser.add_argument("--evaluate", action="store_true")
    parser.add_argument("--threshold", type=float, default=0.2)
    args = parser.parse_args(argv)
    log_path = Path(args.log)
    log_rows = read_rows(log_path)[1] if log_path.is_file() else []
    if args.evaluate:
        if not log_rows:
            print("Chưa có vòng lấy mẫu nào.")
            return 1
        for round_id, n, errors, pending, decision in evaluate(log_rows, args.threshold):
            print(f"Vòng {round_id}: {n} dòng, {errors} lỗi, {pending} chưa kiểm -> {decision}")
        return 0
    if not args.seed:
        parser.error("--seed là bắt buộc để người khác tái lập được mẫu")
    _, rows = read_rows(args.file)
    population, picked = sample(rows, args.seed, args.size, args.tier)
    if not picked:
        hint = " Ghi draft_by=AI cho các dòng Extended đã viết nháp bằng AI." if args.tier == "Extended" else ""
        print(f"Không có dòng {args.tier} nào ở trạng thái Unverified để lấy mẫu.{hint}")
        return 1
    round_id = str(max((int(r["round"]) for r in log_rows), default=0) + 1)
    today = datetime.date.today().isoformat()
    for r in picked:
        log_rows.append({"round": round_id, "date": today, "seed": args.seed, "population": population,
                         "ac_id": r["ac_id"], "group": r["group"], "risk": r["risk"],
                         "result": "", "error_type": "", "notes": ""})
    write_rows(log_path, SAMPLING_COLUMNS, log_rows)
    print(f"Vòng {round_id} (seed {args.seed}, {args.tier}): {len(picked)}/{population} dòng Unverified")
    for r in picked:
        print(f"  {r['ac_id']:<18} {r['group']:<5} {r['risk']}  {r['srs_ref']}")
    print(f"Ghi result OK/Error vào {log_path.name}, sau đó chạy --evaluate.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
