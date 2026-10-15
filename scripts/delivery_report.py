#!/usr/bin/env python3
"""Summarize docs/ai/delivery-log.csv into delivery KPIs (Kit K10, LR-29 baseline).

Metrics are proxies for a local, single-developer project and are labelled so.
They are NOT the DORA software delivery metrics (dora.dev/guides/dora-metrics),
which are measured per deployment to production:
- PR lead time (proxy for DORA change lead time): pr_opened -> pr_merged, hours
- CI first-run failure (proxy, not DORA change fail rate): share of PRs whose first CI run failed
- PR rework rate (proxy, not DORA deployment rework rate): share of PRs with rework_rounds > 0 or outcome = rework
- Review load: review minutes per PR and per 100 diff lines
- AI review precision: ai_findings_valid / ai_findings
- Agent PR first-pass acceptance: agent PRs (agent_mode edit or auto) accepted with at most
  one rework round, over agent PRs whose outcome and rework_rounds are recorded
- Cost per accepted change: total cost_usd (or tokens) of all recorded PRs, including
  rejected or reworked ones, over the number of accepted PRs
Blank cells are treated as "not measured", never as zero.
"""
import argparse
import csv
import statistics
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOG = ROOT / "docs" / "ai" / "delivery-log.csv"


def num(value):
    try:
        return float(value) if value is not None and str(value).strip() != "" else None
    except ValueError:
        return None


def parse_time(value):
    try:
        return datetime.fromisoformat(value.strip()) if value and value.strip() else None
    except ValueError:
        return None


def median(values):
    values = [v for v in values if v is not None]
    return statistics.median(values) if values else None


def ratio(part, whole):
    return part / whole if whole else None


AGENT_MODES = {"edit", "auto"}


def metrics(rows):
    lead = []
    for r in rows:
        opened, merged = parse_time(r.get("pr_opened")), parse_time(r.get("pr_merged"))
        if opened and merged:
            lead.append((merged - opened).total_seconds() / 3600)
    ci = [r for r in rows if r.get("ci_first_run", "").strip().lower() in ("pass", "fail")]
    rework_known = [r for r in rows if num(r.get("rework_rounds")) is not None or r.get("outcome")]
    reworked = [r for r in rework_known if (num(r.get("rework_rounds")) or 0) > 0 or r.get("outcome") == "rework"]
    accepted = [r for r in rows if r.get("outcome") == "accepted"]
    findings = sum(num(r.get("ai_findings")) or 0 for r in rows)
    valid = sum(num(r.get("ai_findings_valid")) or 0 for r in rows)
    review = [num(r.get("review_minutes")) for r in rows]
    per_100 = [num(r.get("review_minutes")) / num(r.get("diff_lines")) * 100
               for r in rows if num(r.get("review_minutes")) is not None and num(r.get("diff_lines"))]
    agent_known = [r for r in rows if r.get("agent_mode", "").strip().lower() in AGENT_MODES
                   and r.get("outcome", "").strip() and num(r.get("rework_rounds")) is not None]
    first_pass = [r for r in agent_known if r.get("outcome").strip() == "accepted" and num(r.get("rework_rounds")) <= 1]
    costs = [num(r.get("cost_usd")) for r in rows if num(r.get("cost_usd")) is not None]
    tokens = [num(r.get("tokens")) for r in rows if num(r.get("tokens")) is not None]
    return {
        "PR": len(rows),
        "PR accepted": len(accepted),
        "PR lead time median, giờ (proxy)": median(lead),
        "CI lần đầu fail (proxy, không phải DORA change fail rate)": ratio(sum(r["ci_first_run"].strip().lower() == "fail" for r in ci), len(ci)),
        "PR rework rate (proxy, không phải DORA deployment rework rate)": ratio(len(reworked), len(rework_known)),
        "Review phút/PR (median)": median(review),
        "Review phút/100 dòng diff (median)": median(per_100),
        "AI review precision": ratio(valid, findings),
        "PR agent được chấp nhận lần đầu (tối đa 1 vòng sửa)": ratio(len(first_pass), len(agent_known)),
        "Author phút/PR (median)": median([num(r.get("author_minutes")) for r in rows]),
        "Cost USD/accepted change": ratio(sum(costs), len(accepted)) if costs else None,
        "Tokens/accepted change": ratio(sum(tokens), len(accepted)) if tokens else None,
    }


PERCENT = {"CI lần đầu fail (proxy, không phải DORA change fail rate)", "PR rework rate (proxy, không phải DORA deployment rework rate)", "AI review precision",
           "PR agent được chấp nhận lần đầu (tối đa 1 vòng sửa)"}


def fmt(key, value):
    if value is None:
        return "chưa đo"
    if key in PERCENT:
        return f"{value:.0%}"
    return f"{value:.1f}" if isinstance(value, float) else str(value)


def render(rows):
    groups = defaultdict(list)
    for r in rows:
        groups[r.get("milestone") or "?"].append(r)
    columns = ["Tổng"] + sorted(groups)
    data = {"Tổng": metrics(rows), **{m: metrics(v) for m, v in groups.items()}}
    lines = ["| KPI | " + " | ".join(columns) + " |", "| --- |" + " --- |" * len(columns)]
    for key in data["Tổng"]:
        lines.append(f"| {key} | " + " | ".join(fmt(key, data[c][key]) for c in columns) + " |")
    lines.append("")
    lines.append("Số liệu là proxy cho dự án cá nhân local, không phải DORA metrics đo theo lần triển khai production. "
                 "Ghi nhãn proxy khi trình bày. Không dùng LOC, số prompt hoặc token làm KPI chính (LR-29).")
    return "\n".join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--file", default=str(LOG))
    parser.add_argument("--output")
    args = parser.parse_args(argv)
    with open(args.file, newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    if not rows:
        print("Delivery log chưa có dòng nào. Ghi một dòng cho mỗi PR từ M1.")
        return 0
    report = render(rows)
    if args.output:
        Path(args.output).write_text(report + "\n", encoding="utf-8")
    print(report)
    return 0


if __name__ == "__main__":
    sys.exit(main())
