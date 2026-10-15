// AI Job scaffold phía web: envelope lỗi và giữ idempotency key khi chưa biết kết quả.
import test from "node:test";
import assert from "node:assert/strict";
import { parseApiError, fieldErrors } from "../lib/api-error.ts";

class MemoryStorage {
  constructor() { this.map = new Map(); }
  get length() { return this.map.size; }
  key(index) { return [...this.map.keys()][index] ?? null; }
  getItem(key) { return this.map.has(key) ? this.map.get(key) : null; }
  setItem(key, value) { this.map.set(key, String(value)); }
  removeItem(key) { this.map.delete(key); }
}
Object.defineProperty(globalThis, "sessionStorage", { value: new MemoryStorage(), configurable: true });
const { startJob, pendingJobs } = await import("../lib/jobs.ts");

function reply(status, body, headers = {}) {
  return async () => new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json", ...headers } });
}

test("parseApiError đọc code, fields, Retry-After và không phụ thuộc chuỗi tiếng Việt", () => {
  const headers = new Headers({ "Retry-After": "12", "X-Request-ID": "req-1" });
  const error = parseApiError(429, { code: "ai_rate_limited", message: "Thử lại sau.", fields: [{ field: "source_ids", code: "duplicate" }, { bad: 1 }] }, headers);
  assert.equal(error.code, "ai_rate_limited");
  assert.equal(error.retryAfterSeconds, 12);
  assert.equal(error.requestId, "req-1");
  assert.deepEqual(fieldErrors(error), { source_ids: "duplicate" });
  const legacy = parseApiError(400, { detail: "Thiếu dữ liệu." });
  assert.equal(legacy.message, "Thiếu dữ liệu.");
  assert.equal(legacy.code, "http_400");
  assert.equal(parseApiError(0, null).code, "network_error");
});

test("startJob lưu key trước khi gửi, giữ key khi mất kết nối và gửi lại đúng key", async () => {
  const seen = [];
  globalThis.fetch = async (url, init) => { seen.push(init.headers["Idempotency-Key"]); throw new TypeError("offline"); };
  const first = await startJob("summary", "/api/x", { source_ids: [1] }, { userId: "u1" });
  assert.equal(first.ok, false);
  assert.equal(first.error.code, "network_error");
  const [pending] = pendingJobs("u1");
  assert.equal(pending.key, seen[0]);
  globalThis.fetch = async (url, init) => { seen.push(init.headers["Idempotency-Key"]); return reply(202, { id: "j1", status: "Processing" })(); };
  const again = await startJob("summary", "/api/x", null, { userId: "u1", pending });
  assert.equal(again.ok, true);
  assert.equal(seen[1], seen[0]);
  assert.equal(pendingJobs("u1")[0].jobId, "j1");
  assert.deepEqual(pendingJobs("u2"), []);
});

test("startJob bỏ key khi API trả lỗi xác định hoặc tác vụ đã kết thúc", async () => {
  globalThis.fetch = reply(429, { code: "ai_job_running", message: "x", retry_after_seconds: 30 }, { "Retry-After": "30" });
  const limited = await startJob("quiz", "/api/q", {}, { userId: "u3" });
  assert.equal(limited.ok, false);
  assert.equal(limited.error.retryAfterSeconds, 30);
  assert.deepEqual(pendingJobs("u3"), []);
  globalThis.fetch = reply(504, { code: "proxy_timeout", message: "x" });
  await startJob("quiz", "/api/q", {}, { userId: "u3" });
  assert.equal(pendingJobs("u3").length, 1);
  globalThis.fetch = reply(200, { id: "j2", status: "Succeeded" });
  await startJob("quiz", "/api/q", null, { userId: "u3", pending: pendingJobs("u3")[0] });
  assert.deepEqual(pendingJobs("u3"), []);
});
