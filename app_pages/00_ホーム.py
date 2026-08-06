import datetime as dt

import streamlit as st
from sqlalchemy import select

from app.auth import log_errors, logout_button, require_login
from app.db import get_session, init_db
from app.models import Notification
from app.seed import DEFAULT_ADMIN_PASSWORD, DEFAULT_ADMIN_USERNAME
from app.ui import apply_theme

init_db()
session = get_session()
user = require_login(session)
apply_theme()
logout_button()

with log_errors(session, "00_ホーム", user):
    st.title("収支ワークフローツール")
    st.caption(f"ログイン中: {user.display_name}({user.role})")

    unread = session.execute(
        select(Notification).where(Notification.user_id == user.id, Notification.read_at.is_(None)).order_by(Notification.created_at.desc())
    ).scalars().all()
    if unread:
        st.subheader("通知")
        for n in unread:
            nc1, nc2 = st.columns([5, 1])
            nc1.info(f"{n.created_at}: {n.message}")
            if nc2.button("既読にする", key=f"read_{n.id}"):
                n.read_at = dt.datetime.utcnow()
                session.commit()
                st.rerun()

    st.markdown(
        """
左のサイドバーから各画面に移動してください(あなたの権限に応じたメニューのみ表示されます)。

- **案件一覧**: 案件の検索・新規登録・複製・削除(権限に応じて)
- **見積入力**: 契約形式の選択 → 見積(概算/確定)の明細入力、収支の自動計算、承認フロー申請
- **マスタ管理**: 契約形式・計算パターン・請求項目・キャンセルポリシー・法定福利費率マスタの編集
- **収支管理**: 確定見積を選んで週次実績を入力
- **経営ボード明細出力**: 確定見積・週次実績を経営ボード明細形式で出力

初回起動時に、契約形式・計算パターン・法定福利費率(令和7年度)・請求項目・キャンセルポリシーの
初期マスタデータを自動投入しています。
"""
    )

    if user.username == DEFAULT_ADMIN_USERNAME:
        st.warning(
            f"初期管理者アカウント(ID: {DEFAULT_ADMIN_USERNAME} / 初期パスワード: {DEFAULT_ADMIN_PASSWORD})でログインしています。"
            "システム管理からユーザーを作成し、初期パスワードは早めに変更してください。"
        )
        st.info(
            "動作確認用のサンプルアカウントも自動投入されています。\n\n"
            "- マネージャー: ID `manager1` / パスワード `manager123`\n"
            "- ユーザー: ID `user1` / パスワード `user123`\n\n"
            "この2アカウントは同じ拠点に所属しているため、承認フロー(ユーザーが申請しマネージャーが"
            "承認する)をすぐに試せます。なお現在の構成ではアプリの再起動のたびにデータが消えるため、"
            "これらのサンプルアカウントは毎回自動的に再作成されます。"
        )

session.close()
