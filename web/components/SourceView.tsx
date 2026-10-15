"use client";
import { useEffect, useState } from "react";
export default function SourceView({ documentId, segmentId, onClose }: { documentId: number; segmentId?: number; onClose: () => void }) {
  const [source, setSource] = useState<{ filename: string; content: string; locator?: { type: string; value: string } } | null>(null);
  const [error, setError] = useState("");
  useEffect(() => {
    const controller = new AbortController();
    setSource(null); setError("");
    fetch(`/api/documents/${documentId}/source${segmentId ? `?segment_id=${segmentId}` : ""}`, { cache: "no-store", signal: controller.signal })
      .then(async res => { if (!res.ok) throw new Error("Nguồn không còn khả dụng."); return res.json(); })
      .then(data => { if (!controller.signal.aborted) setSource(data); })
      .catch(err => { if (!controller.signal.aborted) setError(err.message); });
    const invalidate = () => { controller.abort(); setSource(null); onClose(); };
    const escape = (event: KeyboardEvent) => { if (event.key === "Escape") invalidate(); };
    window.addEventListener("documents-changed", invalidate);
    window.addEventListener("keydown", escape);
    return () => { controller.abort(); window.removeEventListener("documents-changed", invalidate); window.removeEventListener("keydown", escape); };
  }, [documentId, segmentId, onClose]);
  return <section className="source-view" aria-label="Nội dung nguồn" tabIndex={0}>
    <strong>{source?.filename || "Nguồn tài liệu"}{source?.locator ? ` - ${source.locator.type} ${source.locator.value}` : " - toàn văn"}</strong>
    <button className="action-link" onClick={onClose}>Đóng nguồn</button>
    {error ? <p role="alert">{error}</p> : source ? <pre>{source.content}</pre> : <p role="status">Đang mở nguồn...</p>}
  </section>;
}
