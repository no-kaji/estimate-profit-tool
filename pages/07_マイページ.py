import streamlit as st

from app.auth import logout_button, require_login
from app.db import get_session, init_db
from app.seal import generate_personal_seal_svg, seal_img_tag
from app.ui import apply_theme

st.set_page_config(page_title="マイページ | 収支ワークフローツール", page_icon="📊", layout="wide")
init_db()
session = get_session()
user = require_login(session)
apply_theme()
logout_button()

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

session.close()
