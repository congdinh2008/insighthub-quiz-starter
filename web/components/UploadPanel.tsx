"use client";
import { useCallback, useEffect, useState } from "react";
import type { Document } from "@/lib/api";
import { documentError } from "@/lib/errors";
import { beginOperation, pendingOperations, reconcileOperation, sendOperation, operationError, type OperationType, type OperationResult } from "@/lib/operations";
import SourceView from "./SourceView";
type Detail = Document & { attempts: { id: number; status: string; error_code?: string | null }[] };

export default function UploadPanel({ initial, initialError = "" }: { initial: Document[]; initialError?: string }) {
  const [docs, setDocs] = useState(initial);
  const [busy, setBusy] = useState(false);
  const [unresolved, setUnresolved] = useState(false);
  const [error, setError] = useState(initialError);
  const [detail, setDetail] = useState<Detail | null>(null);
  const [sourceId, setSourceId] = useState<number | null>(null);
  const closeSource = useCallback(() => setSourceId(null), []);
  const refresh = useCallback(async () => {
    const res = await fetch("/api/documents", { cache: "no-store", signal: AbortSignal.timeout(10000) });
    if (!res.ok) throw new Error("Không đọc được trạng thái tài liệu.");
    setDocs(await res.json());
    window.dispatchEvent(new Event("documents-changed"));
  }, []);
  const accept = useCallback((state: OperationResult | null) => {
    setUnresolved(!state);
    setError(state?.status === "succeeded" ? "" : operationError(state));
  }, []);
  const recover = useCallback(async (signal?: AbortSignal) => {
    const items = pendingOperations().filter(item => item.type !== "chat");
    if (!items.length) return;
    setBusy(true); setUnresolved(true);
    for (const item of items) {
      const state = await reconcileOperation(item, signal);
      if (signal?.aborted) return;
      accept(state);
      if (!state) break;
    }
    await refresh().catch(() => {});
    if (!signal?.aborted) setBusy(false);
  }, [accept, refresh]);
  useEffect(() => { const controller = new AbortController(); recover(controller.signal); return () => controller.abort(); }, [recover]);
  const pending = docs.some(doc => doc.status === "pending");
  useEffect(() => {
    if (!pending) return;
    const timer = setInterval(() => refresh().catch(() => {}), 3000);
    return () => clearInterval(timer);
  }, [pending, refresh]);

  async function mutate(type: OperationType, id?: number, file?: File) {
    if (busy || unresolved) return;
    if (file && (file.size > 10 * 1024 * 1024 || !/\.(txt|md|pdf)$/i.test(file.name))) { setError("Chọn file TXT, MD hoặc PDF không quá 10 MiB."); return; }
    if (type === "delete" && !window.confirm("Xóa tài liệu và toàn bộ nguồn/chỉ mục liên quan?")) return;
    setBusy(true); setError(""); setDetail(null); setSourceId(null);
    try {
      const operation = beginOperation(type, id);
      const body = file ? new FormData() : undefined;
      if (file) body!.append("file", file);
      const url = type === "upload" ? "/api/proxy?target=upload" : `/api/documents/${id}${type === "retry" ? "/retry" : ""}`;
      accept(await sendOperation(operation, url, { method: type === "delete" ? "DELETE" : "POST", body }));
      await refresh();
    } catch (err) { setError(err instanceof Error ? err.message : "Không gửi được thao tác."); setUnresolved(pendingOperations().some(item => item.type !== "chat")); }
    finally { setBusy(false); }
  }
  async function showDetail(id: number) {
    try {
      const res = await fetch(`/api/documents/${id}`, { cache: "no-store" });
      if (!res.ok) throw new Error("Không đọc được chi tiết tài liệu.");
      setDetail(await res.json());
    } catch (err) { setError(err instanceof Error ? err.message : "Không đọc được chi tiết."); }
  }
  return <div className="panel">
    <h2>Tài liệu</h2>
    <input type="file" aria-label="Chọn tài liệu .txt, .md hoặc .pdf" accept=".txt,.md,.pdf" disabled={busy || unresolved} onChange={e => { const file = e.target.files?.[0]; if (file) mutate("upload", undefined, file); e.target.value = ""; }} />
    {(busy || pending) && <p className="meta" role="status">Đang xử lý / đối soát. Reload sẽ tiếp tục kiểm tra thao tác đã gửi.</p>}
    <button onClick={() => refresh().catch(err => setError(err.message))} disabled={busy}>Làm mới trạng thái</button>
    {unresolved && <button onClick={() => recover()} disabled={busy}>Kiểm tra thao tác đã gửi</button>}
    {error && <p className="error" role="alert">{error}</p>}
    <ul className="doc-list" style={{ marginTop: "1rem" }}>
      {!docs.length && <li className="meta">Chưa có tài liệu. Upload TXT / MD / PDF.</li>}
      {docs.map(doc => <li key={doc.id} className="doc-item">
        <span>{doc.filename} <span className="meta">({doc.chunk_count} chunks)</span></span>
        <span className={`badge ${doc.status}`}>{doc.status === "ready" ? "Sẵn sàng" : doc.status === "failed" ? "Thất bại" : "Đang xử lý"}</span>
        <span className="document-actions">
          <button className="action-link" onClick={() => showDetail(doc.id)}>Chi tiết</button>
          {doc.status === "ready" && <button className="action-link" onClick={() => setSourceId(doc.id)}>Xem nguồn</button>}
          <button className="action-link" onClick={() => mutate("delete", doc.id)} disabled={busy || unresolved}>Xóa</button>
        </span>
        {doc.status === "failed" && <label className="retry-file">Thử lại với đúng tệp {doc.filename}<input type="file" aria-label={`Thử lại ${doc.filename}`} accept=".txt,.md,.pdf" disabled={busy || unresolved} onChange={e => { const file = e.target.files?.[0]; if (file) mutate("retry", doc.id, file); e.target.value = ""; }} /></label>}
        {doc.error_code && <span className="error">{documentError(doc.error_code)}</span>}
        {detail?.id === doc.id && <div className="document-detail"><strong>Thông tin và lịch sử xử lý</strong>
          <p>{detail.mime_type || "Chưa xác định định dạng"} | {detail.size_bytes ?? 0} bytes | Cập nhật: {detail.updated_at || detail.created_at}</p>
          <ul>{detail.attempts.map(attempt => <li key={attempt.id}>#{attempt.id}: {attempt.status}{attempt.error_code ? ` - ${documentError(attempt.error_code)}` : ""}</li>)}</ul>
          <button className="action-link" onClick={() => setDetail(null)}>Đóng chi tiết</button>
        </div>}
      </li>)}
    </ul>
    {sourceId !== null && <SourceView documentId={sourceId} onClose={closeSource} />}
  </div>;
}
