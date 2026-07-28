"""永続化レイヤー（デュアルモード）。

- 環境変数 DATABASE_URL が設定されている場合: PostgreSQL（Neon/Supabase等の無料枠）に保存。
  Render無料プランのようにサーバーのディスクが消える環境でも、データは外部DBに残る。
- 未設定の場合: 従来どおりローカルのSQLite（data/app.db）に保存。

シート画像・学習ルール・ナレッジ編集もDBに保存されるため、
PostgreSQLモードならサーバーが再起動してもすべてのデータが維持される。
"""
import json
import os
from datetime import datetime

DATABASE_URL = os.environ.get("DATABASE_URL", "").strip()
PG = bool(DATABASE_URL)

DB_PATH = os.path.join(os.path.dirname(__file__), "data", "app.db")

if PG:
    import psycopg2
    from psycopg2.extras import RealDictCursor


def _q(sql):
    """SQLiteの ? プレースホルダをPostgres用 %s に変換する。"""
    return sql.replace("?", "%s") if PG else sql


class _PgConn:
    """sqlite3.Connectionと同じ使い勝手にするための薄いラッパー。"""

    def __init__(self, conn):
        self._conn = conn

    def execute(self, sql, params=()):
        cur = self._conn.cursor()
        cur.execute(_q(sql), params)
        return cur

    def commit(self):
        self._conn.commit()

    def close(self):
        self._conn.close()


def get_conn():
    if PG:
        conn = psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
        return _PgConn(conn)
    import sqlite3

    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def _id_type():
    return "SERIAL PRIMARY KEY" if PG else "INTEGER PRIMARY KEY AUTOINCREMENT"


def _blob_type():
    return "BYTEA" if PG else "BLOB"


def init_db():
    conn = get_conn()
    statements = [
        f"""CREATE TABLE IF NOT EXISTS analyses (
            id {_id_type()},
            created_at TEXT NOT NULL,
            image_filename TEXT,
            model TEXT,
            grade TEXT,
            interior_grade TEXT,
            verdict TEXT,
            summary TEXT,
            full_response TEXT,
            user_name TEXT,
            case_id INTEGER
        )""",
        f"""CREATE TABLE IF NOT EXISTS feedback (
            id {_id_type()},
            analysis_id INTEGER NOT NULL,
            created_at TEXT NOT NULL,
            rating TEXT NOT NULL,
            comment TEXT,
            user_name TEXT,
            category TEXT
        )""",
        f"""CREATE TABLE IF NOT EXISTS outcomes (
            id {_id_type()},
            analysis_id INTEGER NOT NULL,
            created_at TEXT NOT NULL,
            purchased TEXT,
            actual_condition TEXT,
            repair_cost INTEGER,
            hidden_issues TEXT,
            satisfaction TEXT,
            notes TEXT,
            user_name TEXT
        )""",
        f"""CREATE TABLE IF NOT EXISTS learned_rules (
            id {_id_type()},
            created_at TEXT NOT NULL,
            source TEXT NOT NULL,
            rule_text TEXT NOT NULL,
            active INTEGER NOT NULL DEFAULT 1
        )""",
        f"""CREATE TABLE IF NOT EXISTS cases (
            id {_id_type()},
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            customer_name TEXT NOT NULL,
            car_info TEXT,
            stage TEXT NOT NULL,
            assignee TEXT,
            notes TEXT,
            final_price TEXT
        )""",
        f"""CREATE TABLE IF NOT EXISTS case_events (
            id {_id_type()},
            case_id INTEGER NOT NULL,
            created_at TEXT NOT NULL,
            user_name TEXT,
            event_type TEXT NOT NULL,
            content TEXT
        )""",
        f"""CREATE TABLE IF NOT EXISTS images (
            filename TEXT PRIMARY KEY,
            data {_blob_type()},
            created_at TEXT
        )""",
        """CREATE TABLE IF NOT EXISTS kv_store (
            key TEXT PRIMARY KEY,
            value TEXT
        )""",
        f"""CREATE TABLE IF NOT EXISTS case_documents (
            id {_id_type()},
            case_id INTEGER NOT NULL,
            created_at TEXT NOT NULL,
            doc_type TEXT,
            orig_name TEXT,
            data {_blob_type()},
            user_name TEXT
        )""",
    ]
    for stmt in statements:
        conn.execute(stmt)

    if PG:
        conn.execute("ALTER TABLE cases ADD COLUMN IF NOT EXISTS final_price TEXT")

    if not PG:
        case_cols = [r["name"] for r in conn.execute("PRAGMA table_info(cases)").fetchall()]
        if "final_price" not in case_cols:
            conn.execute("ALTER TABLE cases ADD COLUMN final_price TEXT")
        # 既存SQLite DBからのアップグレード用（列が無ければ追加）
        for table in ("feedback", "outcomes"):
            cols = [r["name"] for r in conn.execute(f"PRAGMA table_info({table})").fetchall()]
            if "user_name" not in cols:
                conn.execute(f"ALTER TABLE {table} ADD COLUMN user_name TEXT")
        fb_cols = [r["name"] for r in conn.execute("PRAGMA table_info(feedback)").fetchall()]
        if "category" not in fb_cols:
            conn.execute("ALTER TABLE feedback ADD COLUMN category TEXT")
        cols = [r["name"] for r in conn.execute("PRAGMA table_info(analyses)").fetchall()]
        if "user_name" not in cols:
            conn.execute("ALTER TABLE analyses ADD COLUMN user_name TEXT")
        if "case_id" not in cols:
            conn.execute("ALTER TABLE analyses ADD COLUMN case_id INTEGER")

    conn.commit()
    conn.close()


