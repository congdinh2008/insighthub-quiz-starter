#!/usr/bin/env python3
"""PreToolUse hook: agent must not edit tests the learner has approved (test-as-spec).

Approved tests are listed as glob patterns in .claude/approved-tests.txt.
An empty list makes this hook a no-op. When a test is wrong, the learner edits it
by hand in a separate commit with a `Test-Change-Approved: <reason>` trailer;
CI (scripts/check_approved_tests.py) enforces the same rule on every PR.
"""
import sys
from pathlib import PurePosixPath

sys.path.insert(0, str(PurePosixPath(__file__).parent))
from _common import PROJECT_DIR, block, load_patterns, log, matches, read_event, relative  # noqa: E402

HOOK = "protect-approved-tests"
APPROVED = PROJECT_DIR / ".claude" / "approved-tests.txt"


def main():
    event = read_event()
    data = event.get("tool_input") or {}
    # Edit, Write, MultiEdit: file_path. NotebookEdit: notebook_path.
    # generator_write_test của Playwright test agents (MCP): fileName, tương đối với gốc repo.
    target = relative(data.get("file_path") or data.get("notebook_path") or data.get("fileName") or "")
    patterns = load_patterns(APPROVED)
    if target == ".claude/approved-tests.txt" or (patterns and matches(target, patterns)):
        block(
            HOOK,
            event,
            target,
            f"Hook protect-approved-tests: {target} là test đã duyệt (test-as-spec). "
            "Agent không sửa assertion, expected hoặc fixture để test đạt. Dừng lại và báo học viên; "
            "nếu test sai, học viên tự sửa trong commit riêng có trailer 'Test-Change-Approved: <lý do>'.",
        )
    log(HOOK, event, "allow", target)


if __name__ == "__main__":
    main()
