import { test, expect } from '@playwright/test';

// Ví dụ tối thiểu để kiểm cấu hình. E2E theo hành trình của bài làm do học viên viết (LR-20, LR-21).
test('trang chính mở được ở chế độ fixture', async ({ page }) => {
  await page.goto('/');
  await expect(page.getByRole('heading', { name: 'Hỏi đáp (RAG)' })).toBeVisible();
});
