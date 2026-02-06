import os
import pandas as pd
import streamlit as st
from streamlit_autorefresh import st_autorefresh
from datetime import datetime
from db import get_db

conn = get_db()

# =====================================================
# TOTAL UNREAD (UNTUK SIDEBAR)
# =====================================================
def unread_count(user):
    return conn.execute("""
        SELECT COUNT(*) FROM chat
        WHERE receiver=? AND is_read=0
    """, (user,)).fetchone()[0]


# =====================================================
# CHAT UI (ROOM + BUBBLE STYLE)
# =====================================================
def chat_ui(user):
    # auto refresh tiap 3 detik
    st_autorefresh(interval=3000, key="chat_refresh")

    # ================= CSS =================
    st.markdown("""
    <style>
    .chat-container {
        display: flex;
        flex-direction: column;
    }
    .bubble {
        padding:10px 14px;
        border-radius:16px;
        margin:6px 0;
        max-width:70%;
        word-wrap:break-word;
        font-size:14px;
    }
    .me {
        background:#ff5da2;
        color:white;
        margin-left:auto;
        border-bottom-right-radius:4px;
    }
    .other {
        background:#2a2f3a;
        color:white;
        margin-right:auto;
        border-bottom-left-radius:4px;
    }
    .time {
        font-size:10px;
        opacity:0.6;
        margin-top:2px;
        text-align:right;
    }
                          
    </style>
                
    """, unsafe_allow_html=True)
    st.markdown("""
    <style>
    .user-row {
        display:flex;
        align-items:center;
        gap:10px;
        padding:8px 10px;
        border-radius:10px;
        cursor:pointer;
        margin-bottom:6px;
        background:#1f2430;
    }
    .user-row:hover {
        background:#2a2f3a;
    }
    .user-avatar {
        width:36px;
        height:36px;
        border-radius:50%;
        object-fit:cover;
    }
    .user-name {
        flex:1;
        font-size:14px;
    }
    .unread {
        background:red;
        color:white;
        font-size:11px;
        padding:2px 6px;
        border-radius:12px;
    }
    </style>
    """, unsafe_allow_html=True)


    col_left, col_right = st.columns([1, 3])

    # ================= LEFT: ROOM LIST =================

    with col_left:
        st.subheader("💬 Chats")

        users = pd.read_sql("""
            SELECT username, avatar
            FROM users
            WHERE username != ?
            ORDER BY username
        """, conn, params=(user,))

        if "chat_target" not in st.session_state:
            st.session_state.chat_target = None

        for _, row in users.iterrows():
            u = row["username"]
            avatar = row["avatar"]

            badge = conn.execute("""
                SELECT COUNT(*) FROM chat
                WHERE receiver=? AND sender=? AND is_read=0
            """, (user, u)).fetchone()[0]

            colA, colB = st.columns([1, 5])

            with colA:
                if avatar and os.path.exists(avatar):
                    st.image(avatar, width=40)
                else:
                    st.image("https://via.placeholder.com/40", width=40)

            with colB:
                label = u
                if badge > 0:
                    label += f" 🔴{badge}"

                if st.button(label, key=f"user_{u}", use_container_width=True):
                    st.session_state.chat_target = u

                    conn.execute("""
                        UPDATE chat SET is_read=1
                        WHERE sender=? AND receiver=?
                    """, (u, user))
                    conn.commit()

    # ================= RIGHT: CHAT ROOM =================
    with col_right:
        target = st.session_state.chat_target

        if not target:
            st.info("👈 Pilih user untuk mulai chat")
            return

        st.subheader(f"💬 Chat dengan {target}")

        msgs = pd.read_sql("""
            SELECT * FROM chat
            WHERE (sender=? AND receiver=?)
               OR (sender=? AND receiver=?)
            ORDER BY created_at
        """, conn, params=(user, target, target, user))

        st.markdown("<div class='chat-container'>", unsafe_allow_html=True)

        for _, m in msgs.iterrows():
            is_me = m["sender"] == user
            cls = "me" if is_me else "other"

            # ===== MESSAGE BUBBLE =====
            st.markdown(
                f"""
                <div class="bubble {cls}">
                    {m["message"] or ""}
                """,
                unsafe_allow_html=True
            )

            # ===== ATTACHMENT =====
            # ===== ATTACHMENT =====
            if m["attachment"] and os.path.exists(m["attachment"]):
                ext = m["attachment"].lower()

                # 🖼️ IMAGE PREVIEW + DOWNLOAD
                if ext.endswith((".png", ".jpg", ".jpeg")):
                    st.image(m["attachment"], width=240)

                    with open(m["attachment"], "rb") as f:
                        st.download_button(
                            "⬇️ Download Image",
                            f,
                            file_name=os.path.basename(m["attachment"]),
                            mime="image/png",
                            key=f"img_{m['id']}"
                        )

                # 📄 PDF / FILE DOWNLOAD
                else:
                    with open(m["attachment"], "rb") as f:
                        st.download_button(
                            "📎 Download File",
                            f,
                            file_name=os.path.basename(m["attachment"]),
                            mime="application/pdf",
                            key=f"file_{m['id']}"
                        )


            # ===== READ RECEIPT =====
            if is_me:
                status = "✓✓" if m["is_read"] else "✓"
                st.markdown(
                    f"<div class='time'>{m['created_at']} {status}</div></div>",
                    unsafe_allow_html=True
                )
            else:
                st.markdown(
                    f"<div class='time'>{m['created_at']}</div></div>",
                    unsafe_allow_html=True
                )

        st.markdown("</div>", unsafe_allow_html=True)

        st.divider()

        # ================= INPUT =================
        msg = st.text_input("Tulis pesan", key="chat_msg")

        file = st.file_uploader(
            "Kirim file (image / pdf)",
            type=["png", "jpg", "jpeg", "pdf"],
            key="chat_file"
        )

        if st.button("Kirim"):
            attach = None

            if file:
                os.makedirs("uploads/chat", exist_ok=True)
                attach = f"uploads/chat/{datetime.now().timestamp()}_{file.name}"
                with open(attach, "wb") as f:
                    f.write(file.getbuffer())

            conn.execute("""
                INSERT INTO chat
                (sender, receiver, message, attachment, created_at, is_read)
                VALUES (?, ?, ?, ?, ?, 0)
            """, (
                user,
                target,
                msg if msg else None,
                attach,
                datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            ))
            conn.commit()

            st.rerun()
