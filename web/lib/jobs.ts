// Phía trình duyệt: gửi tác vụ AI và đối soát trạng thái (AI Job scaffold learner-r1.3).
// Quy tắc mục 3.3.2: lưu idempotency key TRƯỚC khi gửi; mất kết nối thì đối soát hoặc gửi lại CÙNG key,
// không tự tạo key mới. Key xóa khi tác vụ kết thúc. Khóa lưu gắn người dùng (lib/client-state.ts).
import { parseApiError, type ApiError } from "./api-error.ts";
import { scopedKey } from "./client-state.ts";

export type JobStatus = "Processing" | "Succeeded" | "NoEvidence" | "Failed";
export type AiJob = {
  id: string;
  job_type: string;
  notebook_id: string | null;
  status: JobStatus;
  error_code: string | null;
  accepted_at: string;
  deadline_at: string;
  finished_at: string | null;
  result_ref: string | null;
  retry_of: string | null;
};
export type PendingJob = { jobType: string; key: string; url: string; body: string; startedAt: number; jobId?: string };
export type JobResult = { ok: true; job: AiJob } | { ok: false; error: ApiError };

// Chưa biết API đã tiếp nhận hay chưa: giữ key để đối soát, không gửi key mới.
const UNCERTAIN = new Set(["proxy_timeout", "network_error", "api_unavailable"]);
export const TERMINAL: ReadonlySet<JobStatus> = new Set(["Succeeded", "NoEvidence", "Failed"]);
const storageKey = (userId?: string | null) => scopedKey("jobs.pending.v1", userId);

function storage(): Storage | undefined {
  try { return globalThis.sessionStorage; } catch { return undefined; }
}

export function pendingJobs(userId?: string | null): PendingJob[] {
  try {
    const values = JSON.parse(storage()?.getItem(storageKey(userId)) || "[]");
    return Array.isArray(values) ? values.filter(v => v && typeof v.key === "string" && typeof v.url === "string" && typeof v.jobType === "string") : [];
  } catch { return []; }
}

function savePending(items: PendingJob[], userId?: string | null) {
  try { storage()?.setItem(storageKey(userId), JSON.stringify(items)); } catch { /* Storage bị chặn: vẫn gửi được, chỉ mất khả năng khôi phục khi tải lại trang. */ }
}

export function forgetJob(key: string, userId?: string | null) {
  savePending(pendingJobs(userId).filter(item => item.key !== key), userId);
}

function rememberJob(item: PendingJob, userId?: string | null) {
  savePending([...pendingJobs(userId).filter(other => other.key !== item.key), item], userId);
}

async function toResult(res: Response): Promise<JobResult> {
  const payload = await res.json().catch(() => ({}));
  return res.ok ? { ok: true, job: payload as AiJob } : { ok: false, error: parseApiError(res.status, payload, res.headers) };
}

// Gửi tác vụ mới hoặc gửi lại tác vụ đang chờ (truyền `pending` để dùng lại đúng key và body).
export async function startJob(
  jobType: string, url: string, body: unknown,
  options: { userId?: string | null; pending?: PendingJob; signal?: AbortSignal } = {},
): Promise<JobResult> {
  const item: PendingJob = options.pending || { jobType, key: crypto.randomUUID(), url, body: JSON.stringify(body), startedAt: Date.now() };
  rememberJob(item, options.userId);
  try {
    const res = await fetch(item.url, {
      method: "POST", body: item.body, cache: "no-store", signal: options.signal,
      headers: { "Content-Type": "application/json", "Idempotency-Key": item.key },
    });
    const result = await toResult(res);
    if (result.ok) {
      if (TERMINAL.has(result.job.status)) forgetJob(item.key, options.userId);
      else rememberJob({ ...item, jobId: result.job.id }, options.userId);
    } else if (!UNCERTAIN.has(result.error.code) && !result.error.code.startsWith("http_5")) {
      // API đã trả mã lỗi xác định (quota, xung đột, dữ liệu sai, tác vụ thất bại): bỏ key.
      forgetJob(item.key, options.userId);
    }
    return result;
  } catch {
    return { ok: false, error: parseApiError(0, {}) };
  }
}

export async function getJob(jobId: string, signal?: AbortSignal): Promise<JobResult> {
  try {
    return await toResult(await fetch(`/api/ai-jobs/${encodeURIComponent(jobId)}`, { cache: "no-store", signal }));
  } catch {
    return { ok: false, error: parseApiError(0, {}) };
  }
}

export async function getJobByKey(jobType: string, key: string, signal?: AbortSignal): Promise<JobResult> {
  try {
    return await toResult(await fetch(`/api/ai-jobs/by-key/${encodeURIComponent(jobType)}/${encodeURIComponent(key)}`, { cache: "no-store", signal }));
  } catch {
    return { ok: false, error: parseApiError(0, {}) };
  }
}
