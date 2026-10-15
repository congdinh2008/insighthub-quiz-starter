import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

// Requirements 1.3 mục 2.1.5: khôi phục, đặt lại, đổi mật khẩu, tái xác thực và sửa hồ sơ là Extended.
// Starter tắt các endpoint thư viện tương ứng; đăng ký, đăng nhập, đăng xuất, xác minh email (Core) giữ nguyên.
const source = readFileSync(new URL("../lib/auth/config.ts", import.meta.url), "utf8");
const block = source.match(/extendedAuthPaths = \[([^\]]*)\]/);

test("Extended auth endpoints are disabled by default", () => {
  assert.ok(block, "extendedAuthPaths must exist");
  const paths = [...block[1].matchAll(/"([^"]+)"/g)].map(m => m[1]);
  for (const path of ["/request-password-reset", "/reset-password", "/change-password", "/verify-password", "/update-user"]) {
    assert.ok(paths.includes(path), path);
  }
  for (const path of ["/sign-up/email", "/sign-in/email", "/sign-out", "/verify-email", "/get-session", "/send-verification-email"]) {
    assert.ok(!paths.includes(path), "Core path must stay enabled: " + path);
  }
  assert.match(source, /disabledPaths: \[\.\.\.extendedAuthPaths\]/);
});