def _insert_returning_id(conn, sql, params):
    if PG:
        cur = conn.execute(sql + " RETURNING id", params)
        new_id = cur.fetchone()["id"]
        return new_id
    cur = conn.execute(sql, params)
    return cur.lastrowid


# ---- 画像（オークションシート）の保存 ----

def save_image(filename, data_bytes):
    conn = get_conn()
    if PG:
        conn.execute(
            "INSERT INTO images (filename, data, created_at) VALUES (?, ?, ?) ON CONFLICT (filename) DO NOTHING",
            (filename, psycopg2.Binary(data_bytes), datetime.utcnow().isoformat()),
        )
    else:
        conn.execute(
            "INSERT OR IGNORE INTO images (filename, data, created_at) VALUES (?, ?, ?)",
            (filename, data_bytes, datetime.utcnow().isoformat()),
        )
    conn.commit()
    conn.close()


def get_image(filename):
    conn = get_conn()
    row = conn.execute("SELECT data FROM images WHERE filename = ?", (filename,)).fetchone()
    conn.close()
    if not row or row["data"] is None:
        return None
    data = row["data"]
    return bytes(data)


# ---- 設定値（ナレッジ編集など）の保存 ----

def set_kv(key, value):
    conn = get_conn()
    if PG:
        conn.execute(
            "INSERT INTO kv_store (key, value) VALUES (?, ?) ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value",
            (key, value),
        )
    else:
        conn.execute(
            "INSERT INTO kv_store (key, value) VALUES (?, ?) ON CONFLICT (key) DO UPDATE SET value = excluded.value",
            (key, value),
        )
    conn.commit()
    conn.close()


def get_kv(key):
    conn = get_conn()
    row = conn.execute("SELECT value FROM kv_store WHERE key = ?", (key,)).fetchone()
    conn.close()
    return row["value"] if row else None


# ---- 解析結果 ----

