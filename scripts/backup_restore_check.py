"""Verify a populated backup by content fingerprints and restored application reads."""
import argparse
import hashlib
import json
import os
import re
import subprocess
import uuid
from datetime import datetime, timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
TABLES=('schema_migrations','embedding_index','documents','document_sources','source_segments','chunks','ingestion_attempts','operation_records')
# Extension point: learners add their own tables (users, notebooks, notes...) via
# --extra-tables a,b or BACKUP_EXTRA_TABLES=a,b. Defaults stay the Starter tables.
EXTRA_TABLES_ENV='BACKUP_EXTRA_TABLES'
TABLE_NAME=re.compile(r'^[a-z_][a-z0-9_]{0,62}(\.[a-z_][a-z0-9_]{0,62})?$')


def resolve_tables(extra=None, environ=None):
    """Starter tables plus validated extra tables, in order and without duplicates."""
    environ=os.environ if environ is None else environ
    raw=extra if extra is not None else environ.get(EXTRA_TABLES_ENV,'')
    tables=list(TABLES)
    for name in (part.strip() for part in raw.split(',')):
        if not name:
            continue
        if not TABLE_NAME.match(name):
            raise SystemExit(f'Invalid table name for backup check: {name!r}')
        if name not in tables:
            tables.append(name)
    return tuple(tables)


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--project',required=True)
    parser.add_argument('--env-file',default='.env' if (ROOT/'.env').exists() else '.env.example')
    parser.add_argument('--output-dir',default='reports/backup-restore')
    parser.add_argument('--keep-backup',action='store_true')
    parser.add_argument('--extra-tables',default=None,help=f'Comma-separated extra tables to fingerprint (default: ${EXTRA_TABLES_ENV})')
    args=parser.parse_args()
    tables=resolve_tables(args.extra_tables)
    compose=['docker','compose','--env-file',args.env_file,'-p',args.project]
    suffix=uuid.uuid4().hex[:12]; database='insighthub_restore_'+suffix
    output=ROOT/args.output_dir; output.mkdir(parents=True,exist_ok=True,mode=0o700)
    local_dump=output/f'insighthub-{suffix}.dump'; container_dump=f'/tmp/insighthub-{suffix}.dump'
    def run(command,input=None):
        result=subprocess.run(command,cwd=ROOT,input=input,capture_output=True,text=True)
        if result.returncode: raise RuntimeError('Backup/restore command failed; inspect local Docker/database availability.')
        return result.stdout
    def sql(database,query):
        return run(compose+['exec','-T','postgres','psql','-U','insighthub','-d',database,'-At','-c',query])
    def fingerprint(database):
        result={}
        for table in tables:
            # Stable row ordering hashes every value, including bytes, vectors and JSON.
            raw=sql(database,f'SELECT row_to_json(t)::text FROM {table} t ORDER BY row_to_json(t)::text COLLATE "C"')
            result[table]={'rows':len(raw.splitlines()),'sha256':hashlib.sha256(raw.encode()).hexdigest()}
        return result
    artifact={'schema_version':2,'created_at':datetime.now(timezone.utc).isoformat(),'compose_project':args.project,'passed':False}
    try:
        source=fingerprint('insighthub')
        if any(source[t]['rows']==0 for t in ('documents','document_sources','source_segments','chunks','operation_records')):
            raise RuntimeError('Restore drill requires a populated corpus and completed chat operations, not an empty database.')
        run(compose+['exec','-T','postgres','pg_dump','-U','insighthub','-d','insighthub','-Fc','-f',container_dump])
        run(compose+['cp',f'postgres:{container_dump}',str(local_dump)])
        local_dump.chmod(0o600)
        artifact['backup_sha256']=hashlib.sha256(local_dump.read_bytes()).hexdigest()
        run(compose+['exec','-T','postgres','createdb','-U','insighthub',database])
        run(compose+['exec','-T','postgres','pg_restore','-U','insighthub','-d',database,container_dump])
        restored=fingerprint(database); after=fingerprint('insighthub')
        artifact.update(source=source,restored=restored,source_unchanged=source==after,content_equal=source==restored)
        artifact['orphan_chunks']=int(sql(database,"SELECT count(*) FROM chunks c LEFT JOIN documents d ON d.id=c.document_id LEFT JOIN source_segments s ON s.id=c.source_segment_id WHERE d.id IS NULL OR s.id IS NULL OR c.embedding_identity_id IS DISTINCT FROM d.embedding_identity_id"))
        artifact['failed_attempts']=int(sql(database,"SELECT count(*) FROM ingestion_attempts WHERE status='failed'"))
        # The probe is isolated by DATABASE_URL and does not expose the restored DB on a port.
        probe='''import json,hashlib
from fastapi.testclient import TestClient
from app.main import app
from app.core.db import get_conn,close_pool
from app.services.retrieval import retrieve
client=TestClient(app)
with get_conn() as conn:
    documents=conn.execute("SELECT d.id,d.content_sha256,s.original_bytes,s.extracted_text FROM documents d JOIN document_sources s ON s.document_id=d.id WHERE d.status='ready'").fetchall()
    chunks=conn.execute("SELECT document_id,chunk_text FROM chunks ORDER BY id LIMIT 1").fetchone()
checks=[]
for identifier,digest,original,text in documents:
    response=client.get(f'/documents/{identifier}/source')
    checks.append(response.status_code==200 and response.json()['content']==text and hashlib.sha256(bytes(original)).hexdigest()==digest)
contexts=retrieve(chunks[1],document_ids=[chunks[0]]) if chunks else []
with get_conn() as conn:
    operations=conn.execute("SELECT operation_key FROM operation_records WHERE operation_type='chat' AND status='succeeded'").fetchall()
    segments=conn.execute("SELECT id,document_id,locator_type,locator_value,segment_text FROM source_segments").fetchall()
for identifier,document_id,kind,value,text in segments:
    response=client.get(f'/documents/{document_id}/source?segment_id={identifier}')
    checks.append(response.status_code==200 and response.json()['content']==text and response.json()['locator']=={'type':kind,'value':value})
for key, in operations:
    response=client.get(f'/operations/chat/{key}')
    checks.append(response.status_code==200 and response.json()['status']=='succeeded')
print(json.dumps({'source_reads':len(checks),'all_source_checks':bool(checks) and all(checks),'retrieval_contexts':len(contexts),'scope_valid':bool(contexts) and all(c['document_id']==chunks[0] for c in contexts),'chat_operations':len(operations)}))
close_pool()
'''
        raw=run(compose+['run','--rm','--no-deps','-T','-e',f'DATABASE_URL=postgresql://insighthub:insighthub@postgres:5432/{database}','api','python','-'],input=probe)
        artifact['application_probe']=json.loads(raw.strip().splitlines()[-1])
        probe_result=artifact['application_probe']
        artifact['passed']=source==restored==after and artifact['orphan_chunks']==0 and artifact['failed_attempts']>0 and probe_result['all_source_checks'] and probe_result['scope_valid'] and probe_result['chat_operations']>0
    except Exception as exc:
        artifact['error']=str(exc) if isinstance(exc,RuntimeError) else type(exc).__name__
    finally:
        subprocess.run(compose+['exec','-T','postgres','dropdb','-U','insighthub','--if-exists',database],cwd=ROOT,capture_output=True)
        subprocess.run(compose+['exec','-T','postgres','rm','-f',container_dump],cwd=ROOT,capture_output=True)
        if local_dump.exists() and not args.keep_backup: local_dump.unlink()
        artifact['backup_retained']=args.keep_backup and local_dump.exists()
        path=output/f'backup-restore-{suffix}.json'
        path.write_text(json.dumps(artifact,indent=2)+'\n'); path.chmod(0o600)
        print(path); print('PASS' if artifact['passed'] else 'FAIL')
    if not artifact['passed']: raise SystemExit(1)

if __name__=='__main__': main()
