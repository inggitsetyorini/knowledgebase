import streamlit as st
import pandas as pd
from datetime import datetime
from db import get_db
from auth import login_ui, init_admin, hash_pw
from ai import ai_summary
from chat import chat_ui, unread_count
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import os 
from PIL import Image
from auth import hash_pw
import bcrypt
import json
import matplotlib.pyplot as plt
import re

def strip_html(text):
    return re.sub("<[^<]+?>", "", text)

st.markdown("""
<style>
.article-card {
    background: #1e222d;
    border-radius: 12px;
    padding: 16px;
    margin-bottom: 14px;
}
.article-meta {
    font-size: 12px;
    opacity: 0.7;
    margin-bottom: 8px;
}
.article-actions {
    display:flex;
    gap:12px;
    margin-top:10px;
}
.comment-box {
    background:#2a2f3a;
    border-radius:8px;
    padding:8px;
    margin-top:6px;
}
</style>
""", unsafe_allow_html=True)


st.set_page_config("Knowledge Base","📚",layout="wide")

conn = get_db()
init_admin()

if "login" not in st.session_state:
    st.session_state.login = False

if "edit_article_id" not in st.session_state:
    st.session_state.edit_article_id = None


def search_articles(q):
    df = pd.read_sql("SELECT * FROM articles", conn)
    if df.empty or not q:
        return df,None
    corpus = (df["title"]+" "+df["content"]).tolist()
    tfidf = TfidfVectorizer().fit_transform(corpus+[q])
    score = cosine_similarity(tfidf[-1],tfidf[:-1]).flatten()
    df["score"] = score
    df = df.sort_values("score",ascending=False)
    return df, ai_summary(df["content"].tolist())

def profile_page():
    st.subheader("👤 Profile Saya")

    user = conn.execute(
        "SELECT * FROM users WHERE username=?",
        (st.session_state.user,)
    ).fetchone()

    col1, col2 = st.columns([1, 3])
    
    st.divider()
    st.subheader("🔐 Ganti Password")

    old_pw = st.text_input("Password Lama", type="password")
    new_pw = st.text_input("Password Baru", type="password")
    confirm_pw = st.text_input("Konfirmasi Password Baru", type="password")

    if st.button("🔁 Ganti Password"):
        if not old_pw or not new_pw or not confirm_pw:
            st.error("Semua field password wajib diisi")
            st.stop()

        if new_pw != confirm_pw:
            st.error("Password baru dan konfirmasi tidak sama")
            st.stop()

        # ambil password lama
        current = conn.execute(
            "SELECT password FROM users WHERE username=?",
            (st.session_state.user,)
        ).fetchone()

        if not bcrypt.checkpw(old_pw.encode(), current["password"]):
            st.error("Password lama salah")
            st.stop()

        # update password
        conn.execute(
            "UPDATE users SET password=? WHERE username=?",
            (hash_pw(new_pw), st.session_state.user)
        )
        conn.commit()

        st.success("✅ Password berhasil diganti")
        st.toast("🔐 Password diperbarui", icon="✨")


    # ==== AVATAR ====
    with col1:
        if user["avatar"] and os.path.exists(user["avatar"]):
            st.image(user["avatar"], width=150)
        else:
            st.image("https://via.placeholder.com/150", width=150)

        avatar = st.file_uploader(
            "Upload Avatar",
            type=["png", "jpg", "jpeg"]
        )

    # ==== PROFILE FORM ====
    with col2:
        name = st.text_input("Nama", user["name"] or "")
        bio = st.text_area("Bio", user["bio"] or "")

    if st.button("💾 Simpan Profile"):
        avatar_path = user["avatar"]

        if avatar:
            os.makedirs("uploads/avatars", exist_ok=True)
            avatar_path = f"uploads/avatars/{st.session_state.user}.png"
            Image.open(avatar).save(avatar_path)

        conn.execute("""
            UPDATE users
            SET name=?, bio=?, avatar=?
            WHERE username=?
        """, (name, bio, avatar_path, st.session_state.user))
        conn.commit()

        st.success("Profile berhasil diperbarui")
        st.rerun()


