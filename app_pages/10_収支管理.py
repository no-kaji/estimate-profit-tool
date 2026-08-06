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
st.caption(
    "収支管理は「受注した」確定見積に対して実績を入力する仕組みです。"
    "まずマネージャーが承認した確定見積ごとに受注/失注を選び、受注したものだけを対象に週次実績を入力します。"
)

# ---------------------------------------------------------------
# Step 1: 確定見積一覧 → 受注/失注を選択
# 対象はマネージャーが承認済みの確定見積のみ(未承認・却下のものは収支管理の対象外)。
# ---------------------------------------------------------------
st.subheader("Step 1. 確定見積一覧(受注・失注の選択)")

all_confirmed = session.execute(
    select(FinancialRecord).where(
        FinancialRecord.record_type == "確定見積",
        FinancialRecord.approval_status == "承認済み",
        FinancialRecord.deleted_at.is_(None),
    )
).scalars().all()

if not all_confirmed:
    st.info("承認済みの確定見積がまだありません。マネージャーの承認後、ここに表示されます。")
    st.stop()


@st.dialog("受注の確定")
def _confirm_won_dialog(record_id: int):
    rec = session.get(FinancialRecord, record_id)
    st.write(f"「{rec.project.project_name}」({rec.project.client_name})を**受注**として記録しますか?")
    c1, c2 = st.columns(2)
    if c1.button("受注として確定する", type="primary", use_container_width=True):
        rec.order_result = "受注"
        rec.lost_reason = None
        session.commit()
        st.rerun()
    if c2.button("キャンセル", use_container_width=True):
        st.rerun()


@st.dialog("失注の確定")
def _confirm_lost_dialog(record_id: int):
    rec = session.get(FinancialRecord, record_id)
    st.write(f"「{rec.project.project_name}」({rec.project.client_name})を**失注**として記録します。")
    reason = st.text_area("失注理由", placeholder="例: 価格競合に敗れた / 予算未確保 など")
    c1, c2 = st.columns(2)
    if c1.button("失注として確定する", type="primary", use_container_width=True):
        if not reason:
            st.error("失注理由を入力してください。")
        else:
            rec.order_result = "失注"
            rec.lost_reason = reason
            session.commit()
            st.rerun()
    if c2.button("キャンセル", use_container_width=True):
        st.rerun()


status_badge = {"未定": "⚪ 未定", "受注": "🟢 受注", "失注": "🔴 失注"}
for rec in all_confirmed:
    with st.container(border=True):
        c1, c2, c3 = st.columns([3, 2, 2])
        with c1:
            st.markdown(f"**{rec.project.project_name or '(案件名未設定)'}**({rec.project.client_name})")
            st.caption(f"{rec.period_start or '期間未定'}〜{rec.period_end or ''} / 承認: {rec.approval_status}")
        with c2:
            st.write(status_badge.get(rec.order_result, rec.order_result))
            if rec.order_result == "失注" and rec.lost_reason:
                st.caption(f"理由: {rec.lost_reason}")
        with c3:
            if rec.order_result == "未定":
                b1, b2 = st.columns(2)
                if b1.button("受注", key=f"won_{rec.id}", type="primary"):
                    _confirm_won_dialog(rec.id)
                if b2.button("失注", key=f"lost_{rec.id}"):
                    _confirm_lost_dialog(rec.id)
            else:
                if st.button("未定に戻す", key=f"reset_{rec.id}"):
                    rec.order_result = "未定"
                    rec.lost_reason = None
                    session.commit()
                    st.rerun()

# ---------------------------------------------------------------
# Step 2: 受注した案件を選び、週次実績を入力
# ---------------------------------------------------------------
st.divider()
st.subheader("Step 2. 週次実績の入力(受注した案件のみ)")

won_records = [r for r in all_confirmed if r.order_result == "受注"]
if not won_records:
    st.info("受注として確定した確定見積がまだありません。上の一覧で「受注」を選ぶと、ここに対象が表示されます。")
    session.close()
    st.stop()

record_labels = {
    r.id: f"{r.project.project_name}({r.project.client_name}) / {r.period_start or '期間未定'}〜{r.period_end or ''}"
    for r in won_records
}
record_id = st.selectbox("対象の確定見積(受注済み)", options=list(record_labels.keys()), format_func=lambda i: record_labels[i])
record = session.get(FinancialRecord, record_id)

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
