"""Code graders for InsightHub LLM features (Requirements LR-23, Kit K9).

Graders check what a machine can check: status, schema/structure, length,
citation scope and Quiz shape. They never decide that content is semantically
correct; every run keeps `semantic_review: pending` for the human reviewer.

All graders take a *normalized output* produced by an adapter (see adapters.py):
{
  "status": "Answered|NoEvidence|Failed|Succeeded",
  "text": "...",                                    # answer or summary body
  "claims": [{"text": "...", "citation_ids": ["c1"]}],
  "citations": [{"citation_id": "c1", "document_id": "...", "source": "file.md"}],
  "quiz": {"questions": [{"text": "...", "options": ["a","b","c","d"],
                           "answer_index": 0, "explanation": "...", "citation_ids": ["c1"]}]},
  "meta": {"model": "...", "prompt_version": "...", "schema_version": "...", "latency_ms": 0, "usage": {}}
}
Each grader returns (passed: bool, detail: str).
"""
import re
import unicodedata

SUMMARY_WORDS = {"short": (150, 250), "detailed": (400, 600)}


def _norm(text):
    return unicodedata.normalize("NFC", text or "").casefold()


def words(text):
    return len(re.findall(r"\w+", text or "", re.UNICODE))


def status(case, out):
    expected = case["expected_status"]
    return out.get("status") == expected, f"expected {expected}, got {out.get('status')}"


def citation_scope(case, out, allowed_document_ids):
    bad = [c.get("citation_id") for c in out.get("citations", []) if c.get("document_id") not in allowed_document_ids]
    return not bad, f"citations outside selected sources: {bad}" if bad else "all citations in scope"


def claims_reference_citations(case, out):
    """Grounded outputs must cite; NoEvidence/Failed outputs must not carry claims or citations."""
    if out.get("status") in ("NoEvidence", "Failed"):
        ok = not out.get("claims") and not out.get("citations")
        return ok, "no claims/citations on NoEvidence/Failed" if ok else "NoEvidence/Failed must not carry claims or citations"
    ids = {c.get("citation_id") for c in out.get("citations", [])}
    claims = out.get("claims", [])
    bad = [c.get("text", "")[:40] for c in claims if not c.get("citation_ids") or not set(c["citation_ids"]) <= ids]
    if not claims:
        return False, "grounded output has no claims"
    return not bad, f"claims without valid citation: {bad}" if bad else f"{len(claims)} claims cite known citations"


def forbidden_terms(case, out):
    found = [t for t in case.get("forbidden", []) if _norm(t) in _norm(out.get("text"))]
    return not found, f"forbidden terms present: {found}" if found else "no forbidden terms"


def summary_length(case, out):
    low, high = SUMMARY_WORDS[case["config"]["length"]]
    n = words(out.get("text"))
    return low <= n <= high, f"{n} words, expected {low}-{high}"


def quiz_structure(case, out):
    questions = (out.get("quiz") or {}).get("questions", [])
    expected = case["config"]["question_count"]
    problems = []
    if len(questions) != expected:
        problems.append(f"{len(questions)} questions, expected {expected}")
    seen = set()
    for i, q in enumerate(questions, 1):
        options = q.get("options") or []
        if len(options) != 4 or len({_norm(o) for o in options}) != 4:
            problems.append(f"Q{i}: need 4 distinct options")
        if not isinstance(q.get("answer_index"), int) or not 0 <= q["answer_index"] < len(options):
            problems.append(f"Q{i}: answer_index outside options")
        if not (q.get("explanation") or "").strip():
            problems.append(f"Q{i}: missing explanation")
        if not q.get("citation_ids"):
            problems.append(f"Q{i}: missing citation")
        key = _norm(q.get("text"))
        if key in seen:
            problems.append(f"Q{i}: duplicate question")
        seen.add(key)
    return not problems, "; ".join(problems) or f"{len(questions)} well-formed questions"


def expected_points_hint(case, out):
    """Keyword hint only. Always needs human review of every claim and question."""
    text = _norm(out.get("text")) + " " + _norm(str(out.get("quiz")))
    missing = [p["text"] for p in case.get("expected_points", []) if not all(_norm(k) in text for k in p.get("keywords", []))]
    return True, ("keyword hints missing: " + "; ".join(missing)) if missing else "keyword hints present (not a semantic verdict)"


GRADERS = {
    "chat": [status, citation_scope, claims_reference_citations, forbidden_terms, expected_points_hint],
    "summary": [status, citation_scope, claims_reference_citations, summary_length, forbidden_terms, expected_points_hint],
    "quiz": [status, citation_scope, quiz_structure, expected_points_hint],
}


def grade(case, out, allowed_document_ids):
    results = {}
    for grader in GRADERS[case["tool"]]:
        if grader is citation_scope:
            ok, detail = grader(case, out, allowed_document_ids)
        elif grader in (summary_length, quiz_structure) and case["expected_status"] != "Succeeded":
            continue
        else:
            ok, detail = grader(case, out)
        results[grader.__name__] = {"passed": ok, "detail": detail}
    return all(r["passed"] for r in results.values()), results
