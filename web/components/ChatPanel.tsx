"use client";
import { useCallback, useEffect, useState } from "react";
import type { ChatResult, Document } from "@/lib/api";
import { beginOperation, pendingOperations, reconcileOperation, sendOperation, operationError, type OperationResult } from "@/lib/operations";
import SourceView from "./SourceView";
import { scopedKey } from "@/lib/client-state";

const SOURCES_KEY = scopedKey("sources.v1");

export default function ChatPanel() {
  const [question, setQuestion] = useState("");
  const [result, setResult] = useState<ChatResult | null>(null);
  const [busy, setBusy] = useState(false);
  const [unresolved, setUnresolved] = useState(false);
  const [error, setError] = useState("");
  const [documents, setDocuments] = useState<Document[]>([]);
  const [selected, setSelected] = useState<number[]>([]);
  const [source, setSource] = useState<{ documentId: number; segmentId?: number } | null>(null);
  const closeSource = useCallback(() => setSource(null), []);
  const accept = useCallback((operation: OperationResult | null) => {
    setUnresolved(!operation);
    if (operation?.status === "succeeded") { setResult(operation.response); setError(""); }
    else setError(operationError(operation));
  }, []);

  const recover = useCallback(async (signal?: AbortSignal) => {
    const pending = pendingOperations().find(item => item.type === "chat");
    if (!pending) return;
    setBusy(true); setUnresolved(true);
    const state = await reconcileOperation(pending, signal);
    if (!signal?.aborted) { accept(state); setBusy(false); }
  }, [accept]);

  useEffect(() => {
    const controller = new AbortController();
    recover(controller.signal);
    return () => controller.abort();
  }, [recover]);

  useEffect(() => {
    let active = true;
    try { setSelected(JSON.parse(sessionStorage.getItem(SOURCES_KEY) || "[]")); } catch { /* Empty selection. */ }
    const load = async () => {
      try {
        const res = await fetch("/api/documents", { cache: "no-store" });
        if (!res.ok) throw new Error("Không đọc được danh sách nguồn. Hãy làm mới trạng thái.");
        const items: Document[] = await res.json();
        if (!active) return;
        const ready = items.filter(item => item.status === "ready");
        const available = new Set(ready.map(item => item.id));
        setDocuments(ready);
        setSelected(previous => previous.filter(id => available.has(id)));
        setResult(previous => previous ? { ...previous, citations: previous.citations.map(citation => available.has(citation.document_id) ? citation : { ...citation, available: false, excerpt: null }) } : previous);
      } catch (err) { if (active) setError(err instanceof Error ? err.message : "Không đọc được nguồn."); }
    };
    load(); window.addEventListener("documents-changed", load);
    return () => { active = false; window.removeEventListener("documents-changed", load); };
  }, []);

  function select(id: number, checked: boolean) {
    const next = checked ? [...selected, id] : selected.filter(item => item !== id);
    setSelected(next);
    try { sessionStorage.setItem(SOURCES_KEY, JSON.stringify(next)); } catch { /* Selection remains in memory. */ }
  }

  async function ask() {
    if (!question.trim() || busy || unresolved || !selected.length) return;
    setBusy(true); setError(""); setResult(null); setSource(null);
    try {
      const operation = beginOperation("chat");
      accept(await sendOperation(operation, "/api/proxy?target=chat", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ question, document_ids: selected }) }));
    } catch { setError("Không lưu được thông tin phục hồi trong trình duyệt. Kiểm tra quyền lưu trữ rồi thử lại."); }
    finally { setBusy(false); }
  }

  return <div className="panel">
    <h2>Hỏi đáp (RAG)</h2>
    <textarea aria-label="Câu hỏi về tài liệu" maxLength={2000} placeholder="Đặt câu hỏi dựa trên tài liệu đã chọn..." value={question} onChange={e => setQuestion(e.target.value)} disabled={busy || unresolved} />
    <fieldset className="source-picker" disabled={busy || unresolved}>
      <legend>Nguồn tra cứu</legend>
      {documents.length === 0 && <span className="meta">Chưa có tài liệu sẵn sàng.</span>}
      {documents.map(doc => <label key={doc.id}><input type="checkbox" checked={selected.includes(doc.id)} onChange={e => select(doc.id, e.target.checked)} /> {doc.filename}</label>)}
    </fieldset>
    <button onClick={ask} disabled={busy || unresolved || !question.trim() || !selected.length}>{busy ? "Đang xử lý / đối soát..." : "Hỏi"}</button>
    {unresolved && <button onClick={() => recover()} disabled={busy}>Kiểm tra kết quả đã gửi</button>}
    {busy && <p role="status" className="meta">Đang chờ kết quả. Reload sẽ tiếp tục đối soát cùng thao tác.</p>}
    {error && <p className="error" role="alert">{error}</p>}
    {result && <>
      <div className="answer">{result.status === "NoEvidence" ? "Không tìm thấy bằng chứng phù hợp trong tài liệu đã chọn." : result.answer}</div>
      <div className="sources">Nguồn: {result.sources.join(", ") || "(không có)"}</div>
      <ul className="citation-list">{result.citations.map(citation => <li key={citation.citation_id}>
        <button className="action-link" disabled={citation.available === false} onClick={() => setSource({ documentId: citation.document_id, segmentId: citation.source_segment_id })}>{citation.source} - {citation.locator.type} {citation.locator.value}</button>
        <p className="meta">{citation.available === false ? "Nguồn đã xóa hoặc không còn khả dụng; đây là câu trả lời lịch sử." : citation.excerpt}</p>
      </li>)}</ul>
      <div className="meta">{result.provider} / {result.model} | {result.latency_ms} ms</div>
    </>}
    {source && <SourceView {...source} onClose={closeSource} />}
  </div>;
}