def user_management():
    st.subheader("👥 User Management")

    df = pd.read_sql("SELECT id,username,role FROM users", conn)
    st.dataframe(df, width="stretch")

    st.divider()
    st.markdown("### ➕ Tambah User")

    u = st.text_input("Username")
    p = st.text_input("Password", type="password")
    r = st.selectbox("Role", ["user","editor","admin"])

    if st.button("Tambah User"):
        try:
            conn.execute("""
                INSERT INTO users(username,password,role,name,bio)
                VALUES (?,?,?,?,?)
            """, (u,hash_pw(p),r,u,""))
            conn.commit()
            st.success("User ditambahkan")
            st.rerun()
        except:
            st.error("Username sudah ada")

    st.divider()
    st.markdown("### 🔐 Reset Password User (Admin Only)")

    # 🔒 pastikan admin
    if st.session_state.role != "admin":
        st.info("Hanya admin yang bisa reset password user")
        return

    users = pd.read_sql(
        "SELECT username FROM users WHERE username != ?",
        conn,
        params=(st.session_state.user,)
    )

    target_user = st.selectbox(
        "Pilih User",
        users["username"].tolist()
    )

    new_pw = st.text_input(
        "Password Baru",
        type="password"
    )

    confirm_pw = st.text_input(
        "Konfirmasi Password Baru",
        type="password"
    )

    if st.button("🔁 Reset Password"):
        if not new_pw or not confirm_pw:
            st.error("Password tidak boleh kosong")
            st.stop()

        if new_pw != confirm_pw:
            st.error("Password dan konfirmasi tidak sama")
            st.stop()

        conn.execute(
            "UPDATE users SET password=? WHERE username=?",
            (hash_pw(new_pw), target_user)
        )
        conn.commit()

        st.success(f"✅ Password user `{target_user}` berhasil di-reset")
        st.toast("🔐 Password di-reset", icon="🛡️")


# ================= LOGIN =================
if not st.session_state.login:
    login_ui()
    st.stop()

# ================= SIDEBAR =================
badge = unread_count(st.session_state.user)
chat_label = f"💬 Chat {'🔴' if badge>0 else ''}"

menu_items = ["📖 Baca Artikel","✍️ Artikel Saya","👤 Profile",chat_label]
if st.session_state.role == "admin":
    menu_items.append("👥 User Management")

menu = st.sidebar.radio("Menu", menu_items)

if st.sidebar.button("Logout"):
    st.session_state.login = False
    st.rerun()

# ================= PAGES =================
from deep_translator import GoogleTranslator
translator = GoogleTranslator(source="auto", target="id")