def save_analysis(image_filename, model, grade, interior_grade, verdict, summary, full_response, user_name=None, case_id=None):
    conn = get_conn()
    analysis_id = _insert_returning_id(
        conn,
        """INSERT INTO analyses
           (created_at, image_filename, model, grade, interior_grade, verdict, summary, full_response, user_name, case_id)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            datetime.utcnow().isoformat(),
            image_filename,
            model,
            grade,
            interior_grade,
            verdict,
            summary,
            json.dumps(full_response, ensure_ascii=False),
            user_name,
            case_id,
        ),
    )
    conn.commit()
    conn.close()
    return analysis_id


def get_analysis(analysis_id):
    conn = get_conn()
    row = conn.execute("SELECT * FROM analyses WHERE id = ?", (analysis_id,)).fetchone()
    conn.close()
    return row


def list_analyses(limit=50):
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM analyses ORDER BY id DESC LIMIT ?", (limit,)
    ).fetchall()
    conn.close()
    return rows


def add_feedback(analysis_id, rating, comment, user_name=None, category=None):
    conn = get_conn()
    conn.execute(
        "INSERT INTO feedback (analysis_id, created_at, rating, comment, user_name, category) VALUES (?, ?, ?, ?, ?, ?)",
        (analysis_id, datetime.utcnow().isoformat(), rating, comment, user_name, category),
    )
    conn.commit()
    conn.close()


def add_outcome(analysis_id, purchased, actual_condition, repair_cost, hidden_issues, satisfaction, notes, user_name=None):
    conn = get_conn()
    conn.execute(
        """INSERT INTO outcomes
           (analysis_id, created_at, purchased, actual_condition, repair_cost, hidden_issues, satisfaction, notes, user_name)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            analysis_id,
            datetime.utcnow().isoformat(),
            purchased,
            actual_condition,
            repair_cost,
            hidden_issues,
            satisfaction,
            notes,
            user_name,
        ),
    )
    conn.commit()
    conn.close()


def get_feedback_for_analysis(analysis_id):
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM feedback WHERE analysis_id = ? ORDER BY id DESC", (analysis_id,)
    ).fetchall()
    conn.close()
    return rows


def get_outcomes_for_analysis(analysis_id):
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM outcomes WHERE analysis_id = ? ORDER BY id DESC", (analysis_id,)
    ).fetchall()
    conn.close()
    return rows


def all_feedback_with_analysis(limit=200):
    conn = get_conn()
    rows = conn.execute(
        """SELECT f.*, a.summary as analysis_summary, a.verdict as analysis_verdict
           FROM feedback f JOIN analyses a ON f.analysis_id = a.id
           ORDER BY f.id DESC LIMIT ?""",
        (limit,),
    ).fetchall()
    conn.close()
    return rows


def all_outcomes_with_analysis(limit=200):
    conn = get_conn()
    rows = conn.execute(
        """SELECT o.*, a.summary as analysis_summary, a.verdict as analysis_verdict
           FROM outcomes o JOIN analyses a ON o.analysis_id = a.id
           ORDER BY o.id DESC LIMIT ?""",
        (limit,),
    ).fetchall()
    conn.close()
    return rows


def add_learned_rule(source, rule_text):
    conn = get_conn()
    conn.execute(
        "INSERT INTO learned_rules (created_at, source, rule_text, active) VALUES (?, ?, ?, 1)",
        (datetime.utcnow().isoformat(), source, rule_text),
    )
    conn.commit()
    conn.close()


def list_learned_rules(active_only=True):
    conn = get_conn()
    if active_only:
        rows = conn.execute(
            "SELECT * FROM learned_rules WHERE active = 1 ORDER BY id DESC"
        ).fetchall()
    else:
        rows = conn.execute("SELECT * FROM learned_rules ORDER BY id DESC").fetchall()
    conn.close()
    return rows


def deactivate_rule(rule_id):
    conn = get_conn()
    conn.execute("UPDATE learned_rules SET active = 0 WHERE id = ?", (rule_id,))
    conn.commit()
    conn.close()


def stats_summary():
    conn = get_conn()
    total = conn.execute("SELECT COUNT(*) c FROM analyses").fetchone()["c"]
    fb_total = conn.execute("SELECT COUNT(*) c FROM feedback").fetchone()["c"]
    fb_correct = conn.execute(
        "SELECT COUNT(*) c FROM feedback WHERE rating = 'correct'"
    ).fetchone()["c"]
    outcomes_total = conn.execute("SELECT COUNT(*) c FROM outcomes").fetchone()["c"]
    verdicts = conn.execute(
        "SELECT verdict, COUNT(*) c FROM analyses GROUP BY verdict"
    ).fetchall()
    conn.close()
    accuracy = round((fb_correct / fb_total) * 100, 1) if fb_total else None
    return {
        "total": total,
        "feedback_total": fb_total,
        "feedback_correct": fb_correct,
        "accuracy_pct": accuracy,
        "outcomes_total": outcomes_total,
        "verdict_breakdown": {r["verdict"]: r["c"] for r in verdicts},
    }


# ---- 案件管理（オーストラリア輸出パイプライン） ----

CASE_STAGES = [
    "問い合わせ",
    "候補提案",
    "契約",
    "落札・購入",
    "港手配",
    "豪州到着",
    "コンプライアンス",
    "完了",
]


