import datetime as dt

import streamlit as st
from sqlalchemy import select

from app.auth import log_errors, logout_button, require_login
from app.db import get_session, init_db
from app.models import CostLine, FinancialRecord, LineItem, Project
from app.ui import apply_theme

st.set_page_config(page_title="案件一覧 | 収支ワークフローツール", page_icon="📊", layout="wide")
init_db()
session = get_session()
user = require_login(session)
apply_theme()
logout_button()

st.title("案件一覧")
st.caption("部署・クライアント・案件番号・案件名で絞り込み、案件をクリックすると見積入力画面へ移動します。")

with log_errors(session, "01_案件一覧", user):
    show_trash = False
    if user.can_restore:
        show_trash = st.toggle("削除済み案件(ゴミ箱)を表示", value=False)

    with st.expander("検索条件", expanded=True):
        col1, col2, col3 = st.columns(3)
        f_dept = col1.text_input("部署")
        f_client = col2.text_input("クライアント名")
        f_no = col3.text_input("案件番号")

    st.divider()

    if not show_trash and st.button("＋ 新規案件登録", type="primary"):
        st.session_state["show_new_project_form"] = True

    if st.session_state.get("show_new_project_form"):
        with st.form("new_project_form"):
            st.subheader("新規案件登録")
            dept = st.text_input("部署")
            client_name = st.text_input("クライアント名")
            project_no = st.text_input("案件番号")
            project_name = st.text_input("案件名")
            submitted = st.form_submit_button("登録して見積作成に進む")
            if submitted:
                project = Project(dept=dept, client_name=client_name, project_no=project_no, project_name=project_name)
                session.add(project)
                session.commit()
                st.session_state["current_project_id"] = project.id
                st.session_state["estimate_step"] = "contract_type"
                st.session_state["show_new_project_form"] = False
                st.switch_page("pages/02_見積入力.py")

    query = select(Project)
    query = query.where(Project.deleted_at.is_not(None)) if show_trash else query.where(Project.deleted_at.is_(None))
    if f_dept:
        query = query.where(Project.dept.ilike(f"%{f_dept}%"))
    if f_client:
        query = query.where(Project.client_name.ilike(f"%{f_client}%"))
    if f_no:
        query = query.where(Project.project_no.ilike(f"%{f_no}%"))

    projects = session.execute(query).scalars().all()

    if not projects:
        st.info("削除済みの案件はありません。" if show_trash else "案件がまだ登録されていません。「＋ 新規案件登録」から作成してください。")
    else:
        for project in projects:
            records = session.execute(
                select(FinancialRecord).where(FinancialRecord.project_id == project.id)
            ).scalars().all()
            draft_n = sum(1 for r in records if r.record_type == "概算見積")
            confirmed_n = sum(1 for r in records if r.record_type == "確定見積")
            approved_n = sum(1 for r in records if r.approval_status == "承認済み")

            with st.container(border=True):
                c1, c2, c3 = st.columns([3, 2, 3])
                with c1:
                    st.markdown(f"**{project.project_name or '(案件名未設定)'}**")
                    st.caption(f"{project.dept} / {project.client_name} / {project.project_no}")
                with c2:
                    badges = []
                    if draft_n:
                        badges.append(f"概算 ×{draft_n}")
                    if confirmed_n:
                        badges.append(f"確定 ×{confirmed_n}")
                    if approved_n:
                        badges.append(f"承認済み ×{approved_n}")
                    st.write(" / ".join(badges) if badges else "レコードなし")
                with c3:
                    if show_trash:
                        if st.button("復旧", key=f"restore_{project.id}"):
                            project.deleted_at = None
                            session.commit()
                            st.success("復旧しました。")
                            st.rerun()
                        continue

                    n_buttons = 2 + (1 if user.can_delete else 0)
                    btn_cols = st.columns(n_buttons)
                    if btn_cols[0].button("開く", key=f"open_{project.id}"):
                        st.session_state["current_project_id"] = project.id
                        st.session_state["estimate_step"] = "contract_type"
                        st.switch_page("pages/02_見積入力.py")
                    if btn_cols[1].button("複製", key=f"dup_{project.id}"):
                        new_project = Project(
                            dept=project.dept,
                            client_name=project.client_name,
                            project_no=project.project_no + "-COPY",
                            project_name=(project.project_name or "") + "(コピー)",
                            contract_start=project.contract_start,
                            contract_end=project.contract_end,
                            copied_from_project_id=project.id,
                        )
                        session.add(new_project)
                        session.flush()
                        for rec in records:
                            new_rec = FinancialRecord(
                                project_id=new_project.id,
                                record_type=rec.record_type,
                                contract_type_id=rec.contract_type_id,
                                copied_from_id=rec.id,
                                period_start=rec.period_start,
                                period_end=rec.period_end,
                                cancellation_policy_id=rec.cancellation_policy_id,
                                sga_cost=rec.sga_cost,
                                segment=rec.segment,
                                product=rec.product,
                                region=rec.region,
                                order_status=rec.order_status,
                                unit_name=rec.unit_name,
                                headquarters_name=rec.headquarters_name,
                            )
                            session.add(new_rec)
                            session.flush()
                            for li in rec.line_items:
                                session.add(
                                    LineItem(
                                        financial_record_id=new_rec.id,
                                        billing_item_id=li.billing_item_id,
                                        billing_item_name_free=li.billing_item_name_free,
                                        insurance_status=li.insurance_status,
                                        headcount=li.headcount,
                                        employment_type=li.employment_type,
                                        remarks=li.remarks,
                                        billing_daily_rate=li.billing_daily_rate,
                                        billing_hourly_rate=li.billing_hourly_rate,
                                        billing_days=li.billing_days,
                                        billing_commute_monthly=li.billing_commute_monthly,
                                        billing_admin_fee_monthly=li.billing_admin_fee_monthly,
                                        billing_allowance_monthly=li.billing_allowance_monthly,
                                        payment_pricing_pattern_id=li.payment_pricing_pattern_id,
                                        payment_rate=li.payment_rate,
                                        payment_qty1=li.payment_qty1,
                                        payment_qty2=li.payment_qty2,
                                        payment_qty3=li.payment_qty3,
                                        payment_commute_monthly=li.payment_commute_monthly,
                                        payment_allowance_monthly=li.payment_allowance_monthly,
                                        standard_hours_daily=li.standard_hours_daily,
                                        standard_hours_monthly=li.standard_hours_monthly,
                                        overtime_hours_monthly=li.overtime_hours_monthly,
                                        night_overtime_hours_monthly=li.night_overtime_hours_monthly,
                                        unbilled_leave_hours_monthly=li.unbilled_leave_hours_monthly,
                                    )
                                )
                            for cl in rec.cost_lines:
                                session.add(
                                    CostLine(
                                        financial_record_id=new_rec.id,
                                        category=cl.category,
                                        billing_pricing_pattern_id=cl.billing_pricing_pattern_id,
                                        billing_rate=cl.billing_rate,
                                        billing_qty1=cl.billing_qty1,
                                        billing_qty2=cl.billing_qty2,
                                        billing_qty3=cl.billing_qty3,
                                        cost_pricing_pattern_id=cl.cost_pricing_pattern_id,
                                        cost_rate=cl.cost_rate,
                                        cost_qty1=cl.cost_qty1,
                                        cost_qty2=cl.cost_qty2,
                                        cost_qty3=cl.cost_qty3,
                                        timing=cl.timing,
                                    )
                                )
                        session.commit()
                        st.success("案件情報と配下の見積明細をまるごと複製しました(週次実績は複製されません)。")
                        st.rerun()
                    if user.can_delete:
                        if btn_cols[2].button("削除", key=f"del_{project.id}"):
                            project.deleted_at = dt.datetime.utcnow()
                            session.commit()
                            st.success(
                                "削除しました(論理削除)。"
                                + ("システム管理者が復旧できます。" if not user.can_restore else "")
                            )
                            st.rerun()

session.close()
