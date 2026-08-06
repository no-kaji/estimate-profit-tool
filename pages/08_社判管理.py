import streamlit as st
from sqlalchemy import select

from app.auth import logout_button, require_login
from app.db import get_session, init_db
from app.models import CompanySeal
from app.seal import generate_company_seal_svg, seal_img_tag
from app.ui import apply_theme

st.set_page_config(page_title="社判管理 | 収支ワークフローツール", page_icon="📊", layout="wide")
init_db()
session = get_session()
user = require_login(session)
apply_theme()
logout_button()

st.title("社判管理")

if not user.can_manage_company_seal:
    st.error("この画面はマネージャー・システム管理者のみ利用できます。")
    st.stop()

current = session.execute(select(CompanySeal).order_by(CompanySeal.registered_at.desc())).scalars().first()

st.write("承認された確定見積の見積書には、ここで登録した社判が自動的に配置されます。")

if current:
    st.markdown(seal_img_tag(current.svg, size=120), unsafe_allow_html=True)
    st.caption(f"登録者: {current.registered_by_id} / 登録日時: {current.registered_at}")
else:
    st.info("社判が未登録です。下のフォームから登録してください。")

st.divider()
with st.form("company_seal_form"):
    company_name = st.text_input("社判に表示する名称", value="会社印")
    submitted = st.form_submit_button("社判を生成して登録")
    if submitted:
        session.add(CompanySeal(svg=generate_company_seal_svg(company_name), registered_by_id=user.id))
        session.commit()
        st.success("社判を登録しました。")
        st.rerun()

session.close()
