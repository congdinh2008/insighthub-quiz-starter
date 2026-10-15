"""Read-only MCP server for the InsightHub database (M0.2, LR-05).

The security boundary is the PostgreSQL role `insighthub_readonly` (migration 003):
SELECT on an explicit list of tables, read-only transactions, 5 second statement timeout.
This server does not try to filter SQL. It refuses to start with any other role, so a
"read-only" label can never hide an owner connection (see Knowledge Content session 2).

Run through `.mcp.json` (copied from `.mcp.json.example`). Password comes from the
environment variable MCP_DB_READONLY_PASSWORD or, if missing, from that single key in `.env`.
"""

from __future__ import annotations

import os
import sys
from decimal import Decimal
from pathlib import Path

import psycopg
from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError

ROOT = Path(__file__).resolve().parents[2]
ROLE = "insighthub_readonly"
MAX_ROWS = 200
MAX_TEXT = 500


def _password() -> str:
    value = os.environ.get("MCP_DB_READONLY_PASSWORD", "")
    if value:
        return value
    env_file = ROOT / ".env"
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            if line.startswith("MCP_DB_READONLY_PASSWORD="):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    return ""


def _connect() -> psycopg.Connection:
    password = _password()
    if not password:
        raise SystemExit("Thiếu MCP_DB_READONLY_PASSWORD. Xem GETTING_STARTED mục MCP.")
    conn = psycopg.connect(
        host=os.environ.get("MCP_DB_HOST", "127.0.0.1"),
        port=int(os.environ.get("DB_PORT", "5433")),
        dbname=os.environ.get("MCP_DB_NAME", "insighthub"),
        user=ROLE,
        password=password,
        connect_timeout=5,
        autocommit=False,
    )
    conn.read_only = True
    current = conn.execute("SELECT current_user").fetchone()[0]
    if current != ROLE:
        conn.close()
        raise SystemExit(f"Từ chối chạy: kết nối bằng role {current}, chỉ chấp nhận {ROLE}.")
    conn.rollback()
    return conn


def _cell(value):
    if isinstance(value, (bytes, bytearray, memoryview)):
        return f"<{len(bytes(value))} bytes>"
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, str) and len(value) > MAX_TEXT:
        return value[:MAX_TEXT] + f"... (+{len(value) - MAX_TEXT} ký tự)"
    if value is None or isinstance(value, (int, float, bool)):
        return value
    return str(value)


server = MCPServer(
    name="insighthub-db-readonly",
    instructions=(
        "Truy vấn chỉ đọc database InsightHub bằng role insighthub_readonly. "
        "Ghi dữ liệu sẽ bị PostgreSQL từ chối. Kết quả tối đa 200 dòng, chuỗi dài bị cắt."
    ),
)


@server.tool(description="Liệt kê các bảng role chỉ đọc được phép SELECT.")
def list_tables() -> list[str]:
    with _connect() as conn:
        rows = conn.execute(
            "SELECT table_name FROM information_schema.table_privileges "
            "WHERE grantee = %s AND privilege_type = 'SELECT' ORDER BY table_name",
            (ROLE,),
        ).fetchall()
    return [row[0] for row in rows]


@server.tool(description="Mô tả cột của một bảng được phép đọc.")
def describe_table(table: str) -> list[dict]:
    with _connect() as conn:
        rows = conn.execute(
            "SELECT column_name, data_type, is_nullable FROM information_schema.columns "
            "WHERE table_name = %s ORDER BY ordinal_position",
            (table,),
        ).fetchall()
    if not rows:
        raise ToolError(f"Không có bảng {table} hoặc role không được phép đọc.")
    return [{"column": r[0], "type": r[1], "nullable": r[2] == "YES"} for r in rows]


@server.tool(description="Chạy một câu SQL trong transaction chỉ đọc. Lệnh ghi sẽ bị database từ chối.")
def run_query(sql: str) -> dict:
    with _connect() as conn:
        try:
            cursor = conn.execute(sql)
            columns = [c.name for c in cursor.description] if cursor.description else []
            rows = cursor.fetchmany(MAX_ROWS + 1) if columns else []
        except psycopg.Error as exc:
            conn.rollback()
            # Trả lỗi của database để người học thấy giới hạn được thực thi ở đâu.
            raise ToolError(f"{exc.sqlstate}: {exc.diag.message_primary}") from None
        conn.rollback()
    return {
        "columns": columns,
        "rows": [[_cell(v) for v in row] for row in rows[:MAX_ROWS]],
        "truncated": len(rows) > MAX_ROWS,
    }


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--check":
        with _connect() as connection:
            print("OK", connection.execute("SELECT current_user").fetchone()[0])
        sys.exit(0)
    server.run("stdio")
