import streamlit as st

from app.auth import get_current_user, log_errors, logout_button, require_login
from app.db import init_db, get_session
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

    st.markdown(
        """
左のサイドバーから各画面に移動してください。

- **01_案件一覧**: 案件の検索・新規登録・複製・削除(権限に応じて)
- **02_見積入力**: 契約形式の選択 → 見積(概算/確定)・実績の明細入力、収支の自動計算
- **05_マスタ管理**: 契約形式・計算パターン・請求項目・キャンセルポリシー・法定福利費率マスタの編集
- **06_システム管理**: (システム管理者のみ)ユーザー管理・エラーログ確認・削除済み案件の復旧

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
