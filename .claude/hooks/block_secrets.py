#!/usr/bin/env python3
"""PreToolUse hook: stop Claude Code from reading secrets.

Enforces the data rules of the AI Usage Charter on top of the `deny` rules in
.claude/settings.json. Exit code 2 blocks the tool call and returns the reason
to Claude. This is a safety net, not a security boundary.
"""
import re
import sys
from pathlib import PurePosixPath

sys.path.insert(0, str(PurePosixPath(__file__).parent))
from _common import block, log, read_event, relative  # noqa: E402

HOOK = "block-secrets"
SECRET_FILE = re.compile(r"(^|/)\.env(\.(?!example\b)[\w.-]+)?$|(^|/)secrets(/|$)|\.(pem|key)$")
ENV_TOKEN = re.compile(r"(?<![\w.-])(?:[\w./-]*/)?\.env(?:\.(?!example\b)[\w.-]+)?(?![\w.-])")
ENV_FILE_ARG = re.compile(r"(--env-file[= ]\S+|\bENV_FILE=\S+|--exclude(-dir)?=\S+)")
DUMP_COMMAND = re.compile(
    r"\bprintenv\b|(^|[;&|]\s*)env\s*($|[;&|])|docker(-compose| compose)\b[^;&|]*\bconfig\b"
)
RECURSIVE_GREP = re.compile(r"\b(e|f)?grep\b[^;&|]*\s(-[a-zA-Z]*[rR][a-zA-Z]*|--recursive)\b")
REASON = (
    "Hook block-secrets: không đọc, in hoặc gửi .env, secrets, file khóa. "
    "Cần tên biến cấu hình thì đọc mục 'Cấu hình AI' trong README.md; "
    "chạy ứng dụng bằng make up hoặc make test (Compose tự đọc .env)."
)


def main():
    event = read_event()
    tool = event.get("tool_name", "")
    data = event.get("tool_input") or {}
    if tool == "Bash":
        command = data.get("command", "")
        scanned = ENV_FILE_ARG.sub(" ", command)
        if RECURSIVE_GREP.search(command) and "--exclude" not in command:
            block(HOOK, event, command[:120], REASON + " Tìm kiếm đệ quy: dùng Grep tool (tôn trọng .gitignore) hoặc thêm --exclude='.env*'.")
        if ENV_TOKEN.search(scanned) or DUMP_COMMAND.search(command) or re.search(r"(\bsecrets/|\.pem\b|\.key\b)", scanned):
            block(HOOK, event, command[:120], REASON)
        log(HOOK, event, "allow", command[:120])
        return
    targets = [data.get(key, "") for key in ("file_path", "path", "pattern", "glob", "notebook_path")]
    for target in filter(None, targets):
        rel = relative(target) if tool in ("Read", "NotebookEdit") else target
        if SECRET_FILE.search(rel) or ENV_TOKEN.search(target):
            block(HOOK, event, rel, REASON)
    log(HOOK, event, "allow", ",".join(filter(None, targets))[:120])


if __name__ == "__main__":
    main()
