"use client";
// Theo dõi trạng thái một tác vụ AI cho tới khi kết thúc (AI Job scaffold learner-r1.3).
// Dùng khi tải lại trang hoặc quay lại Notebook trong lúc tác vụ đang chạy. Chỉ đọc, không tạo tác vụ mới.
import { useEffect, useState } from "react";
import type { ApiError } from "./api-error.ts";
import { getJob, TERMINAL, type AiJob } from "./jobs.ts";

export function useJobStatus(jobId: string | null, { intervalMs = 1500, maxIntervalMs = 5000 } = {}) {
  const [job, setJob] = useState<AiJob | null>(null);
  const [error, setError] = useState<ApiError | null>(null);

  useEffect(() => {
    if (!jobId) return;
    const controller = new AbortController();
    let delay = intervalMs;
    let timer: ReturnType<typeof setTimeout> | undefined;
    const poll = async () => {
      const result = await getJob(jobId, controller.signal);
      if (controller.signal.aborted) return;
      if (result.ok) {
        setJob(result.job);
        setError(null);
        if (TERMINAL.has(result.job.status)) return;
      } else {
        setError(result.error);
        // 401, 404: hết phiên hoặc không còn quyền đọc. Dừng, để UI hướng dẫn đăng nhập lại hoặc quay về danh sách.
        if (result.error.status === 401 || result.error.status === 404) return;
      }
      delay = Math.min(maxIntervalMs, Math.round(delay * 1.5));
      timer = setTimeout(poll, delay);
    };
    poll();
    return () => { controller.abort(); if (timer) clearTimeout(timer); };
  }, [jobId, intervalMs, maxIntervalMs]);

  return { job, error, done: !!job && TERMINAL.has(job.status) };
}
