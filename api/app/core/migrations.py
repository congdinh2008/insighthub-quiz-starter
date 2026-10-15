"""Forward-only SQL migration runner guarded by a PostgreSQL advisory lock."""

from pathlib import Path

from app.core.config import get_settings
from app.core.errors import SchemaMismatch


def run_migrations(conn):
    path = Path(get_settings().migration_path)
    if not path.exists():
        local = Path(__file__).resolve().parents[2] / "migrations"
        path = local if local.exists() else path
    if not path.exists():
        raise SchemaMismatch("Không tìm thấy migration bundle.")
    with conn.transaction():
        conn.execute("SELECT pg_advisory_xact_lock(hashtext('insighthub:migrations'))")
        conn.execute(
            "CREATE TABLE IF NOT EXISTS schema_migrations ("
            "version TEXT PRIMARY KEY, applied_at TIMESTAMPTZ NOT NULL DEFAULT now())"
        )
        applied = {
            row[0] for row in conn.execute("SELECT version FROM schema_migrations")
        }
        for migration in sorted(path.glob("*.sql")):
            version = migration.stem
            if version in applied:
                continue
            conn.execute(migration.read_text(encoding="utf-8"))
            conn.execute(
                "INSERT INTO schema_migrations(version) VALUES (%s) ON CONFLICT DO NOTHING",
                (version,),
            )