if menu == "📖 Baca Artikel":
    st.subheader("📖 Baca Artikel")

    q = st.text_input("🔍 Cari artikel")
    df, summary = search_articles(q)

    if summary:
        st.info(f"🧠 Ringkasan AI:\n\n{summary}")

    for _, r in df.iterrows():
        with st.container():
            st.markdown("<div class='article-card'>", unsafe_allow_html=True)

            # ===== TITLE =====
            st.markdown(f"### {r['title']}")

            st.markdown(
                f"<div class='article-meta'>✍️ {r['author']} • {r['created_at']}</div>",
                unsafe_allow_html=True
            )

            # ===== CONTENT =====
            st.markdown(r["content"], unsafe_allow_html=True)
            # ===== RENDER CHART =====
            if r.get("chart_config"):
                cfg = json.loads(r["chart_config"])
                if cfg and cfg.get("csv") and os.path.exists(cfg["csv"]):
                    dfc = pd.read_csv(cfg["csv"])

                    st.markdown("#### 📊 Grafik")

                    fig, ax = plt.subplots()

                    if cfg["type"] == "Line":
                        ax.plot(dfc[cfg["x"]], dfc[cfg["y"]], color=cfg["color"])
                    elif cfg["type"] == "Bar":
                        ax.bar(dfc[cfg["x"]], dfc[cfg["y"]], color=cfg["color"])
                    else:
                        ax.fill_between(
                            dfc[cfg["x"]],
                            dfc[cfg["y"]],
                            color=cfg["color"],
                            alpha=0.6
                        )

                    ax.set_xlabel(cfg["x"])
                    ax.set_ylabel(cfg["y"])
                    st.pyplot(fig)


            # ===== ATTACHMENT =====
            if r["attachment"]:
                st.markdown(f"📎 [Download File]({r['attachment']})")

            # ===== LIKE =====
            likes = conn.execute(
                "SELECT COUNT(*) FROM article_likes WHERE article_id=?",
                (r["id"],)
            ).fetchone()[0]

            liked = conn.execute(
                "SELECT 1 FROM article_likes WHERE article_id=? AND username=?",
                (r["id"], st.session_state.user)
            ).fetchone()

            col1, col2, col3, col4 = st.columns(4)

            with col1:
                if st.button(
                    f"❤️ {likes}",
                    key=f"like_{r['id']}"
                ):
                    if not liked:
                        conn.execute(
                            "INSERT INTO article_likes(article_id, username) VALUES (?,?)",
                            (r["id"], st.session_state.user)
                        )
                        conn.commit()
                        st.rerun()

            # ===== SHARE TO CHAT =====
            with col2:
                target_users = pd.read_sql(
                    "SELECT username FROM users WHERE username != ?",
                    conn,
                    params=(st.session_state.user,)
                )["username"].tolist()

                target = st.selectbox(
                    "Kirim ke",
                    target_users,
                    key=f"share_to_{r['id']}"
                )

                if st.button("💬 Share ke Chat", key=f"share_{r['id']}"):
                    msg = f"""📚 *{r['title']}*

            {r['content'][:500]}...

            🔗 Dibagikan dari Knowledge Base
            """
                    conn.execute("""
                        INSERT INTO chat
                        (sender, receiver, message, created_at, is_read)
                        VALUES (?, ?, ?, ?, 0)
                    """, (
                        st.session_state.user,
                        target,
                        msg,
                        datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    ))
                    conn.commit()

                    st.success("✅ Artikel berhasil dibagikan ke chat")


            # ===== TRANSLATE =====
    
            with col3:
                if st.button("🌐 Translate EN", key=f"tr_{r['id']}"):
                    clean_text = strip_html(r["content"])
                    translated = GoogleTranslator(
                        source="auto",
                        target="id"
                    ).translate(clean_text)

                    st.write(translated)


                    st.markdown("### 🇬🇧 English Version")
                    st.markdown(
                        f"<div style='font-style:italic'>{translated}</div>",
                        unsafe_allow_html=True
        )


            # ===== KOMENTAR =====
            with col4:
                st.write("💬 Komentar")

            # ===== COMMENT LIST =====
            comments = pd.read_sql(
                "SELECT * FROM article_comments WHERE article_id=? ORDER BY created_at",
                conn,
                params=(r["id"],)
            )

            for _, c in comments.iterrows():
                st.markdown(
                    f"<div class='comment-box'><b>{c['username']}</b><br>{c['comment']}</div>",
                    unsafe_allow_html=True
                )

            # ===== ADD COMMENT =====
            comment = st.text_input(
                "Tulis komentar",
                key=f"c_{r['id']}"
            )

            if st.button("Kirim", key=f"send_c_{r['id']}"):
                if comment:
                    conn.execute("""
                        INSERT INTO article_comments
                        (article_id, username, comment, created_at)
                        VALUES (?, ?, ?, ?)
                    """, (
                        r["id"],
                        st.session_state.user,
                        comment,
                        datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    ))
                    conn.commit()
                    st.rerun()

            st.markdown("</div>", unsafe_allow_html=True)


        

import json
import matplotlib.pyplot as plt

if menu == "✍️ Artikel Saya":
    st.subheader("✍️ Tambah Artikel")

title = st.text_input("Judul Artikel")

font_family = st.selectbox(
    "Font Artikel",
    ["Default", "Serif", "Monospace"]
)

content = st.text_area(
    "Isi Artikel (Markdown didukung)",
    height=260,
    placeholder="""
## Judul Section
Paragraf biasa

### Tabel
| Nama | Nilai |
|------|------|
| A    | 90   |
"""
)

# ================= IMAGE / PDF =================
file = st.file_uploader(
    "Upload Gambar / PDF",
    type=["png", "jpg", "jpeg", "pdf"]
)

if file and file.type.startswith("image"):
    st.image(file, width=300)

# ================= CSV → GRAFIK =================
st.divider()
st.markdown("### 📊 Grafik dari CSV (Opsional)")

csv_file = st.file_uploader("Upload CSV", type=["csv"])

chart_config = None

