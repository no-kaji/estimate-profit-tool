import streamlit as st

from app.auth import require_login
from app.db import init_db, get_session
from app.models import ROLE_SYSTEM_ADMIN
from app.seed import seed_if_empty
from app.ui import apply_theme

st.set_page_config(page_title="収支ワークフローツール", page_icon="📊", layout="wide")

init_db()
session = get_session()
seed_if_empty(session)
user = require_login(session)
apply_theme()

# ログイン中のユーザーの権限に応じて、左サイドバーに表示するページを出し分ける。
# 「このページはマネージャーのみ利用できます」という表示だけをして終わるページは、
# そもそもサイドバーに出す意味がないため、st.navigationで動的に絞り込む。
# アイコンはすべてMaterial Symbols(線形/アウトラインスタイル)で統一する。
pages = [
    st.Page("app_pages/00_ホーム.py", title="ホーム", icon=":material/home:", default=True),
    st.Page("app_pages/01_案件一覧.py", title="案件一覧", icon=":material/folder_open:"),
    st.Page("app_pages/02_見積入力.py", title="見積入力", icon=":material/edit_note:"),
    st.Page("app_pages/10_収支管理.py", title="収支管理", icon=":material/payments:"),
    st.Page("app_pages/11_経営ボード明細出力.py", title="データ連携", icon=":material/monitoring:"),
]
if user.role != ROLE_SYSTEM_ADMIN:
    pages.append(st.Page("app_pages/07_マイページ.py", title="マイページ", icon=":material/person:"))
if user.can_manage_company_seal:
    pages.append(st.Page("app_pages/08_社判管理.py", title="社判管理", icon=":material/approval:"))
if user.can_approve:
    pages.append(st.Page("app_pages/09_承認.py", title="承認", icon=":material/task_alt:"))
if user.can_manage_users:
    pages.append(st.Page("app_pages/05_マスタ管理.py", title="マスタ管理", icon=":material/tune:"))
    pages.append(st.Page("app_pages/06_システム管理.py", title="システム管理", icon=":material/admin_panel_settings:"))

session.close()

nav = st.navigation(pages)
nav.run()
