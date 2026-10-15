#!/usr/bin/env python3
"""In ra header Cookie phiên của tài khoản thử A (hoặc B) để script kiểm gọi API sau khi đã khóa endpoint.

Dùng sau `make seed-users`, khi smoke, E2E, eval adapter hoặc probe restore cần phiên đăng nhập (LR-12):

    export INSIGHTHUB_SESSION_COOKIE="$(python3 scripts/session_cookie.py)"
    python3 scripts/smoke.py

Mật khẩu lấy từ SEED_USER_PASSWORD hoặc khóa đó trong .env như `seed_auth_users.py`. Script chỉ in cookie
ra stdout để gán vào biến môi trường; không ghi file, không log. Cookie là phiên thật của tài khoản thử,
không dán vào công cụ AI hay evidence. Chỉ dùng trên môi trường local hoặc CI fixture.
"""
import argparse
import json
import sys
import urllib.error
import urllib.request

from seed_auth_users import USERS, password_from_env

COOKIE_NAME = "insighthub.session_token"


def session_cookie(web_url: str, email: str, password: str) -> str:
    body = json.dumps({"email": email, "password": password}).encode()
    request = urllib.request.Request(
        f"{web_url}/api/auth/sign-in/email", data=body, method="POST",
        headers={"Content-Type": "application/json", "Origin": web_url},
    )
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            cookies = response.headers.get_all("Set-Cookie") or []
    except urllib.error.HTTPError as exc:
        raise SystemExit(f"Đăng nhập {email} thất bại: HTTP {exc.code}. Chạy make seed-users và kiểm SEED_USER_PASSWORD.")
    for raw in cookies:
        pair = raw.split(";", 1)[0].strip()
        name = pair.split("=", 1)[0]
        if name.endswith(COOKIE_NAME):
            return pair
    raise SystemExit("Không nhận được cookie phiên từ Better Auth.")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--web-url", default="http://127.0.0.1:3107")
    parser.add_argument("--account", choices=["A", "B"], default="A")
    args = parser.parse_args()
    password, generated = password_from_env()
    if generated:
        raise SystemExit("Thiếu SEED_USER_PASSWORD (biến môi trường hoặc .env). Đặt cùng giá trị đã dùng cho make seed-users.")
    email = USERS[0 if args.account == "A" else 1][1]
    print(session_cookie(args.web_url.rstrip("/"), email, password))
    return 0


if __name__ == "__main__":
    sys.exit(main())
