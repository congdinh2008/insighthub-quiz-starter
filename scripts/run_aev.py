"""Run release RAG evaluation against an isolated real-provider runtime."""

import argparse
import hashlib
import json
import time
import unicodedata
import uuid
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
CORPUS = ROOT / "evaluation" / "corpus"


def call(base, path, method="GET", data=None, headers=None, timeout=130):
    request = Request(base + path, data=data, method=method, headers=headers or {})
    try:
        with urlopen(request, timeout=timeout) as response:
            return response.status, response.read(), dict(response.headers)
    except HTTPError as exc:
        return exc.code, exc.read(), dict(exc.headers)


def upload(base: str, path: Path, headers: dict | None = None):
    boundary = "----aev" + uuid.uuid4().hex
    mime = "application/pdf" if path.suffix == ".pdf" else "text/plain"
    body = (
        f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="{path.name}"\r\n'
        f"Content-Type: {mime}\r\n\r\n"
    ).encode() + path.read_bytes() + f"\r\n--{boundary}--\r\n".encode()
    return call(
        base,
        "/documents",
        "POST",
        body,
        {
            "Content-Type": "multipart/form-data; boundary=" + boundary,
            "Idempotency-Key": "aev-upload-" + uuid.uuid4().hex,
            **(headers or {}),
        },
    )


def normalized(value: str) -> str:
    return unicodedata.normalize("NFC", value).casefold()


