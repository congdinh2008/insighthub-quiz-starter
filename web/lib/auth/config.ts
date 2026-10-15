// Auth scaffold (learner-r1.3): cấu hình Better Auth dùng chung cho server Next.js và script migration.
// Đây là PHẦN NỀN (plumbing). Chính sách của SRS (độ dài mật khẩu LIM-01, bắt buộc xác minh email,
// thời hạn phiên LIM-07, nội dung email EML-001) là việc của học viên ở tầng Core. Khôi phục, đặt lại,
// đổi mật khẩu, hồ sơ và EML-002 là Extended (Requirements mục 1.4).
// Xem docs/Auth_Integration_Guide.md mục "Auth scaffold".
import type { BetterAuthOptions } from "better-auth";
import { sendResetPasswordEmail, sendVerificationEmail } from "./email";

// Endpoint của thư viện cho các chức năng tầng Extended (khôi phục, đặt lại, đổi mật khẩu, tái xác thực,
// sửa hồ sơ). Starter tắt sẵn để chúng không chạy theo mặc định thư viện thay vì theo SRS khi học viên
// chưa làm Extended. Khi làm chức năng nào, xóa đường dẫn tương ứng khỏi danh sách và cấu hình chính sách
// theo SRS (LIM-07, LIM-19), ghi trong fit-gap của Auth Integration Guide.
export const extendedAuthPaths = [
  "/request-password-reset",
  "/reset-password",
  "/change-password",
  "/verify-password",
  "/update-user",
] as const;

const snake = {
  createdAt: "created_at",
  updatedAt: "updated_at",
} as const;

export const authTables = {
  user: "auth_user",
  session: "auth_session",
  account: "auth_account",
  verification: "auth_verification",
} as const;

export function authOptions(database: BetterAuthOptions["database"]): BetterAuthOptions {
  const webOrigins = (process.env.MUTATION_ALLOWED_ORIGINS || "http://localhost:3107,http://127.0.0.1:3107")
    .split(",").map(value => value.trim()).filter(Boolean);
  return {
    appName: "InsightHub",
    baseURL: process.env.BETTER_AUTH_URL || "http://localhost:3107",
    secret: process.env.BETTER_AUTH_SECRET,
    database,
    trustedOrigins: webOrigins,
    disabledPaths: [...extendedAuthPaths],
    user: {
      modelName: authTables.user,
      fields: { emailVerified: "email_verified", ...snake },
    },
    session: {
      modelName: authTables.session,
      fields: { expiresAt: "expires_at", ipAddress: "ip_address", userAgent: "user_agent", userId: "user_id", ...snake },
    },
    account: {
      modelName: authTables.account,
      fields: {
        accountId: "account_id", providerId: "provider_id", userId: "user_id", accessToken: "access_token",
        refreshToken: "refresh_token", idToken: "id_token", accessTokenExpiresAt: "access_token_expires_at",
        refreshTokenExpiresAt: "refresh_token_expires_at", ...snake,
      },
    },
    verification: {
      modelName: authTables.verification,
      fields: { expiresAt: "expires_at", ...snake },
    },
    emailAndPassword: {
      enabled: true,
      // Giá trị mặc định của thư viện. Học viên đối chiếu LIM-01 và cấu hình lại (fit-gap LR-09).
      requireEmailVerification: false,
      sendResetPassword: sendResetPasswordEmail,
    },
    emailVerification: {
      sendVerificationEmail,
    },
    advanced: {
      cookiePrefix: "insighthub",
      database: { generateId: "uuid" },
    },
  };
}
