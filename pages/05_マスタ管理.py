import pandas as pd
import streamlit as st
from sqlalchemy import select

from app.auth import logout_button, require_login
from app.db import get_session, init_db
from app.models import (
    BillingItemMaster,
    CancellationPolicyMaster,
    ContractType,
    ContractTypePattern,
    InsuranceRateMaster,
    PricingPattern,
)
from app.ui import apply_theme

st.set_page_config(page_title="マスタ管理 | 見積収支計算書ツール", page_icon="📊", layout="wide")
init_db()
session = get_session()
user = require_login(session)
apply_theme()
logout_button()

st.title("マスタ管理")

tab_contract, tab_billing, tab_policy, tab_insurance = st.tabs(
    ["契約形式・計算パターン", "請求項目", "キャンセルポリシー", "法定福利費率"]
)

# ---------------------------------------------------------------
# 契約形式・計算パターン
# ---------------------------------------------------------------
with tab_contract:
    st.subheader("計算パターン")
    st.caption("契約形式・経費行から選択できる「単価×数量」の計算パターンです。数量ラベルは空欄で構いません(その項目は使わないパターンになります)。")

    patterns = session.execute(select(PricingPattern)).scalars().all()
    pattern_df = pd.DataFrame(
        [{"名称": p.name, "数量1ラベル": p.qty1_label or "", "数量2ラベル": p.qty2_label or "", "数量3ラベル": p.qty3_label or ""} for p in patterns]
    )
    edited_patterns = st.data_editor(pattern_df, num_rows="dynamic", use_container_width=True, key="pattern_editor")

    if st.button("計算パターンを保存"):
        existing_by_name = {p.name: p for p in patterns}
        seen = set()
        for _, row in edited_patterns.iterrows():
            name = row["名称"]
            if not name:
                continue
            seen.add(name)
            p = existing_by_name.get(name)
            if p is None:
                p = PricingPattern(name=name)
                session.add(p)
            p.qty1_label = row["数量1ラベル"] or None
            p.qty2_label = row["数量2ラベル"] or None
            p.qty3_label = row["数量3ラベル"] or None
        for name, p in existing_by_name.items():
            if name not in seen:
                session.delete(p)
        session.commit()
        st.success("計算パターンを保存しました。")
        st.rerun()

    st.divider()
    st.subheader("契約形式")
    contract_types = session.execute(select(ContractType)).scalars().all()
    all_pattern_names = [p.name for p in session.execute(select(PricingPattern)).scalars().all()]

    ct_df = pd.DataFrame(
        [{"名称": c.name, "説明": c.description, "使用可能な計算パターン": ", ".join(p.name for p in c.patterns)} for c in contract_types]
    )
    st.dataframe(ct_df, use_container_width=True)

    st.caption("契約形式ごとの計算パターン紐付けを編集します。")
    for ct in contract_types:
        with st.expander(f"{ct.name} の計算パターン"):
            current = {p.name for p in ct.patterns}
            selected = st.multiselect("使用可能な計算パターン", options=all_pattern_names, default=list(current), key=f"ct_patterns_{ct.id}")
            if st.button("この契約形式の紐付けを保存", key=f"save_ct_{ct.id}"):
                session.query(ContractTypePattern).filter(ContractTypePattern.contract_type_id == ct.id).delete()
                pattern_by_name = {p.name: p for p in session.execute(select(PricingPattern)).scalars().all()}
                for name in selected:
                    session.add(ContractTypePattern(contract_type_id=ct.id, pricing_pattern_id=pattern_by_name[name].id))
                session.commit()
                st.success("保存しました。")
                st.rerun()

    with st.form("new_contract_type"):
        st.write("新しい契約形式を追加")
        new_name = st.text_input("名称")
        new_desc = st.text_input("説明")
        if st.form_submit_button("追加"):
            if new_name:
                session.add(ContractType(name=new_name, description=new_desc))
                session.commit()
                st.rerun()

