import streamlit as st
from sqlalchemy import select

from app.auth import logout_button, require_login
from app.db import get_session, init_db
from app.models import ROLE_SYSTEM_ADMIN, FinancialRecord
from app.seal import generate_personal_seal_svg, seal_img_tag
from app.ui import apply_theme

st.set_page_config(page_title="マイページ | 収支ワークフローツール", page_icon="📊", layout="wide")
init_db()
session = get_session()
user = require_login(session)
apply_theme()
logout_button()

if user.role == ROLE_SYSTEM_ADMIN:
    st.title("マイページ")
    st.info("システム管理者はユーザー管理から各ユーザーの登録状況(印鑑等)を確認できます。マイページは対象外です。")
    st.stop()

st.title("マイページ")
st.caption(f"{user.display_name}({user.role}) / ID: {user.username}")

st.subheader("個人印鑑")
st.write("確定見積の承認申請時に、この印鑑があなたの承認印として見積書に配置されます。")

if user.seal_svg:
    st.markdown(seal_img_tag(user.seal_svg, size=110), unsafe_allow_html=True)
    st.caption("現在登録されている個人印鑑です。")
else:
    st.info("まだ個人印鑑が生成されていません。下のボタンから生成してください。")

if st.button("個人印鑑を生成 / 再生成"):
    user.seal_svg = generate_personal_seal_svg(user.display_name or user.username)
    session.commit()
    st.success("個人印鑑を生成しました。")
    st.rerun()

st.divider()
st.subheader("自分が作成した見積もりの履歴")

my_records = session.execute(
    select(FinancialRecord)
    .where(FinancialRecord.created_by_id == user.id, FinancialRecord.deleted_at.is_(None))
    .order_by(FinancialRecord.updated_at.desc())
).scalars().all()

badge_map = {"下書き": "⚪ 下書き", "申請中": "🟡 承認申請中", "承認済み": "🟢 承認済み", "却下": "🔴 却下"}

if not my_records:
    st.info("まだ作成した見積もりがありません。")
else:
    for rec in my_records:
        with st.container(border=True):
            c1, c2 = st.columns([3, 2])
            with c1:
                st.markdown(f"**{rec.project.project_name or '(案件名未設定)'}**({rec.project.client_name})")
                st.caption(f"{rec.record_type} / 更新日時: {rec.updated_at}")
            with c2:
                status_label = badge_map.get(rec.approval_status, rec.approval_status) if rec.record_type == "確定見積" else ""
                if status_label:
                    st.write(status_label)
                if rec.record_type == "確定見積" and rec.approval_status == "却下" and rec.reject_reason:
                    st.caption(f"却下理由: {rec.reject_reason}")
                if st.button("開く", key=f"open_myrec_{rec.id}"):
                    st.session_state["current_project_id"] = rec.project_id
                    st.session_state["estimate_step"] = "detail"
                    st.session_state["selected_contract_type_id"] = rec.contract_type_id
                    st.session_state["editing_record_id"] = rec.id
                    st.switch_page("pages/02_見積入力.py")

session.close()
