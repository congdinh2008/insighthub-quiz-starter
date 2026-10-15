// Trạng thái phía trình duyệt của InsightHub luôn dùng tiền tố "insighthub." và gắn với người dùng.
// Khi đổi tài khoản hoặc đăng xuất, xóa toàn bộ để tài khoản sau không thấy dữ liệu của tài khoản trước.
const PREFIX = "insighthub.";

export function scopedKey(name: string, userId?: string | null): string {
  return `${PREFIX}${userId || "anon"}.${name}`;
}

function clearStorage(storage: Storage | undefined): void {
  if (!storage) return;
  const keys: string[] = [];
  for (let index = 0; index < storage.length; index += 1) {
    const key = storage.key(index);
    if (key?.startsWith(PREFIX)) keys.push(key);
  }
  keys.forEach(key => storage.removeItem(key));
}

export function clearClientState(): void {
  try { clearStorage(globalThis.sessionStorage); } catch { /* Storage có thể bị chặn. */ }
  try { clearStorage(globalThis.localStorage); } catch { /* Storage có thể bị chặn. */ }
}
