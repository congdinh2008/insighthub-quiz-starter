import { defineConfig } from '@playwright/test';

// E2E theo hành trình bằng Playwright Test (TG-08). Chạy trên stack chế độ fixture, cùng namespace với tests/e2e.mjs.
// retries: 0 vì retry chỉ dùng để phát hiện flaky test, không để CI pass (KC buổi 8 mục 4.3).
// Mặc định Microsoft Edge, cùng trình duyệt với tests/e2e.mjs. Đổi bằng E2E_BROWSER=chrome|chromium.
const browserChannel = process.env.E2E_BROWSER || 'msedge';

export default defineConfig({
  testDir: './e2e',
  retries: 0,
  failOnFlakyTests: !!process.env.CI,
  forbidOnly: !!process.env.CI,
  globalSetup: './e2e/global-setup.ts',
  reporter: [['list'], ['html', { open: 'never' }]],
  use: {
    baseURL: process.env.E2E_WEB_URL || 'http://127.0.0.1:3107',
    trace: 'retain-on-failure',
  },
  projects: [
    { name: 'desktop', use: { browserName: 'chromium', channel: browserChannel, viewport: { width: 1440, height: 900 } } },
    { name: 'mobile', use: { browserName: 'chromium', channel: browserChannel, viewport: { width: 390, height: 844 } } },
  ],
});
