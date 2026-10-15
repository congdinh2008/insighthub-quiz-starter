import test from "node:test";
import assert from "node:assert/strict";
import { errorMessage, allowsMutation } from "../lib/errors.ts";

test("validation arrays and malformed errors never become [object Object]", () => {
  for (const value of [null, {}, { detail: [] }, { detail: [{ msg: "invalid" }] }, { detail: " " }]) {
    assert.equal(errorMessage(value, "Upload lỗi"), "Upload lỗi");
  }
  assert.equal(errorMessage({ detail: "File vượt giới hạn" }, "Lỗi"), "File vượt giới hạn");
});

test("mutation origin guard rejects foreign browsers and accepts same origin or CLI", () => {
  const url = "http://localhost:3107/api/proxy?target=upload";
  assert.equal(allowsMutation(new Request(url)), true);
  assert.equal(allowsMutation(new Request(url, { headers: { origin: "http://localhost:3107" } })), true);
  for (const origin of ["https://foreign.example", "null", "http://localhost:3000"]) {
    assert.equal(allowsMutation(new Request(url, { headers: { origin } })), false);
  }
});

test("standalone proxy uses configured public origins instead of its internal hostname", () => {
  const req = new Request("http://0.0.0.0:3000/api/proxy", { headers: { origin: "http://127.0.0.1:3107" } });
  assert.equal(allowsMutation(req), true);
  assert.equal(allowsMutation(req, ["http://localhost:9999"]), false);
});
