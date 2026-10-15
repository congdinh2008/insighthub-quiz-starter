// Điểm nối email của Auth scaffold. Hạ tầng gửi thư (SMTP, Mailpit) có sẵn ở lib/auth/mailer.ts.
// Trigger, nội dung, link và trạng thái gửi của EML-001 (Core) là việc của học viên (LR-12, LR-14).
// EML-002 chỉ cần khi làm khôi phục mật khẩu (Extended); endpoint tương ứng đang tắt trong config.ts.
// Hai hàm dưới đây cố ý báo lỗi cho tới khi học viên triển khai: không gửi email giả để "đạt".
type User = { id: string; email: string; name: string };

export async function sendVerificationEmail(data: { user: User; url: string; token: string }): Promise<void> {
  void data;
  throw new Error("EML-001 chưa được triển khai. Xem Requirements mục 16.2 (Extended) và SRS mục 3.5.4.");
}

export async function sendResetPasswordEmail(data: { user: User; url: string; token: string }): Promise<void> {
  void data;
  throw new Error("EML-002 chưa được triển khai. Xem Requirements mục 16.2 (Extended) và SRS mục 3.5.4.");
}
