import sqlite3
import os

DB_PATH = "knowledgebase.db"

def get_db():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    init_db(conn)
    return conn


def init_db(conn):
    cur = conn.cursor()

    # ================= USERS =================
    cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE,
        password TEXT,
        role TEXT,
        name TEXT,
        bio TEXT,
        avatar TEXT
    )
    """)

    # ================= ARTICLES =================
    cur.execute("""
    CREATE TABLE IF NOT EXISTS articles (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT,
        content TEXT,
        author TEXT,
        attachment TEXT,
        chart_config TEXT,
        created_at TEXT
    )
    """)

    # ================= ARTICLE LIKES =================
    cur.execute("""
    CREATE TABLE IF NOT EXISTS article_likes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        article_id INTEGER,
        username TEXT
    )
    """)

    # ================= ARTICLE COMMENTS =================
    cur.execute("""
    CREATE TABLE IF NOT EXISTS article_comments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        article_id INTEGER,
        username TEXT,
        comment TEXT,
        created_at TEXT
    )
    """)

    # ================= CHAT =================
    cur.execute("""
    CREATE TABLE IF NOT EXISTS chat (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        sender TEXT,
        receiver TEXT,
        message TEXT,
        attachment TEXT,
        created_at TEXT,
        is_read INTEGER DEFAULT 0
    )
    """)

    conn.commit()


# =====================================================
# AUTO MIGRATION (ANTI ERROR KOLOM TIDAK ADA)
# =====================================================
def ensure_column(conn, table, column, col_type):
    cur = conn.cursor()
    cur.execute(f"PRAGMA table_info({table})")
    cols = [c["name"] for c in cur.fetchall()]

    if column not in cols:
        cur.execute(f"ALTER TABLE {table} ADD COLUMN {column} {col_type}")
        conn.commit()


def migrate():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    # USERS
    ensure_column(conn, "users", "name", "TEXT")
    ensure_column(conn, "users", "bio", "TEXT")
    ensure_column(conn, "users", "avatar", "TEXT")

    # ARTICLES
    ensure_column(conn, "articles", "attachment", "TEXT")
    ensure_column(conn, "articles", "chart_config", "TEXT")

    # CHAT
    ensure_column(conn, "chat", "is_read", "INTEGER DEFAULT 0")

    conn.close()


# Jalankan migration otomatis
if os.path.exists(DB_PATH):
    migrate()
