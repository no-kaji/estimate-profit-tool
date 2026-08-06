import datetime as dt

import streamlit as st
from sqlalchemy import select

from app.auth import logout_button, require_login
from app.db import get_session, init_db
from app.models import CompanySeal, FinancialRecord, Notification
from app.seal import seal_img_tag
from app.ui import apply_theme

st.set_page_config(page_title="承認 | 収支ワークフローツール", page_icon="📊", layout="wide")
init_db()
session = get_session()
user = require_login(session)
apply_theme()
logout_button()

st.title("承認")
st.caption("確定見積の見積書発行に対する承認申請を確認できます。承認すると社判が配置され、申請者に通知されます。")

if not user.can_approve:
    st.error("この画面はマネージャー・システム管理者のみ利用できます。")
    st.stop()

company_seal = session.execute(select(CompanySeal).order_by(CompanySeal.registered_at.desc())).scalars().first()
if company_seal is None:
    st.warning("社判が未登録です。先に「08_社判管理」で社判を登録してください。承認は社判登録後に行えます。")

pending = session.execute(
    select(FinancialRecord).where(FinancialRecord.approval_status == "申請中")
).scalars().all()

if not pending:
    st.info("現在、承認待ちの申請はありません。")

for rec in pending:
    with st.container(border=True):
        c1, c2 = st.columns([3, 2])
        with c1:
            st.markdown(f"**{rec.project.project_name}**({rec.project.client_name} / {rec.project.dept})")
            st.caption(f"申請者: {rec.requested_by.display_name if rec.requested_by else '不明'} / 申請日時: {rec.requested_at}")
            if rec.requested_by and rec.requested_by.seal_svg:
                st.markdown(seal_img_tag(rec.requested_by.seal_svg, size=60), unsafe_allow_html=True)
        with c2:
            reason = st.text_input("却下理由(却下する場合のみ入力)", key=f"reason_{rec.id}")
            b1, b2 = st.columns(2)
            if b1.button("承認する", key=f"approve_{rec.id}", type="primary", disabled=company_seal is None):
                rec.approval_status = "承認済み"
                rec.approved_by_id = user.id
                rec.approved_at = dt.datetime.utcnow()
                if rec.requested_by_id:
                    session.add(
                        Notification(
                            user_id=rec.requested_by_id,
                            message=f"「{rec.project.project_name}」の見積書が承認され、社判が配置されました。",
                        )
                    )
                session.commit()
                st.success("承認しました。")
                st.rerun()
            if b2.button("却下する", key=f"reject_{rec.id}"):
                rec.approval_status = "却下"
                rec.approved_by_id = user.id
                rec.approved_at = dt.datetime.utcnow()
                rec.reject_reason = reason or "(理由未記入)"
                if rec.requested_by_id:
                    session.add(
                        Notification(
                            user_id=rec.requested_by_id,
                            message=f"「{rec.project.project_name}」の見積書申請が却下されました。理由: {rec.reject_reason}",
                        )
                    )
                session.commit()
                st.warning("却下しました。")
                st.rerun()

session.close()
