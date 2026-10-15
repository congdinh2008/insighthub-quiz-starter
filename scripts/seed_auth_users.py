#!/usr/bin/env python3
"""Tạo hai tài khoản thử A và B đã xác minh email để chạy hành trình và kiểm quyền (Auth scaffold).

Đăng ký qua endpoint của Better Auth (giống người dùng thật), sau đó đánh dấu email đã xác minh
trực tiếp trong database vì đây là dữ liệu thử. Chỉ dùng trên môi trường local.
Mật khẩu lấy từ biến SEED_USER_PASSWORD hoặc khóa đó trong .env; thiếu thì sinh ngẫu nhiên.
Không in mật khẩu trừ khi được sinh mới.
"""

import argparse
import json
import os
import secrets
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
USERS = [("Người dùng A", "a@insighthub.test"), ("Người dùng B", "b@insighthub.test")]


def password_from_env() -> tuple[str, bool]:
    value = os.environ.get("SEED_USER_PASSWORD", "")
    env_file = ROOT / ".env"
    if not value and env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            if line.startswith("SEED_USER_PASSWORD="):
                value = line.split("=", 1)[1].strip().strip('"').strip("'")
    if value:
        return value, False
    return secrets.token_urlsafe(18), True


def sign_up(web_url: str, name: str, email: str, password: str) -> str:
    body = json.dumps({"name": name, "email": email, "password": password}).encode()
    request = urllib.request.Request(
        f"{web_url}/api/auth/sign-up/email", data=body, method="POST",
        headers={"Content-Type": "application/json", "Origin": web_url},
    )
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            return f"tạo mới ({response.status})"
    except urllib.error.HTTPError as exc:
        payload = exc.read().decode(errors="replace")
        if exc.code in (400, 422) and "exist" in payload.lower():
            return "đã tồn tại"
        raise SystemExit(f"Đăng ký {email} thất bại: HTTP {exc.code}")


def mark_verified(emails: list[str], compose: list[str]) -> None:
    quoted = ",".join("'" + e.replace("'", "''") + "'" for e in emails)
    sql = f"UPDATE auth_user SET email_verified = true, updated_at = now() WHERE email IN ({quoted});"
    subprocess.run([*compose, "exec", "-T", "postgres", "psql", "-q", "-v", "ON_ERROR_STOP=1",
                    "-U", "insighthub", "-d", "insighthub", "-c", sql], check=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--web-url", default="http://127.0.0.1:3107")
    parser.add_argument("--compose", default="docker compose")
    args = parser.parse_args()
    password, generated = password_from_env()
    for name, email in USERS:
        print(f"{email}: {sign_up(args.web_url.rstrip('/'), name, email, password)}")
    mark_verified([email for _, email in USERS], args.compose.split())
    print("Đã đánh dấu email đã xác minh cho tài khoản thử.")
    if generated:
        print(f"Mật khẩu sinh ngẫu nhiên cho cả hai tài khoản: {password}")
        print("Lưu vào .env với khóa SEED_USER_PASSWORD nếu muốn dùng lại.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
