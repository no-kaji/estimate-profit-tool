import streamlit as st
from sqlalchemy import select

from app.auth import get_current_user, log_errors, logout_button, require_login
from app.db import init_db, get_session
from app.models import Notification
from app.seed import DEFAULT_ADMIN_PASSWORD, DEFAULT_ADMIN_USERNAME, seed_if_empty
from app.ui import apply_theme

st.set_page_config(page_title="収支ワークフローツール", page_icon="📊", layout="wide")

init_db()
session = get_session()
seed_if_empty(session)

user = require_login(session)
apply_theme()
with log_errors(session, "Home", user):
    logout_button()
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
                import datetime as _dt

                n.read_at = _dt.datetime.utcnow()
                session.commit()
                st.rerun()

    st.markdown(
        """
左のサイドバーから各画面に移動してください。

- **01_案件一覧**: 案件の検索・新規登録・複製・削除(権限に応じて)
- **02_見積入力**: 契約形式の選択 → 見積(概算/確定)の明細入力、収支の自動計算、承認フロー申請
- **05_マスタ管理**: 契約形式・計算パターン・請求項目・キャンセルポリシー・法定福利費率マスタの編集
- **06_システム管理**: (システム管理者のみ)ユーザー管理・エラーログ確認・削除済み案件の復旧
- **07_マイページ**: 個人印鑑の生成
- **08_社判管理**: (マネージャー・システム管理者のみ)社判の登録
- **09_承認**: (マネージャー・システム管理者のみ)確定見積の承認フロー処理

初回起動時に、契約形式・計算パターン・法定福利費率(令和7年度)・請求項目・キャンセルポリシーの
初期マスタデータを自動投入しています。
"""
    )

    if user.username == DEFAULT_ADMIN_USERNAME:
        st.warning(
            f"初期管理者アカウント(ID: {DEFAULT_ADMIN_USERNAME} / 初期パスワード: {DEFAULT_ADMIN_PASSWORD})でログインしています。"
            "06_システム管理からユーザーを作成し、初期パスワードは早めに変更してください。"
        )

session.close()
