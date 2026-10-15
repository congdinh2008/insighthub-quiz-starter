#!/usr/bin/env python3
"""CI guard for test-as-spec (LR-13).

A test is approved once its glob pattern is in .claude/approved-tests.txt at the
parent of a commit. Every commit in BASE..HEAD that changes an approved test, or
removes a pattern from the list (weakening the guard), must carry the trailer
`Test-Change-Approved: <reason>` written by the learner. Adding a new test and
approving it (adding its pattern) needs no trailer.

Usage: python3 scripts/check_approved_tests.py --base origin/main
"""
import argparse
import fnmatch
import subprocess
import sys

PATTERN_FILE = ".claude/approved-tests.txt"
TRAILER = "Test-Change-Approved:"


def git(*args):
    return subprocess.run(["git", *args], check=True, capture_output=True, text=True).stdout


def parse_patterns(text):
    return {line.strip() for line in text.splitlines() if line.strip() and not line.strip().startswith("#")}


def patterns_at(ref):
    try:
        return parse_patterns(git("show", f"{ref}:{PATTERN_FILE}"))
    except subprocess.CalledProcessError:
        return set()


def violations(base, head="HEAD"):
    found = []
    for sha in reversed(git("rev-list", "--first-parent", f"{base}..{head}").split()):
        parent = f"{sha}^"
        before = patterns_at(parent)
        files = git("diff", "--name-only", parent, sha).split()
        guarded = [f for f in files if any(fnmatch.fnmatch(f, p) for p in before)]
        if PATTERN_FILE in files and before - patterns_at(sha):
            guarded.append(PATTERN_FILE + " (removed patterns: " + ", ".join(sorted(before - patterns_at(sha))) + ")")
        if not guarded:
            continue
        message = git("log", "-1", "--format=%B", sha)
        reason = next((line.split(":", 1)[1].strip() for line in message.splitlines() if line.startswith(TRAILER)), "")
        if not reason:
            found.append((sha[:10], guarded))
    return found


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", required=True, help="Base ref, for example origin/main")
    parser.add_argument("--head", default="HEAD")
    args = parser.parse_args()
    try:
        git("rev-parse", "--verify", "--quiet", f"{args.base}^{{commit}}")
    except subprocess.CalledProcessError:
        print(f"FAIL: không tìm thấy base ref '{args.base}'. Chạy 'git fetch origin' hoặc checkout với fetch-depth: 0.")
        return 2
    problems = violations(args.base, args.head)
    if problems:
        for sha, files in problems:
            print(f"FAIL {sha}: sửa test đã duyệt mà thiếu trailer '{TRAILER} <lý do>': {', '.join(files)}")
        print("Test-as-spec: học viên tự sửa test đã duyệt trong commit riêng và ghi lý do; agent không sửa test để đạt.")
        return 1
    print("PASS: không có thay đổi test đã duyệt thiếu trailer.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
