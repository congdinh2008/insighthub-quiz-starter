"""Shared definitions for trace/ac-trace.csv (stdlib only)."""
import csv
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TRACE = ROOT / "trace" / "ac-trace.csv"
SAMPLING_LOG = ROOT / "trace" / "sampling-log.csv"
REQUIREMENTS = ROOT / "docs" / "learner" / "01_Requirements_InsightHub.md"

INSTRUCTOR_COLUMNS = ["ac_id", "req_id", "group", "scope", "tier", "risk_suggested", "lr", "due", "uat", "srs_ref"]
LEARNER_COLUMNS = [
    "risk", "risk_reason", "branches", "expected", "draft_by", "verification", "verified_by",
    "verify_method", "design_ref", "test_ids", "actual", "commit", "evidence", "verdict", "notes",
]
COLUMNS = INSTRUCTOR_COLUMNS + LEARNER_COLUMNS
SAMPLING_COLUMNS = ["round", "date", "seed", "population", "ac_id", "group", "risk", "result", "error_type", "notes"]

TIERS = {"Core", "Extended", "Pending", "OutOfScope"}
RISKS = {"R1", "R2", "R3"}
DRAFT_BY = {"", "AI", "Human"}
VERIFICATION = {"Unverified", "Human-verified"}
VERIFY_METHODS = {"", "SRS-crosscheck", "Test", "Sample", "Review"}
VERDICTS = {"NotRun", "Passed", "Failed", "Blocked", "Extended-NotDone", "OutOfScope"}
MILESTONE_ORDER = ["M2.1", "M2", "M3.1", "M3", "M4", "M5"]
REQ_ROW = re.compile(r"^\| (IH-[A-Z]+-\d{3}) \| (IH-[A-Z]+-\d{3}-AC\d{2}) \| (A|D\d|N) \|", re.M)


def read_rows(path=TRACE):
    with Path(path).open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        return list(reader.fieldnames or []), list(reader)


def write_rows(path, fieldnames, rows):
    with Path(path).open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def requirement_scopes(path=REQUIREMENTS):
    path = Path(path)
    if not path.is_file():
        return {}
    return {ac: scope for _, ac, scope in REQ_ROW.findall(path.read_text(encoding="utf-8"))}


def final_milestone(due):
    """'M3 -> M4' -> 'M4'; 'Mở rộng' -> ''."""
    parts = [p.strip() for p in due.replace("→", "->").split("->")]
    return parts[-1] if parts and parts[-1] in MILESTONE_ORDER else ""
