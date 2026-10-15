import { request } from '@playwright/test';

// Dừng toàn bộ lần chạy nếu API không ở chế độ fixture: E2E không được gọi provider AI thật.
export default async function globalSetup() {
  const api = process.env.E2E_API_URL || 'http://127.0.0.1:8107';
  const ctx = await request.newContext();
  try {
    const profile = await (await ctx.get(`${api}/system/profile`)).json();
    if (profile.mode !== 'fixture') {
      throw new Error(`E2E chỉ chạy khi API ở chế độ fixture, hiện tại: ${profile.mode}`);
    }
  } finally {
    await ctx.dispose();
  }
}