# ---------------------------------------------------------------
# 請求項目マスタ
# ---------------------------------------------------------------
with tab_billing:
    st.subheader("請求項目マスタ")
    items = session.execute(select(BillingItemMaster)).scalars().all()
    items_df = pd.DataFrame([{"項目名": i.item_name, "区分": i.category, "詳細": i.item_detail} for i in items])
    edited_items = st.data_editor(items_df, num_rows="dynamic", use_container_width=True, key="billing_item_editor")
    if st.button("請求項目マスタを保存"):
        existing_by_name = {i.item_name: i for i in items}
        seen = set()
        for _, row in edited_items.iterrows():
            if not row["項目名"]:
                continue
            seen.add(row["項目名"])
            item = existing_by_name.get(row["項目名"])
            if item is None:
                item = BillingItemMaster(item_name=row["項目名"])
                session.add(item)
            item.category = row["区分"] or ""
            item.item_detail = row["詳細"] or ""
        for name, item in existing_by_name.items():
            if name not in seen:
                session.delete(item)
        session.commit()
        st.success("保存しました。")
        st.rerun()

# ---------------------------------------------------------------
# キャンセルポリシーマスタ
# ---------------------------------------------------------------
with tab_policy:
    st.subheader("キャンセルポリシーマスタ")
    policies = session.execute(select(CancellationPolicyMaster)).scalars().all()
    for p in policies:
        with st.expander(p.policy_name):
            st.text_area("顧客向け記載内容", value=p.policy_text_client, key=f"policy_client_{p.id}")
            st.text_area("社内向け記載内容", value=p.policy_text_internal, key=f"policy_internal_{p.id}")
            if st.button("保存", key=f"save_policy_{p.id}"):
                p.policy_text_client = st.session_state[f"policy_client_{p.id}"]
                p.policy_text_internal = st.session_state[f"policy_internal_{p.id}"]
                session.commit()
                st.success("保存しました。")

    with st.form("new_policy"):
        st.write("新しいキャンセルポリシーを追加")
        name = st.text_input("ポリシー名")
        client_text = st.text_area("顧客向け記載内容")
        internal_text = st.text_area("社内向け記載内容")
        if st.form_submit_button("追加"):
            if name:
                session.add(CancellationPolicyMaster(policy_name=name, policy_text_client=client_text, policy_text_internal=internal_text))
                session.commit()
                st.rerun()

# ---------------------------------------------------------------
# 法定福利費率マスタ
# ---------------------------------------------------------------
with tab_insurance:
    st.subheader("法定福利費率マスタ(年度別)")
    st.caption("年度は西暦(会計年度の開始年、例: 令和7年度=2025)で管理します。")
    rates = session.execute(select(InsuranceRateMaster)).scalars().all()
    rates_df = pd.DataFrame(
        [
            {
                "年度(西暦)": r.fiscal_year,
                "健保": r.health_insurance_rate,
                "介護": r.nursing_care_rate,
                "年金": r.pension_rate,
                "児童拠出": r.child_allowance_rate,
                "雇保": r.employment_insurance_rate,
                "労災": r.workers_comp_rate,
                "一般拠出": r.general_contribution_rate,
            }
            for r in rates
        ]
    )
    edited_rates = st.data_editor(rates_df, num_rows="dynamic", use_container_width=True, key="insurance_editor")
    if st.button("法定福利費率マスタを保存"):
        existing_by_year = {r.fiscal_year: r for r in rates}
        seen = set()
        for _, row in edited_rates.iterrows():
            year = int(row["年度(西暦)"]) if row["年度(西暦)"] else None
            if year is None:
                continue
            seen.add(year)
            r = existing_by_year.get(year)
            if r is None:
                r = InsuranceRateMaster(fiscal_year=year)
                session.add(r)
            r.health_insurance_rate = float(row["健保"] or 0)
            r.nursing_care_rate = float(row["介護"] or 0)
            r.pension_rate = float(row["年金"] or 0)
            r.child_allowance_rate = float(row["児童拠出"] or 0)
            r.employment_insurance_rate = float(row["雇保"] or 0)
            r.workers_comp_rate = float(row["労災"] or 0)
            r.general_contribution_rate = float(row["一般拠出"] or 0)
        for year, r in existing_by_year.items():
            if year not in seen:
                session.delete(r)
        session.commit()
        st.success("保存しました。")
        st.rerun()

session.close()
