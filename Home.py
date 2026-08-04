import streamlit as st

from app.db import init_db, get_session
from app.seed import seed_if_empty

st.set_page_config(page_title="見積収支計算書ツール", page_icon="📊", layout="wide")

init_db()
_session = get_session()
try:
    seed_if_empty(_session)
finally:
    _session.close()

st.title("見積収支計算書ツール")
st.caption("社内向け見積・収支管理ツール(開発中)")

st.markdown(
    """
左のサイドバーから各画面に移動してください。

- **01_案件一覧**: 案件の検索・新規登録・複製
- **02_見積入力**: 契約形式の選択 → 見積(概算/確定)・実績の明細入力、収支の自動計算
- **05_マスタ管理**: 契約形式・計算パターン・請求項目・キャンセルポリシー・法定福利費率マスタの編集

初回起動時に、契約形式・計算パターン・法定福利費率(令和7年度)・請求項目・キャンセルポリシーの
初期マスタデータを自動投入しています。
"""
)
