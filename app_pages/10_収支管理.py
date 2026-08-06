import datetime as dt

import pandas as pd
import streamlit as st
from sqlalchemy import select

from app.auth import logout_button, require_login
from app.db import get_session, init_db
from app.models import FinancialRecord, Project, WeeklyActual
from app.ui import apply_theme

init_db()
session = get_session()
user = require_login(session)
apply_theme()
logout_button()

st.title("収支管理")
st.caption("確定見積を選び、実績値を週単位で入力します。月次に合算して経営ボード明細形式で出力できます。")

projects = session.execute(select(Project).where(Project.deleted_at.is_(None))).scalars().all()
if not projects:
    st.info("案件が登録されていません。先に案件と確定見積を作成してください。")
    st.stop()

project_labels = {p.id: f"{p.project_name or '(未設定)'}({p.dept} / {p.client_name})" for p in projects}
project_id = st.selectbox("案件", options=list(project_labels.keys()), format_func=lambda i: project_labels[i])

confirmed_records = session.execute(
    select(FinancialRecord).where(
        FinancialRecord.project_id == project_id,
        FinancialRecord.record_type == "確定見積",
    )
).scalars().all()

if not confirmed_records:
    st.info("この案件にはまだ確定見積がありません。「02_見積入力」で確定見積を作成してください。")
    st.stop()

record_labels = {
    r.id: f"{r.period_start or '期間未定'}〜{r.period_end or ''}({r.approval_status})" for r in confirmed_records
}
record_id = st.selectbox("対象の確定見積", options=list(record_labels.keys()), format_func=lambda i: record_labels[i])
record = session.get(FinancialRecord, record_id)

st.divider()
st.subheader("週次実績の入力")

week_start = st.date_input("対象週(その週の月曜日を選択)", value=dt.date.today())
week_start = week_start - dt.timedelta(days=week_start.weekday())  # 月曜日に丸める

existing = session.execute(
    select(WeeklyActual).where(WeeklyActual.financial_record_id == record.id, WeeklyActual.week_start == week_start)
).scalars().first()

with st.form("weekly_actual_form"):
    sales = st.number_input("売上高", min_value=0.0, step=1000.0, value=existing.sales if existing else 0.0, format="%.0f")
    cost = st.number_input("売上原価", min_value=0.0, step=1000.0, value=existing.cost if existing else 0.0, format="%.0f")
    sga_cost = st.number_input("販売管理費", min_value=0.0, step=1000.0, value=existing.sga_cost if existing else 0.0, format="%.0f")
    hc1, hc2 = st.columns(2)
    headcount_regular = hc1.number_input("常勤数", min_value=0, step=1, value=existing.headcount_regular if existing else 0)
    headcount_position = hc2.number_input("ポジ数", min_value=0, step=1, value=existing.headcount_position if existing else 0)
    submitted = st.form_submit_button("この週の実績を保存", type="primary")
    if submitted:
        if existing:
            existing.sales = sales
            existing.cost = cost
            existing.sga_cost = sga_cost
            existing.headcount_regular = headcount_regular
            existing.headcount_position = headcount_position
            existing.entered_by_id = user.id
        else:
            session.add(
                WeeklyActual(
                    financial_record_id=record.id,
                    week_start=week_start,
                    sales=sales,
                    cost=cost,
                    sga_cost=sga_cost,
                    headcount_regular=headcount_regular,
                    headcount_position=headcount_position,
                    entered_by_id=user.id,
                )
            )
        session.commit()
        st.success(f"{week_start} 週の実績を保存しました。")
        st.rerun()

st.divider()
st.subheader("入力済みの週次実績")
weeklies = session.execute(
    select(WeeklyActual).where(WeeklyActual.financial_record_id == record.id).order_by(WeeklyActual.week_start)
).scalars().all()

if not weeklies:
    st.info("まだ実績が入力されていません。")
else:
    df = pd.DataFrame(
        [
            {
                "週(月曜)": w.week_start,
                "売上高": w.sales,
                "売上原価": w.cost,
                "粗利": w.profit,
                "販管費": w.sga_cost,
                "常勤数": w.headcount_regular,
                "ポジ数": w.headcount_position,
                "入力者": w.entered_by.display_name if w.entered_by else "",
            }
            for w in weeklies
        ]
    )
    st.dataframe(df, use_container_width=True)

    total_actual_sales = sum(w.sales for w in weeklies)
    total_actual_cost = sum(w.cost for w in weeklies)
    m1, m2, m3 = st.columns(3)
    m1.metric("実績合計 売上高", f"¥{total_actual_sales:,.0f}")
    m2.metric("実績合計 売上原価", f"¥{total_actual_cost:,.0f}")
    m3.metric("実績合計 粗利", f"¥{total_actual_sales - total_actual_cost:,.0f}")

session.close()
