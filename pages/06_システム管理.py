import streamlit as st
from sqlalchemy import select

from app.auth import hash_password, logout_button, require_login
from app.db import get_session, init_db
from app.models import ROLES, BranchMaster, ErrorLog, HeadquartersMaster, User
from app.ui import apply_theme

st.set_page_config(page_title="システム管理 | 収支ワークフローツール", page_icon="📊", layout="wide")
init_db()
session = get_session()
user = require_login(session)
apply_theme()
logout_button()

st.title("システム管理")

if not user.can_manage_users:
    st.error("この画面はシステム管理者のみ利用できます。")
    st.stop()

tab_users, tab_org, tab_logs = st.tabs(["ユーザー管理", "組織属性マスタ", "エラーログ"])

# ---------------------------------------------------------------
# ユーザー管理
# ---------------------------------------------------------------
with tab_users:
    st.subheader("ユーザー一覧")
    headquarters = session.execute(select(HeadquartersMaster)).scalars().all()
    branches = session.execute(select(BranchMaster)).scalars().all()
    hq_options = {h.id: h.name for h in headquarters}
    branch_options = {b.id: b.name for b in branches}

    users = session.execute(select(User)).scalars().all()
    for u in users:
        with st.container(border=True):
            c1, c2, c3, c4 = st.columns([2, 2, 2, 2])
            c1.markdown(f"**{u.username}**")
            c1.caption(u.display_name)
            new_role = c2.selectbox("ロール", options=ROLES, index=ROLES.index(u.role), key=f"role_{u.id}")
            new_hq = c3.selectbox(
                "統括部門",
                options=[None] + list(hq_options.keys()),
                format_func=lambda i: "未設定" if i is None else hq_options[i],
                index=(0 if u.headquarters_id is None else list(hq_options.keys()).index(u.headquarters_id) + 1),
                key=f"hq_{u.id}",
            )
            new_branch = c4.selectbox(
                "拠点",
                options=[None] + list(branch_options.keys()),
                format_func=lambda i: "未設定" if i is None else branch_options[i],
                index=(0 if u.branch_id is None else list(branch_options.keys()).index(u.branch_id) + 1),
                key=f"branch_{u.id}",
            )
            b1, b2, b3 = st.columns(3)
            if b1.button("有効/無効切替", key=f"toggle_active_{u.id}"):
                u.active = not u.active
                session.commit()
                st.rerun()
            st.caption("状態: " + ("有効" if u.active else "無効"))
            if b2.button("保存", key=f"save_user_{u.id}"):
                u.role = new_role
                u.headquarters_id = new_hq
                u.branch_id = new_branch
                session.commit()
                st.success("保存しました。")
                st.rerun()
            new_pw = b3.text_input("新しいパスワード", type="password", key=f"pw_{u.id}")
            if new_pw and st.button("パスワードを再設定", key=f"reset_pw_{u.id}"):
                u.password_hash = hash_password(new_pw)
                session.commit()
                st.success("パスワードを再設定しました。")

    st.divider()
    st.subheader("新規ユーザー登録")
    with st.form("new_user_form"):
        username = st.text_input("ユーザーID")
        display_name = st.text_input("表示名")
        password = st.text_input("初期パスワード", type="password")
        role = st.selectbox("ロール", options=ROLES)
        hq_id = st.selectbox("統括部門", options=[None] + list(hq_options.keys()), format_func=lambda i: "未設定" if i is None else hq_options[i])
        branch_id = st.selectbox("拠点", options=[None] + list(branch_options.keys()), format_func=lambda i: "未設定" if i is None else branch_options[i])
        if st.form_submit_button("登録"):
            if username and password:
                session.add(
                    User(
                        username=username,
                        display_name=display_name,
                        password_hash=hash_password(password),
                        role=role,
                        headquarters_id=hq_id,
                        branch_id=branch_id,
                    )
                )
                session.commit()
                st.success("登録しました。")
                st.rerun()
            else:
                st.error("ユーザーIDと初期パスワードは必須です。")

# ---------------------------------------------------------------
# 組織属性マスタ(統括部門・拠点)
# ---------------------------------------------------------------
with tab_org:
    col_hq, col_branch = st.columns(2)
    with col_hq:
        st.subheader("統括部門名称マスタ")
        for h in headquarters:
            st.write(f"- {h.name}")
        with st.form("new_hq_form"):
            name = st.text_input("新しい統括部門名称")
            if st.form_submit_button("追加"):
                if name:
                    session.add(HeadquartersMaster(name=name))
                    session.commit()
                    st.rerun()
    with col_branch:
        st.subheader("拠点名称マスタ")
        for b in branches:
            st.write(f"- {b.name}")
        with st.form("new_branch_form"):
            name = st.text_input("新しい拠点名称")
            if st.form_submit_button("追加"):
                if name:
                    session.add(BranchMaster(name=name))
                    session.commit()
                    st.rerun()

# ---------------------------------------------------------------
# エラーログ
# ---------------------------------------------------------------
with tab_logs:
    st.subheader("エラーログ(新しい順・直近200件)")
    logs = session.execute(select(ErrorLog).order_by(ErrorLog.occurred_at.desc()).limit(200)).scalars().all()
    if not logs:
        st.info("記録されたエラーはありません。")
    for log in logs:
        with st.expander(f"{log.occurred_at} / {log.page} / {log.user.display_name if log.user else '(未ログイン)'}"):
            st.code(log.message)

session.close()
