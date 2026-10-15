// Hạ tầng gửi thư cho phía web (Better Auth chạy trong Next.js). Mặc định trỏ tới Mailpit (make mail-up).
// Không log nội dung thư, link hay token.
import nodemailer, { type Transporter } from "nodemailer";

let transport: Transporter | null = null;

function getTransport(): Transporter {
  if (!transport) {
    transport = nodemailer.createTransport({
      host: process.env.SMTP_HOST || "127.0.0.1",
      port: Number(process.env.SMTP_PORT || 1025),
      secure: process.env.SMTP_SECURE === "true",
      auth: process.env.SMTP_USER ? { user: process.env.SMTP_USER, pass: process.env.SMTP_PASSWORD || "" } : undefined,
    });
  }
  return transport;
}

export async function sendMail(message: { to: string; subject: string; text: string; html?: string }): Promise<{ accepted: boolean }> {
  const info = await getTransport().sendMail({ from: process.env.MAIL_FROM || "InsightHub <no-reply@insighthub.local>", ...message });
  // Dịch vụ chấp nhận gửi chưa chứng minh người dùng đã nhận thư (Requirements mục 16.2).
  return { accepted: (info.accepted?.length ?? 0) > 0 };
}