if csv_file:
    df_csv = pd.read_csv(csv_file)
    st.dataframe(df_csv, use_container_width=True)

    c1, c2, c3, c4 = st.columns(4)

    with c1:
        x_col = st.selectbox("Kolom X", df_csv.columns)
    with c2:
        y_col = st.selectbox("Kolom Y", df_csv.columns)
    with c3:
        chart_type = st.selectbox("Jenis Grafik", ["Line", "Bar", "Area"])
    with c4:
        chart_color = st.color_picker("Warna", "#ff5da2")

    fig, ax = plt.subplots()
    if chart_type == "Line":
        ax.plot(df_csv[x_col], df_csv[y_col], color=chart_color)
    elif chart_type == "Bar":
        ax.bar(df_csv[x_col], df_csv[y_col], color=chart_color)
    else:
        ax.fill_between(df_csv[x_col], df_csv[y_col], color=chart_color, alpha=0.6)

    st.pyplot(fig)

    chart_config = {
        "x": x_col,
        "y": y_col,
        "type": chart_type,
        "color": chart_color,
        "csv": None
    }

    # ================= SIMPAN ARTIKEL =================
    if st.button("💾 Simpan Artikel", type="primary"):
        if not title or not content:
            st.warning("Judul dan isi wajib diisi")
            st.stop()

        attach = None

        if file:
            folder = "uploads/images" if file.type.startswith("image") else "uploads/pdfs"
            os.makedirs(folder, exist_ok=True)
            attach = f"{folder}/{datetime.now().timestamp()}_{file.name}"
            with open(attach, "wb") as f:
                f.write(file.getbuffer())

            if file.type.startswith("image"):
                content += f"\n\n![{file.name}]({attach})"

    if csv_file and chart_config:
        os.makedirs("uploads/csv", exist_ok=True)
        csv_path = f"uploads/csv/{datetime.now().timestamp()}_{csv_file.name}"
        with open(csv_path, "wb") as f:
            f.write(csv_file.getbuffer())
        chart_config["csv"] = csv_path

    font_css = ""
    if font_family == "Serif":
        font_css = "font-family:serif;"
    elif font_family == "Monospace":
        font_css = "font-family:monospace;"

    content = f"<div style='{font_css}'>{content}</div>"

    conn.execute("""
        INSERT INTO articles
        (title, content, author, attachment, chart_config, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (
        title,
        content,
        st.session_state.user,
        attach,
        json.dumps(chart_config) if chart_config else None,
        datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ))
    conn.commit()

    st.success("✅ Artikel berhasil ditambahkan")
    st.rerun()


    # =====================================================
    # ================= EDIT ARTIKEL ======================
    # =====================================================
    if st.session_state.edit_article_id:
        edit_id = st.session_state.edit_article_id

        a = pd.read_sql(
            "SELECT * FROM articles WHERE id=?",
            conn,
            params=(edit_id,)
        ).iloc[0]

        st.divider()
        st.subheader("✏️ Edit Artikel")

        with st.form("edit_form"):
            edit_title = st.text_input("Judul", a["title"])
            edit_content = st.text_area("Isi", a["content"], height=260)

            col1, col2 = st.columns(2)
            with col1:
                save = st.form_submit_button("💾 Simpan")
            with col2:
                cancel = st.form_submit_button("❌ Batal")

        if save:
            conn.execute("""
                UPDATE articles
                SET title=?, content=?, updated_at=?
                WHERE id=?
            """, (
                edit_title,
                edit_content,
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                edit_id
            ))
            conn.commit()

            st.session_state.edit_article_id = None
            st.success("✅ Artikel diperbarui")
            st.rerun()

        if cancel:
            st.session_state.edit_article_id = None
            st.rerun()

    # =====================================================
    # ================= LIST ARTIKEL ======================
    # =====================================================
    st.divider()
    st.subheader("📄 Daftar Artikel")

    if st.session_state.role in ["admin", "editor"]:
        articles = pd.read_sql(
            "SELECT * FROM articles ORDER BY created_at DESC",
            conn
        )
    else:
        articles = pd.read_sql(
            "SELECT * FROM articles WHERE author=? ORDER BY created_at DESC",
            conn,
            params=(st.session_state.user,)
        )

    for _, a in articles.iterrows():
        with st.expander(f"{a['title']} — ✍️ {a['author']}"):
            st.markdown(a["content"], unsafe_allow_html=True)

            col1, col2 = st.columns(2)

            with col1:
                if st.button("✏️ Edit", key=f"edit_{a['id']}"):
                    st.session_state.edit_article_id = a["id"]
                    st.rerun()

            with col2:
                if st.button("🗑️ Delete", key=f"del_{a['id']}"):
                    conn.execute(
                        "DELETE FROM articles WHERE id=?",
                        (a["id"],)
                    )
                    conn.commit()
                    st.success("🗑️ Artikel dihapus")
                    st.rerun()



if menu == chat_label:
    chat_ui(st.session_state.user)

if menu == "👥 User Management":
    user_management()

if menu == "👤 Profile":
    profile_page()

