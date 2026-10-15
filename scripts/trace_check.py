#!/usr/bin/env python3
"""Validate trace/ac-trace.csv (verification at scale, Requirements 16.1).

Default mode checks consistency only, so an early milestone with mostly NotRun rows
passes. `--gate M4` or `--gate M5` also fails when Core AC due by that milestone are
still NotRun or unverified.

Usage:
  python3 scripts/trace_check.py
  python3 scripts/trace_check.py --gate M4
"""
import argparse
import re
import sys

from trace_lib import (
    COLUMNS,
    DRAFT_BY,
    MILESTONE_ORDER,
    REQUIREMENTS,
    RISKS,
    TIERS,
    TRACE,
    VERDICTS,
    VERIFICATION,
    VERIFY_METHODS,
    final_milestone,
    read_rows,
    requirement_scopes,
)

COMMIT = re.compile(r"^[0-9a-f]{7,40}$")
RISK_RANK = {"R1": 1, "R2": 2, "R3": 3}


def check(rows, fieldnames, scopes, gate=None):
    errors, warnings = [], []
    missing = [c for c in COLUMNS if c not in fieldnames]
    if missing:
        return [f"Thiếu cột: {', '.join(missing)}"], warnings
    ids = [r["ac_id"] for r in rows]
    if len(ids) != len(set(ids)):
        errors.append("ac_id bị trùng")
    if scopes and set(ids) != set(scopes):
        errors.append(f"Danh sách AC lệch Requirements: thiếu {sorted(set(scopes) - set(ids))[:5]}, thừa {sorted(set(ids) - set(scopes))[:5]}")
    gate_index = MILESTONE_ORDER.index(gate) if gate else None
    for r in rows:
        ac = r["ac_id"]
        def err(msg, ac=ac):
            errors.append(f"{ac}: {msg}")

        if scopes and ac in scopes and r["scope"] != scopes[ac]:
            err(f"scope {r['scope']} khác Requirements ({scopes[ac]})")
        if r["tier"] not in TIERS:
            err(f"tier không hợp lệ: {r['tier']}")
        if r["verdict"] not in VERDICTS:
            err(f"verdict không hợp lệ: {r['verdict']}")
        if r["draft_by"] not in DRAFT_BY:
            err(f"draft_by chỉ nhận AI hoặc Human: {r['draft_by']}")
        if r["verify_method"] not in VERIFY_METHODS:
            err(f"verify_method không hợp lệ: {r['verify_method']}")
        if r["scope"] == "N":
            if r["verdict"] != "OutOfScope" or r["tier"] != "OutOfScope":
                err("AC ngoài phạm vi phải có tier và verdict OutOfScope")
            continue
        if r["verification"] not in VERIFICATION:
            err(f"verification không hợp lệ: {r['verification']}")
        if r["risk"] not in RISKS:
            err(f"risk không hợp lệ: {r['risk']}")
        elif r["risk_suggested"] in RISKS and RISK_RANK[r["risk"]] > RISK_RANK[r["risk_suggested"]] and not r["risk_reason"].strip():
            err(f"hạ mức rủi ro {r['risk_suggested']} -> {r['risk']} phải ghi risk_reason")
        if r["verdict"] == "OutOfScope":
            err("AC áp dụng không được ghi OutOfScope")
        if r["verdict"] == "Extended-NotDone" and r["tier"] != "Extended":
            err("Extended-NotDone chỉ dùng cho AC tầng Extended")
        if r["verification"] == "Human-verified":
            for column in ("expected", "verified_by", "verify_method"):
                if not r[column].strip():
                    err(f"Human-verified thiếu {column}")
        if r["verdict"] in ("Passed", "Failed"):
            if not COMMIT.match(r["commit"].strip()):
                err(f"{r['verdict']} cần commit SHA đã kiểm")
            for column in ("actual", "evidence"):
                if not r[column].strip():
                    err(f"{r['verdict']} thiếu {column}")
        if r["verdict"] == "Passed":
            if r["verification"] != "Human-verified":
                err("Passed khi expected chưa Human-verified")
            if r["risk"] == "R1" and not r["test_ids"].strip():
                err("AC R1 Passed cần test_ids của evidence trực tiếp")
        if r["verdict"] == "Blocked" and not r["notes"].strip():
            err("Blocked cần ghi nguyên nhân và bước xử lý trong notes")
        if r["draft_by"] == "AI" and r["verification"] == "Unverified" and r["verdict"] not in ("NotRun", "Extended-NotDone"):
            err("bản nháp AI chưa verify không được có verdict")
        if gate_index is not None and r["tier"] == "Core":
            due = final_milestone(r["due"])
            if due and MILESTONE_ORDER.index(due) <= gate_index and (r["verdict"] == "NotRun" or r["verification"] != "Human-verified"):
                err(f"Core đến hạn {due} chưa có kết quả tại gate {gate}")
        if r["tier"] == "Pending" and gate:
            warnings.append(f"{ac}: tier còn Pending; cập nhật skeleton khi danh sách Core được công bố")
    return errors, warnings


def summary(rows):
    applied = [r for r in rows if r["scope"] != "N"]
    count = lambda key, value: sum(r[key] == value for r in applied)  # noqa: E731
    return (f"{len(applied)} AC áp dụng | Human-verified {count('verification', 'Human-verified')} | "
            f"AI-drafted {count('draft_by', 'AI')} | Passed {count('verdict', 'Passed')} | Failed {count('verdict', 'Failed')} | "
            f"Blocked {count('verdict', 'Blocked')} | NotRun {count('verdict', 'NotRun')} | "
            f"R1/R2/R3 {count('risk', 'R1')}/{count('risk', 'R2')}/{count('risk', 'R3')}")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--file", default=str(TRACE))
    parser.add_argument("--requirements", default=str(REQUIREMENTS))
    parser.add_argument("--gate", choices=["M4", "M5"])
    args = parser.parse_args(argv)
    fieldnames, rows = read_rows(args.file)
    errors, warnings = check(rows, fieldnames, requirement_scopes(args.requirements), args.gate)
    for line in warnings[:10]:
        print("WARN", line)
    if len(warnings) > 10:
        print(f"WARN ... và {len(warnings) - 10} cảnh báo khác")
    if errors:
        for line in errors:
            print("FAIL", line)
        print(f"{len(errors)} lỗi trong {args.file}")
        return 1
    print("PASS:", summary(rows))
    return 0


if __name__ == "__main__":
    sys.exit(main())
