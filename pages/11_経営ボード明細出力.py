import io

import streamlit as st
from sqlalchemy import select

from app.auth import logout_button, require_login
from app.db import get_session, init_db
from app.models import FinancialRecord, Project
from app.services.board_export import build_board_dataframe
from app.ui import apply_theme

st.set_page_config(page_title="経営ボード明細出力 | 収支ワークフローツール", page_icon="📊", layout="wide")
init_db()
session = get_session()
user = require_login(session)
apply_theme()
logout_button()

st.title("経営ボード明細出力")
st.caption(
    "確定見積(予算)と週次実績(実績)を、経営ボード明細.xlsxと同じ列構成で出力します。"
    "現時点ではSharePoint/Power BIへの自動反映は行っていないため、出力したファイルを"
    "既存のSharePoint上のファイルへ手動で反映してください(自動連携はMicrosoft Graph APIの"
    "アプリ登録が必要なため別途検討中です)。"
)

projects = session.execute(select(Project).where(Project.deleted_at.is_(None))).scalars().all()
project_labels = {p.id: f"{p.project_name or '(未設定)'}({p.dept} / {p.client_name})" for p in projects}
selected_ids = st.multiselect(
    "対象案件(未選択の場合は全案件が対象)",
    options=list(project_labels.keys()),
    format_func=lambda i: project_labels[i],
)

query = select(FinancialRecord).where(FinancialRecord.record_type == "確定見積")
if selected_ids:
    query = query.where(FinancialRecord.project_id.in_(selected_ids))
records = session.execute(query).scalars().all()

st.write(f"対象の確定見積レコード数: {len(records)}")

if st.button("プレビューを生成", type="primary"):
    df = build_board_dataframe(session, records)
    st.session_state["_board_export_df"] = df

df = st.session_state.get("_board_export_df")
if df is not None:
    st.dataframe(df, use_container_width=True)

    excel_buffer = io.BytesIO()
    df.to_excel(excel_buffer, index=False, sheet_name="経営ボード明細")
    st.download_button(
        "Excelでダウンロード",
        data=excel_buffer.getvalue(),
        file_name="経営ボード明細_出力.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    st.download_button(
        "CSVでダウンロード",
        data=df.to_csv(index=False).encode("utf-8-sig"),
        file_name="経営ボード明細_出力.csv",
        mime="text/csv",
    )

session.close()
