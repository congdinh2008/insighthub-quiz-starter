#!/usr/bin/env python3
"""Eval-driven development harness for InsightHub (Kit K9, Requirements LR-23).

Live:   python3 evaluation/harness/run_eval.py --api-url http://127.0.0.1:8107 --suite evaluation/harness/suites/example-chat.json
Replay: python3 evaluation/harness/run_eval.py --replay reports/evaluation/harness-<time>.json
        (re-grade recorded outputs after changing a grader; no API call, usable in CI)

Real content quality needs RAG_MODE=real. Fixture runs are refused unless
--allow-fixture is given, and are then labelled as pipeline checks only.
"""
import argparse
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
from adapters import ADAPTERS, CORPUS, call  # noqa: E402
from graders import grade  # noqa: E402
from passk import aggregate, suite_rate  # noqa: E402

CASE_KEYS = {"id", "tool", "sources", "input", "expected_status"}
TOOLS = {"chat", "summary", "quiz"}
STATUSES = {"Answered", "NoEvidence", "Failed", "Succeeded"}


def validate_suite(suite):
    problems = []
    for key in ("suite", "version", "cases"):
        if key not in suite:
            problems.append(f"missing {key}")
    ids = set()
    for case in suite.get("cases", []):
        missing = CASE_KEYS - case.keys()
        if missing:
            problems.append(f"{case.get('id', '?')}: missing {sorted(missing)}")
            continue
        if case["id"] in ids:
            problems.append(f"{case['id']}: duplicate id")
        ids.add(case["id"])
        if case["tool"] not in TOOLS:
            problems.append(f"{case['id']}: tool must be one of {sorted(TOOLS)}")
        if case["expected_status"] not in STATUSES:
            problems.append(f"{case['id']}: expected_status must be one of {sorted(STATUSES)}")
        if not 1 <= len(case["sources"]) <= 3:
            problems.append(f"{case['id']}: 1-3 sources (LIM-05)")
        for name in case["sources"]:
            if not (CORPUS / name).is_file():
                problems.append(f"{case['id']}: source not in evaluation/corpus: {name}")
        if case["tool"] == "summary" and case.get("config", {}).get("length") not in ("short", "detailed"):
            problems.append(f"{case['id']}: summary config.length must be short or detailed")
        if case["tool"] == "quiz" and case.get("config", {}).get("question_count") not in (5, 10):
            problems.append(f"{case['id']}: quiz config.question_count must be 5 or 10")
        if case["expected_status"] in ("Answered", "Succeeded") and not case.get("expected_points"):
            problems.append(f"{case['id']}: grounded case needs 3-5 expected_points fixed before running")
    return problems


def commit_sha():
    try:
        return subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True, check=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def summarize(results):
    per_case = aggregate(results)
    return {
        "runs": len(results),
        "runs_passed": sum(r["passed"] for r in results),
        "cases": len(per_case),
        "pass_hat_k_rate": suite_rate(per_case, "pass_hat_k"),
        "pass_at_k_rate": suite_rate(per_case, "pass_at_k"),
        "per_case": per_case,
        "semantic_review": "pending",
    }


def live(args):
    suite = json.loads(Path(args.suite).read_text(encoding="utf-8"))
    problems = validate_suite(suite)
    if problems:
        raise SystemExit("Invalid suite:\n  " + "\n  ".join(problems))
    base = args.api_url.rstrip("/")
    status, raw, _ = call(base, "/system/profile")
    profile = json.loads(raw) if status == 200 else {}
    if profile.get("mode") != "real" and not args.allow_fixture:
        raise SystemExit("Eval needs RAG_MODE=real. Use --allow-fixture only to check the pipeline.")
    adapters = {tool: cls(base) for tool, cls in ADAPTERS.items()}
    report = {
        "schema_version": 1, "created_at": datetime.now(timezone.utc).isoformat(), "commit": commit_sha(),
        "suite": suite["suite"], "suite_version": suite["version"], "profile": profile,
        "evidence_kind": "quality" if profile.get("mode") == "real" else "pipeline-only (fixture)",
        "corpus_sha256": {n: hashlib.sha256((CORPUS / n).read_bytes()).hexdigest()
                          for n in sorted({s for c in suite["cases"] for s in c["sources"]})},
        "cases": suite["cases"], "results": [],
    }
    try:
        for case in suite["cases"]:
            adapter = adapters[case["tool"]]
            document_ids = adapter.ensure_sources(case["sources"])
            for run in range(1, (args.k or case.get("repeat", 1)) + 1):
                try:
                    out = adapter.run(case, document_ids)
                except NotImplementedError as exc:
                    print(f"SKIP {case['id']}: {exc}")
                    break
                passed, checks = grade(case, out, set(document_ids))
                report["results"].append({"case_id": case["id"], "run": run, "passed": passed, "checks": checks,
                                          "allowed_document_ids": document_ids, "output": out,
                                          "semantic_review": {"verdict": "pending", "reviewer": "", "notes": ""}})
                print(f"{case['id']} run={run} {'PASS' if passed else 'FAIL'}", flush=True)
    finally:
        for adapter in adapters.values():
            adapter.cleanup()
    report["summary"] = summarize(report["results"])
    return report


def replay(args):
    report = json.loads(Path(args.replay).read_text(encoding="utf-8"))
    cases = {c["id"]: c for c in report["cases"]}
    for result in report["results"]:
        result["passed"], result["checks"] = grade(cases[result["case_id"]], result["output"], set(result["allowed_document_ids"]))
    report["regraded_at"] = datetime.now(timezone.utc).isoformat()
    report["summary"] = summarize(report["results"])
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--api-url", default="http://127.0.0.1:8107")
    parser.add_argument("--suite", default=str(HERE / "suites" / "example-chat.json"))
    parser.add_argument("--k", type=int, help="Override repeat count for every case")
    parser.add_argument("--replay", help="Re-grade a recorded report without calling the API")
    parser.add_argument("--validate", action="store_true", help="Only validate the suite file")
    parser.add_argument("--allow-fixture", action="store_true")
    parser.add_argument("--output")
    parser.add_argument("--min-pass-hat-k", type=float,
                        help="Exit 1 when the pass^k rate is below this value (0-1). Use in CI as a quality gate")
    args = parser.parse_args(argv)
    if args.validate:
        problems = validate_suite(json.loads(Path(args.suite).read_text(encoding="utf-8")))
        print("\n".join(problems) or "PASS: suite valid")
        return 1 if problems else 0
    report = replay(args) if args.replay else live(args)
    output = Path(args.output) if args.output else ROOT / "reports" / "evaluation" / f"harness-{datetime.now().strftime('%Y%m%d-%H%M%S')}.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    s = report["summary"]
    print(f"{output}\nruns {s['runs_passed']}/{s['runs']} | pass^k {s['pass_hat_k_rate']:.0%} | pass@k {s['pass_at_k_rate']:.0%} | semantic review pending")
    if args.min_pass_hat_k is not None and s["pass_hat_k_rate"] < args.min_pass_hat_k:
        print(f"FAIL: pass^k {s['pass_hat_k_rate']:.0%} < {args.min_pass_hat_k:.0%}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
