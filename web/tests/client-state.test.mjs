import test from 'node:test';
import assert from 'node:assert/strict';
import { clearClientState, scopedKey } from '../lib/client-state.ts';
function storage() { const map = new Map(); return { get length() { return map.size; }, key: i => [...map.keys()][i] ?? null, getItem: k => map.get(k) ?? null, setItem: (k, v) => map.set(k, String(v)), removeItem: k => map.delete(k) }; }
test('scoped keys separate users and logout clears every InsightHub key', () => {
  globalThis.sessionStorage = storage(); globalThis.localStorage = storage();
  assert.equal(scopedKey('sources.v1', 'user-a'), 'insighthub.user-a.sources.v1');
  assert.equal(scopedKey('pending.v1'), 'insighthub.anon.pending.v1');
  sessionStorage.setItem(scopedKey('sources.v1', 'user-a'), '[1]');
  localStorage.setItem(scopedKey('draft', 'user-a'), 'x');
  sessionStorage.setItem('other-app', 'keep');
  clearClientState();
  assert.equal(sessionStorage.getItem('insighthub.user-a.sources.v1'), null);
  assert.equal(localStorage.getItem('insighthub.user-a.draft'), null);
  assert.equal(sessionStorage.getItem('other-app'), 'keep');
});
