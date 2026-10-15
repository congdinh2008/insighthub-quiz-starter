"""Create a small, identified recovery corpus in a fixture-only test runtime."""
import argparse
import json
import tempfile
import uuid
from pathlib import Path
from run_aev import CORPUS, call, upload


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--api-url', required=True)
    parser.add_argument('--output', default='reports/recovery-seed.json')
    args = parser.parse_args()
    code, raw, _ = call(args.api_url, '/system/profile')
    if code != 200 or json.loads(raw)['mode'] != 'fixture':
        raise SystemExit('Recovery seed requires an isolated fixture runtime.')
    documents = []
    for name in ('01_quy_trinh_vi.md', '02_operations_en.txt', '03_reference.pdf'):
        code, raw, _ = upload(args.api_url, CORPUS / name)
        body = json.loads(raw)
        assert code == 201 and body['status'] == 'ready', (name, code)
        documents.append(body['id'])
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / ('blank-' + uuid.uuid4().hex + '.txt')
        path.write_text(' \n\t')
        code, raw, _ = upload(args.api_url, path)
        body = json.loads(raw)
        assert code == 422 and body.get('document_id'), code
        failed = body['document_id']
    code, raw, _ = call(args.api_url, '/chat', 'POST', json.dumps({
        'question': 'Quy trình vận hành và khôi phục?', 'document_ids': documents,
    }).encode(), {'Content-Type': 'application/json', 'Idempotency-Key': 'recovery-' + uuid.uuid4().hex})
    assert code == 200 and json.loads(raw)['status'] == 'Answered', code
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps({'ready_documents': documents, 'failed_document': failed, 'chat': json.loads(raw)}, ensure_ascii=False, indent=2) + '\n')
    print(output)


if __name__ == '__main__':
    main()
