import os
import sqlite3
import psycopg2

DB_PATH = "knowledgebase.db"


# ======================================================
# CONNECTION
# ======================================================
def get_db():
    database_url = os.getenv("DATABASE_URL")

    # ================= POSTGRES =================
    if database_url:
        import psycopg2
        #conn = psycopg2.connect(database_url)
        conn = psycopg2.connect(
        database_url,
        sslmode="require",
        connect_timeout=10
        )

        init_db_postgres(conn)
        return conn

    # ================= SQLITE =================
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    init_db_sqlite(conn)
    return conn


# ======================================================
# INIT SQLITE
# ======================================================
def init_db_sqlite(conn):
    cur = conn.cursor()

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

    cur.execute("""
    CREATE TABLE IF NOT EXISTS article_likes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        article_id INTEGER,
        username TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS article_comments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        article_id INTEGER,
        username TEXT,
        comment TEXT,
        created_at TEXT
    )
    """)

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


# ======================================================
# INIT POSTGRES
# ======================================================
def init_db_postgres(conn):
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id SERIAL PRIMARY KEY,
        username TEXT UNIQUE,
        password TEXT,
        role TEXT,
        name TEXT,
        bio TEXT,
        avatar TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS articles (
        id SERIAL PRIMARY KEY,
        title TEXT,
        content TEXT,
        author TEXT,
        attachment TEXT,
        chart_config TEXT,
        created_at TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS article_likes (
        id SERIAL PRIMARY KEY,
        article_id INTEGER,
        username TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS article_comments (
        id SERIAL PRIMARY KEY,
        article_id INTEGER,
        username TEXT,
        comment TEXT,
        created_at TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS chat (
        id SERIAL PRIMARY KEY,
        sender TEXT,
        receiver TEXT,
        message TEXT,
        attachment TEXT,
        created_at TEXT,
        is_read INTEGER DEFAULT 0
    )
    """)

    conn.commit()


# ======================================================
# SQLITE MIGRATION (tetap jalan jika lokal)
# ======================================================
def ensure_column(conn, table, column, col_type):
    cur = conn.cursor()
    cur.execute(f"PRAGMA table_info({table})")
    cols = [c[1] for c in cur.fetchall()]

    if column not in cols:
        cur.execute(f"ALTER TABLE {table} ADD COLUMN {column} {col_type}")
        conn.commit()


def migrate():
    if not os.path.exists(DB_PATH):
        return

    conn = sqlite3.connect(DB_PATH)

    ensure_column(conn, "users", "name", "TEXT")
    ensure_column(conn, "users", "bio", "TEXT")
    ensure_column(conn, "users", "avatar", "TEXT")

    ensure_column(conn, "articles", "attachment", "TEXT")
    ensure_column(conn, "articles", "chart_config", "TEXT")

    ensure_column(conn, "chat", "is_read", "INTEGER DEFAULT 0")

    conn.close()


migrate()
