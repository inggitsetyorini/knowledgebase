import bcrypt
import streamlit as st
from db import get_db

conn = get_db()

def hash_pw(p): return bcrypt.hashpw(p.encode(), bcrypt.gensalt())
def check_pw(p,h): return bcrypt.checkpw(p.encode(), h)

def init_admin():
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE username='admin'")
    if not c.fetchone():
        c.execute("""
            INSERT INTO users(username,password,role,name,bio)
            VALUES (?,?,?,?,?)
        """, ("admin", hash_pw("admin123"), "admin",
              "Administrator", "Super Admin"))
        conn.commit()

def login_ui():
    st.title("🔐 Login")
    u = st.text_input("Username")
    p = st.text_input("Password", type="password")

    if st.button("Login"):
        c = conn.cursor()
        c.execute("SELECT password,role FROM users WHERE username=?", (u,))
        r = c.fetchone()
        if r and check_pw(p,r[0]):
            st.session_state.login = True
            st.session_state.user = u
            st.session_state.role = r[1]
            st.rerun()
        else:
            st.error("Login gagal")