def create_case(customer_name, car_info, assignee, notes):
    now = datetime.utcnow().isoformat()
    conn = get_conn()
    case_id = _insert_returning_id(
        conn,
        """INSERT INTO cases (created_at, updated_at, customer_name, car_info, stage, assignee, notes)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (now, now, customer_name, car_info, CASE_STAGES[0], assignee, notes),
    )
    conn.commit()
    conn.close()
    return case_id


def list_cases(active_only=False):
    conn = get_conn()
    if active_only:
        rows = conn.execute(
            "SELECT * FROM cases WHERE stage != '完了' ORDER BY updated_at DESC"
        ).fetchall()
    else:
        rows = conn.execute("SELECT * FROM cases ORDER BY updated_at DESC").fetchall()
    conn.close()
    return rows


def get_case(case_id):
    conn = get_conn()
    row = conn.execute("SELECT * FROM cases WHERE id = ?", (case_id,)).fetchone()
    conn.close()
    return row


def update_case_stage(case_id, stage, user_name=None):
    if stage not in CASE_STAGES:
        return
    now = datetime.utcnow().isoformat()
    conn = get_conn()
    conn.execute(
        "UPDATE cases SET stage = ?, updated_at = ? WHERE id = ?", (stage, now, case_id)
    )
    conn.execute(
        "INSERT INTO case_events (case_id, created_at, user_name, event_type, content) VALUES (?, ?, ?, ?, ?)",
        (case_id, now, user_name, "stage_change", stage),
    )
    conn.commit()
    conn.close()


def add_case_note(case_id, content, user_name=None):
    now = datetime.utcnow().isoformat()
    conn = get_conn()
    conn.execute(
        "INSERT INTO case_events (case_id, created_at, user_name, event_type, content) VALUES (?, ?, ?, ?, ?)",
        (case_id, now, user_name, "note", content),
    )
    conn.execute("UPDATE cases SET updated_at = ? WHERE id = ?", (now, case_id))
    conn.commit()
    conn.close()


def case_events(case_id):
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM case_events WHERE case_id = ? ORDER BY id DESC", (case_id,)
    ).fetchall()
    conn.close()
    return rows


def analyses_for_case(case_id):
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM analyses WHERE case_id = ? ORDER BY id DESC", (case_id,)
    ).fetchall()
    conn.close()
    return rows


def link_analysis_to_case(analysis_id, case_id):
    conn = get_conn()
    conn.execute("UPDATE analyses SET case_id = ? WHERE id = ?", (case_id, analysis_id))
    conn.commit()
    conn.close()


def set_case_price(case_id, final_price, user_name=None):
    now = datetime.utcnow().isoformat()
    conn = get_conn()
    conn.execute(
        "UPDATE cases SET final_price = ?, updated_at = ? WHERE id = ?",
        (final_price, now, case_id),
    )
    conn.execute(
        "INSERT INTO case_events (case_id, created_at, user_name, event_type, content) VALUES (?, ?, ?, ?, ?)",
        (case_id, now, user_name, "note", f"成約金額を記録: {final_price}"),
    )
    conn.commit()
    conn.close()


# ---- 案件書類（Invoice / Import Approval 等） ----

def add_case_document(case_id, doc_type, orig_name, data_bytes, user_name=None):
    conn = get_conn()
    payload = psycopg2.Binary(data_bytes) if PG else data_bytes
    doc_id = _insert_returning_id(
        conn,
        """INSERT INTO case_documents (case_id, created_at, doc_type, orig_name, data, user_name)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (case_id, datetime.utcnow().isoformat(), doc_type, orig_name, payload, user_name),
    )
    conn.commit()
    conn.close()
    return doc_id


def list_case_documents(case_id):
    conn = get_conn()
    rows = conn.execute(
        "SELECT id, case_id, created_at, doc_type, orig_name, user_name FROM case_documents WHERE case_id = ? ORDER BY id DESC",
        (case_id,),
    ).fetchall()
    conn.close()
    return rows


def get_case_document(doc_id):
    conn = get_conn()
    row = conn.execute("SELECT * FROM case_documents WHERE id = ?", (doc_id,)).fetchone()
    conn.close()
    return row
