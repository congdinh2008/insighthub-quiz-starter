"""Shared helpers for InsightHub Claude Code hooks (stdlib only)."""
import datetime
import fnmatch
import json
import os
import sys
from pathlib import Path

PROJECT_DIR = Path(os.environ.get("CLAUDE_PROJECT_DIR") or Path(__file__).resolve().parents[2])
LOG_FILE = PROJECT_DIR / "reports" / "hooks" / "events.jsonl"


def read_event():
    try:
        return json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return {}


def relative(path):
    if not path:
        return ""
    candidate = Path(path)
    if not candidate.is_absolute():
        candidate = PROJECT_DIR / candidate
    try:
        return candidate.resolve().relative_to(PROJECT_DIR.resolve()).as_posix()
    except ValueError:
        return candidate.as_posix()


def log(hook, event, decision, target, reason=""):
    """Append one evidence line. Never log file content or command output."""
    try:
        LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        record = {
            "time": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
            "hook": hook,
            "event": event.get("hook_event_name", "PreToolUse"),
            "tool": event.get("tool_name", ""),
            "decision": decision,
            "target": target[:200],
            "reason": reason,
        }
        with LOG_FILE.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
    except OSError:
        pass


def load_patterns(path):
    if not path.is_file():
        return []
    patterns = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            patterns.append(line)
    return patterns


def matches(path, patterns):
    return any(fnmatch.fnmatch(path, pattern) for pattern in patterns)


def block(hook, event, target, reason):
    log(hook, event, "deny", target, reason)
    print(reason, file=sys.stderr)
    sys.exit(2)