def check_response(case, response, status, documents, read_source):
    """Structural/source oracle. Semantic support still requires claim review."""
    answer=response.get("answer") or ""
    claims=response.get("claims") or []
    citations=response.get("citations") or []
    allowed={documents[name] for name in case["sources"]}
    citation_ids={item.get("citation_id") for item in citations}
    answered=case["expected_status"]=="Answered"
    source_checks=[]
    for citation in citations:
        code,source=read_source(citation)
        excerpt=citation.get("excerpt") or ""
        content=source.get("content") or ""
        source_checks.append({
            "citation_id":citation.get("citation_id"),"source":citation.get("source"),"http_status":code,
            "locator":source.get("locator"),"locator_matches":source.get("locator")==citation.get("locator"),
            "excerpt_matches":bool(excerpt) and " ".join(excerpt.split()) in " ".join(content.split()),
            "source_sha256":hashlib.sha256(content.encode()).hexdigest(),
            "expected_facts_present":{fact:normalized(fact) in normalized(content) for oracle in case.get("expected_evidence",[]) if oracle["source"]==citation.get("source") for fact in oracle["required_facts"]},
        })
    checks={
        "http_200":status==200,"status":response.get("status")==case["expected_status"],
        "concepts":all(normalized(term) in normalized(answer) for term in case.get("must_include_concepts",[])),
        "forbidden":all(normalized(term) not in normalized(answer) for term in case.get("forbidden",[])),
        "citation_scope":all(c.get("document_id") in allowed for c in citations),
        "citation_presence":bool(citations) if answered else not citations,
        "claim_references":bool(claims) and all(isinstance(c,dict) and c.get("text") and c.get("citation_ids") and set(c["citation_ids"])<=citation_ids for c in claims) if answered else not claims and not answer,
        "source_links":all(c["http_status"]==200 and c["locator_matches"] and c["excerpt_matches"] for c in source_checks),
        "expected_sources":all(any(c["source"]==oracle["source"] and c["locator"]==oracle["locator"] and all(c["expected_facts_present"].get(fact,False) for fact in oracle["required_facts"]) for c in source_checks) for oracle in case.get("expected_evidence",[])),
        "deadline":response.get("latency_ms",float('inf')) <= 60000,
    }
    return checks,source_checks


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--api-url",default="http://127.0.0.1:8107")
    parser.add_argument("--output")
    args=parser.parse_args(); base=args.api_url.rstrip("/")
    output=Path(args.output) if args.output else ROOT/"reports/evaluation"/f"AEV-01-{datetime.now().strftime('%Y%m%d-%H%M%S')}.json"
    output.parent.mkdir(parents=True,exist_ok=True)
    status,raw,_=call(base,"/system/profile")
    if status != 200: raise SystemExit("Runtime profile unavailable")
    profile=json.loads(raw)
    if profile["mode"] != "real": raise SystemExit("AEV requires RAG_MODE=real")
    spec=json.loads((ROOT/"evaluation/AEV-01.json").read_text())
    documents,created,results,uploads,hashes={ },[],[],[],{}
    cleanup=[]
    artifact={"schema_version":2,"created_at":datetime.now(timezone.utc).isoformat(),"profile":profile,"spec_version":spec["version"],"corpus_sha256":hashes,"uploads":uploads,"results":results,"cleanup":cleanup,"semantic_review":"pending"}
    try:
        for name in sorted({name for case in spec["cases"] for name in case["sources"]}):
            path=CORPUS/name; hashes[name]=hashlib.sha256(path.read_bytes()).hexdigest()
            start=time.perf_counter(); status,raw,_=upload(base,path); response=json.loads(raw)
            uploads.append({"source":name,"http_status":status,"latency_ms":int((time.perf_counter()-start)*1000),"document":response})
            identifier=response.get("id") or response.get("document_id")
            if identifier and not response.get("deduplicated",False): created.append(identifier)
            if status!=201 or response.get("status")!="ready": raise RuntimeError(f"Upload failed: {name}, HTTP {status}")
            documents[name]=identifier
        def read_source(citation):
            code,raw,_=call(base,f"/documents/{citation['document_id']}/source?segment_id={citation['source_segment_id']}")
            return code,json.loads(raw)
        for case in spec["cases"]:
            for run in range(1,case.get("repeat",1)+1):
                payload=json.dumps({"question":case["question"],"document_ids":[documents[name] for name in case["sources"]]},ensure_ascii=False).encode()
                start=time.perf_counter()
                status,raw,headers=call(base,"/chat","POST",payload,{"Content-Type":"application/json","Idempotency-Key":"aev-chat-"+uuid.uuid4().hex})
                elapsed=int((time.perf_counter()-start)*1000); response=json.loads(raw)
                checks,source_checks=check_response(case,response,status,documents,read_source)
                results.append({"case_id":case["id"],"run":run,"supplement":case.get("supplement",False),"passed":all(checks.values()),"checks":checks,"source_checks":source_checks,"http_status":status,"latency_ms":elapsed,"request_id":next((v for k,v in headers.items() if k.lower()=="x-request-id"),None),"response":response,"expected_evidence":case["expected_evidence"],"semantic_review":{"verdict":"pending","claims":[{"text":c["text"],"citation_ids":c["citation_ids"],"supported":None,"reason":""} for c in response.get("claims",[])]}})
                print(f"{case['id']} run={run} HTTP={status} checks={'PASS' if all(checks.values()) else 'FAIL'}",flush=True)
    except Exception as exc:
        artifact['run_error']=str(exc) if isinstance(exc,RuntimeError) else type(exc).__name__
    finally:
        for identifier in created:
            status,_,_=call(base,f"/documents/{identifier}","DELETE",headers={"Idempotency-Key":"aev-delete-"+uuid.uuid4().hex})
            cleanup.append({"document_id":identifier,"http_status":status})
        expected=sum(case.get('repeat',1) for case in spec['cases'])
        passed=sum(r['passed'] for r in results)
        artifact['summary']={"passed":passed,"total":len(results),"expected":expected,"success":passed==expected and all(c['http_status']==204 for c in cleanup)}
        output.write_text(json.dumps(artifact,ensure_ascii=False,indent=2)+"\n")
        print(output); print(f"PASS={passed}/{expected}; semantic review pending")
    if not artifact['summary']['success']: raise SystemExit(1)


if __name__ == "__main__":
    main()
