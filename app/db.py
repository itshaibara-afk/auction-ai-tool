"""SQLite永続化レイヤー。すべてのデータはローカルファイル data/app.db に保存される。"""
import sqlite3
import json
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), "data", "app.db")


def get_conn():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    conn = get_conn()
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS analyses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT NOT NULL,
            image_filename TEXT,
            model TEXT,
            grade TEXT,
            interior_grade TEXT,
            verdict TEXT,
            summary TEXT,
            full_response TEXT
        );

        CREATE TABLE IF NOT EXISTS feedback (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            analysis_id INTEGER NOT NULL,
            created_at TEXT NOT NULL,
            rating TEXT NOT NULL,      -- 'correct' | 'incorrect' | 'partial'
            comment TEXT,
            user_name TEXT,
            FOREIGN KEY (analysis_id) REFERENCES analyses(id)
        );

        CREATE TABLE IF NOT EXISTS outcomes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            analysis_id INTEGER NOT NULL,
            created_at TEXT NOT NULL,
            purchased TEXT,            -- 'yes' | 'no'
            actual_condition TEXT,     -- free text: 実際の状態
            repair_cost INTEGER,       -- 実際にかかった修理費用(円) nullable
            hidden_issues TEXT,        -- シートに無かった問題点
            satisfaction TEXT,         -- 'good' | 'ok' | 'bad'
            notes TEXT,
            user_name TEXT,
            FOREIGN KEY (analysis_id) REFERENCES analyses(id)
        );

        CREATE TABLE IF NOT EXISTS cases (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            customer_name TEXT NOT NULL,
            car_info TEXT,              -- 車種・条件など
            stage TEXT NOT NULL,        -- パイプラインのステージ
            assignee TEXT,              -- 担当者
            notes TEXT
        );

        CREATE TABLE IF NOT EXISTS case_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            case_id INTEGER NOT NULL,
            created_at TEXT NOT NULL,
            user_name TEXT,
            event_type TEXT NOT NULL,   -- 'note' | 'stage_change'
            content TEXT,
            FOREIGN KEY (case_id) REFERENCES cases(id)
        );

        CREATE TABLE IF NOT EXISTS learned_rules (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT NOT NULL,
            source TEXT NOT NULL,      -- 'feedback' | 'growth' | 'manual'
            rule_text TEXT NOT NULL,
            active INTEGER NOT NULL DEFAULT 1
        );
        """
    )
    # 既存DBからのアップグレード用（列が無ければ追加）
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
    cur = conn.execute(
        """INSERT INTO cases (created_at, updated_at, customer_name, car_info, stage, assignee, notes)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (now, now, customer_name, car_info, CASE_STAGES[0], assignee, notes),
    )
    conn.commit()
    case_id = cur.lastrowid
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


def save_analysis(image_filename, model, grade, interior_grade, verdict, summary, full_response, user_name=None, case_id=None):
    conn = get_conn()
    cur = conn.execute(
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
    analysis_id = cur.lastrowid
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
