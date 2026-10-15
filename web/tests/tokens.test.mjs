// Kiểm design token: prototype HTML (design/prototype/_base/tokens.css) dùng đúng giá trị của web,
// và các cặp màu chính đạt độ tương phản WCAG (chữ >= 4,5:1, viền điều khiển >= 3:1).
import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const read = (path) => readFileSync(new URL(path, import.meta.url), "utf8");

function rootTokens(css) {
  const block = css.match(/:root\s*\{([\s\S]*?)\n\}/);
  assert.ok(block, "thiếu khối :root");
  return Object.fromEntries([...block[1].matchAll(/(--[\w-]+):\s*([^;]+);/g)].map((m) => [m[1], m[2].trim()]));
}

const web = rootTokens(read("../app/globals.css"));
const proto = rootTokens(read("../../design/prototype/_base/tokens.css"));

test("prototype tokens trùng khớp với web/app/globals.css", () => {
  for (const [name, value] of Object.entries(web)) {
    assert.equal(proto[name], value, `${name}: web=${value}, prototype=${proto[name]}`);
  }
});

function luminance(hex) {
  const [r, g, b] = hex.match(/^#([0-9a-f]{2})([0-9a-f]{2})([0-9a-f]{2})$/i).slice(1).map((h) => {
    const c = parseInt(h, 16) / 255;
    return c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4;
  });
  return 0.2126 * r + 0.7152 * g + 0.0722 * b;
}

function contrast(a, b) {
  const [hi, lo] = [luminance(web[a]), luminance(web[b])].sort((x, y) => y - x);
  return (hi + 0.05) / (lo + 0.05);
}

test("chữ đạt tương phản 4,5:1", () => {
  const pairs = [
    ["--foreground", "--background"], ["--foreground", "--card"], ["--muted-foreground", "--background"],
    ["--muted-foreground", "--card"], ["--muted-foreground", "--muted"], ["--primary-foreground", "--primary"],
    ["--destructive-foreground", "--destructive"], ["--warning", "--background"], ["--status-ready", "--background"],
    ["--status-processing", "--background"], ["--status-failed", "--background"], ["--status-noevidence", "--background"],
  ];
  for (const [fg, bg] of pairs) {
    const ratio = contrast(fg, bg);
    assert.ok(ratio >= 4.5, `${fg} trên ${bg}: ${ratio.toFixed(2)}:1`);
  }
});

test("viền điều khiển và focus ring đạt 3:1", () => {
  for (const token of ["--input", "--ring"]) {
    const ratio = contrast(token, "--background");
    assert.ok(ratio >= 3, `${token}: ${ratio.toFixed(2)}:1`);
  }
});
