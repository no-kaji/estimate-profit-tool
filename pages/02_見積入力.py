import datetime as dt

import pandas as pd
import streamlit as st
from sqlalchemy import select

from app.auth import logout_button, require_login
from app.db import get_session, init_db
from app.models import (
    BillingItemMaster,
    CancellationPolicyMaster,
    ContractType,
    CostLine,
    FinancialRecord,
    InsuranceRateMaster,
    LineItem,
    PricingPattern,
    Project,
)
from app.services.calc import (
    CostLineInput,
    FinancialRecordSummary,
    LineItemInput,
    calc_cost_line_amount,
    calc_financial_record_summary,
    calc_line_item,
    fiscal_year_of,
)
from app.ui import apply_theme

st.set_page_config(page_title="見積入力 | 見積収支計算書ツール", page_icon="📊", layout="wide")
init_db()
session = get_session()
user = require_login(session)
apply_theme()
logout_button()

st.title("見積入力")

# ---------------------------------------------------------------
# 案件の選択(01_案件一覧を経由しない直接アクセスにも対応)
# ---------------------------------------------------------------
projects = session.execute(select(Project).where(Project.deleted_at.is_(None))).scalars().all()
if not projects:
    st.warning("案件が登録されていません。先に「01_案件一覧」から新規案件を登録してください。")
    st.stop()

project_id = st.session_state.get("current_project_id")
project_labels = {p.id: f"{p.project_name or '(未設定)'}({p.dept} / {p.client_name})" for p in projects}
selected_id = st.selectbox(
    "案件",
    options=list(project_labels.keys()),
    format_func=lambda i: project_labels[i],
    index=list(project_labels.keys()).index(project_id) if project_id in project_labels else 0,
)
st.session_state["current_project_id"] = selected_id
project = session.get(Project, selected_id)

# ---------------------------------------------------------------
# 新規作成 or 既存レコードの編集
# ---------------------------------------------------------------
existing_records = session.execute(
    select(FinancialRecord).where(FinancialRecord.project_id == project.id)
).scalars().all()

mode = st.radio("操作", ["新規に見積/実績を作成", "既存レコードを編集"], horizontal=True)

editing_record: FinancialRecord | None = None
if mode == "既存レコードを編集":
    if not existing_records:
        st.info("この案件にはまだレコードがありません。「新規に見積/実績を作成」を選んでください。")
        st.stop()
    rec_labels = {r.id: f"{r.record_type} / {r.period_start or '期間未定'}〜{r.period_end or ''}" for r in existing_records}
    rec_id = st.selectbox("編集するレコード", options=list(rec_labels.keys()), format_func=lambda i: rec_labels[i])
    editing_record = session.get(FinancialRecord, rec_id)
    st.session_state["estimate_step"] = "detail"
    st.session_state["selected_contract_type_id"] = editing_record.contract_type_id
    st.session_state["editing_record_id"] = editing_record.id
else:
    st.session_state.setdefault("estimate_step", "contract_type")
    if st.session_state.get("editing_record_id") is not None and mode == "新規に見積/実績を作成":
        st.session_state["editing_record_id"] = None
        st.session_state["estimate_step"] = "contract_type"

st.divider()

# ---------------------------------------------------------------
# Step 1: 契約形式の選択
# ---------------------------------------------------------------
contract_types = session.execute(select(ContractType)).scalars().all()

if st.session_state.get("estimate_step", "contract_type") == "contract_type":
    st.subheader("Step 1. 契約形式を選択")
    st.caption("見積1件につき契約形式は1つです(経費行は契約形式を問わず入力できます)")
    cols = st.columns(len(contract_types))
    for col, ct in zip(cols, contract_types):
        with col:
            st.markdown(f"**{ct.name}**")
            st.caption(ct.description)
            if st.button("これを選択", key=f"pick_{ct.id}"):
                st.session_state["selected_contract_type_id"] = ct.id
                st.session_state["estimate_step"] = "detail"
                st.rerun()
    st.stop()

# ---------------------------------------------------------------
# Step 2: 明細入力
# ---------------------------------------------------------------
contract_type_id = st.session_state.get("selected_contract_type_id")
contract_type = session.get(ContractType, contract_type_id) if contract_type_id else None
if contract_type is None:
    st.session_state["estimate_step"] = "contract_type"
    st.rerun()

c1, c2 = st.columns([4, 1])
c1.info(f"契約形式: **{contract_type.name}**")
if c2.button("契約形式を変更"):
    st.session_state["estimate_step"] = "contract_type"
    st.rerun()

record_type = st.radio(
    "レコード種別",
    ["概算見積", "確定見積", "実績"],
    horizontal=True,
    index=["概算見積", "確定見積", "実績"].index(editing_record.record_type) if editing_record else 0,
)

period_start = period_end = None
if record_type == "確定見積":
    pc1, pc2 = st.columns(2)
    period_start = pc1.date_input("開始月(1日を選択)", value=editing_record.period_start if editing_record else dt.date.today().replace(day=1))
    period_end = pc2.date_input("終了月(1日を選択)", value=editing_record.period_end if editing_record else dt.date.today().replace(day=1))
elif record_type == "実績":
    target_month = st.date_input("対象年月(1日を選択)", value=editing_record.period_start if editing_record else dt.date.today().replace(day=1))
    period_start = period_end = target_month
else:
    st.caption("概算見積のため期間は未定でも登録できます。")

if record_type == "概算見積" and editing_record is not None:
    if st.button("この内容で確定見積を作成 →"):
        st.session_state["_copy_to_confirmed"] = editing_record.id

# ---------------------------------------------------------------
# 明細行(人件費)
# ---------------------------------------------------------------
st.subheader("明細行(人件費)")
st.caption("個人名ではなく「請求科目」を単位として入力します。社保加入区分は社内用で、見積書には表示されません。")

billing_items = session.execute(select(BillingItemMaster)).scalars().all()
billing_item_names = [b.item_name for b in billing_items]

with st.expander("＋ 請求科目マスタに新しい項目を追加"):
    new_item_name = st.text_input("請求科目名", key="new_billing_item_name")
    if st.button("マスタに追加", key="add_billing_item"):
        if new_item_name and new_item_name not in billing_item_names:
            session.add(BillingItemMaster(item_name=new_item_name, category="職種"))
            session.commit()
            st.rerun()

patterns_for_contract = [p.name for p in contract_type.patterns]
all_patterns = [p.name for p in session.execute(select(PricingPattern)).scalars().all()]

if "line_items_df" not in st.session_state or st.session_state.get("_line_items_loaded_for") != (project.id, editing_record.id if editing_record else None):
    if editing_record:
        rows = [
            {
                "請求科目": li.billing_item_display,
                "社保加入区分(社内用)": li.insurance_status,
                "人数": li.headcount,
                "請求日額単価": li.billing_daily_rate,
                "請求日数": li.billing_days,
                "支払計算パターン": (li.payment_pricing_pattern.name if li.payment_pricing_pattern else patterns_for_contract[0]),
                "支払単価": li.payment_rate,
                "数量1": li.payment_qty1,
                "数量2": li.payment_qty2,
                "数量3": li.payment_qty3,
            }
            for li in editing_record.line_items
        ]
    else:
        rows = []
    st.session_state["line_items_df"] = pd.DataFrame(
        rows,
        columns=["請求科目", "社保加入区分(社内用)", "人数", "請求日額単価", "請求日数", "支払計算パターン", "支払単価", "数量1", "数量2", "数量3"],
    )
    st.session_state["_line_items_loaded_for"] = (project.id, editing_record.id if editing_record else None)

line_items_df = st.data_editor(
    st.session_state["line_items_df"],
    num_rows="dynamic",
    use_container_width=True,
    column_config={
        "請求科目": st.column_config.SelectboxColumn(options=billing_item_names, required=False),
        "社保加入区分(社内用)": st.column_config.SelectboxColumn(options=["済", "未", "外注"]),
        "支払計算パターン": st.column_config.SelectboxColumn(options=patterns_for_contract),
        "人数": st.column_config.NumberColumn(min_value=0, step=1),
    },
    key="line_items_editor",
)
st.session_state["line_items_df"] = line_items_df

# ---------------------------------------------------------------
# 経費行
# ---------------------------------------------------------------
st.subheader("経費")
st.caption("契約形式に縛られず、計算パターンを直接選択できます。")

if "cost_lines_df" not in st.session_state or st.session_state.get("_cost_lines_loaded_for") != (project.id, editing_record.id if editing_record else None):
    if editing_record:
        rows = [
            {
                "費目": cl.category,
                "計算パターン": (cl.pricing_pattern.name if cl.pricing_pattern else all_patterns[0]),
                "単価": cl.rate,
                "数量1": cl.qty1,
                "数量2": cl.qty2,
                "数量3": cl.qty3,
                "区分": cl.timing,
            }
            for cl in editing_record.cost_lines
        ]
    else:
        rows = []
    st.session_state["cost_lines_df"] = pd.DataFrame(rows, columns=["費目", "計算パターン", "単価", "数量1", "数量2", "数量3", "区分"])
    st.session_state["_cost_lines_loaded_for"] = (project.id, editing_record.id if editing_record else None)

cost_lines_df = st.data_editor(
    st.session_state["cost_lines_df"],
    num_rows="dynamic",
    use_container_width=True,
    column_config={
        "計算パターン": st.column_config.SelectboxColumn(options=all_patterns),
        "区分": st.column_config.SelectboxColumn(options=["イニシャル", "ランニング"]),
    },
    key="cost_lines_editor",
)
st.session_state["cost_lines_df"] = cost_lines_df
if record_type != "確定見積":
    st.caption("確定見積以外では「区分(イニシャル/ランニング)」は無視され、集計にのみ利用します。")

# ---------------------------------------------------------------
# 収支サマリ
# ---------------------------------------------------------------
insurance_master = session.execute(
    select(InsuranceRateMaster).where(InsuranceRateMaster.fiscal_year == fiscal_year_of(period_start or dt.date.today()))
).scalar_one_or_none()
insurance_rate = insurance_master.total_rate if insurance_master else 0.0
if insurance_master is None:
    st.warning("該当年度の法定福利費率マスタが未登録のため、社保料は0として計算しています。マスタ管理から登録してください。")

pattern_by_name = {p.name: p for p in session.execute(select(PricingPattern)).scalars().all()}

line_results = []
for _, row in line_items_df.iterrows():
    pattern = pattern_by_name.get(row.get("支払計算パターン"))
    is_hourly = pattern is not None and pattern.name == "時間×日数×月数"
    item_input = LineItemInput(
        billing_daily_rate=float(row.get("請求日額単価") or 0),
        billing_days=float(row.get("請求日数") or 0),
        headcount=int(row.get("人数") or 1),
        payment_rate=float(row.get("支払単価") or 0),
        payment_qty1=float(row.get("数量1") or 1) if pattern and pattern.qty1_label else None,
        payment_qty2=float(row.get("数量2") or 1) if pattern and pattern.qty2_label else None,
        payment_qty3=float(row.get("数量3") or 1) if pattern and pattern.qty3_label else None,
        is_hourly_pattern=is_hourly,
    )
    line_results.append(calc_line_item(item_input, insurance_rate))

cost_amounts = []
for _, row in cost_lines_df.iterrows():
    pattern = pattern_by_name.get(row.get("計算パターン"))
    cost_input = CostLineInput(
        rate=float(row.get("単価") or 0),
        qty1=float(row.get("数量1") or 1) if pattern and pattern.qty1_label else None,
        qty2=float(row.get("数量2") or 1) if pattern and pattern.qty2_label else None,
        qty3=float(row.get("数量3") or 1) if pattern and pattern.qty3_label else None,
    )
    cost_amounts.append(calc_cost_line_amount(cost_input))

summary: FinancialRecordSummary = calc_financial_record_summary(line_results, cost_amounts)

st.subheader("収支サマリ")
m1, m2, m3, m4, m5 = st.columns(5)
m1.metric("売上高", f"¥{summary.sales:,.0f}")
m2.metric("売上原価", f"¥{summary.cost:,.0f}")
m3.metric("粗利", f"¥{summary.profit:,.0f}")
m4.metric("粗利率", f"{summary.margin * 100:.1f}%")
m5.metric("営業利益", f"¥{summary.operating_profit:,.0f}")

with st.expander("経営ボード明細用の追加項目(統括名称・地域区分・セグメント 等)"):
    d1, d2, d3 = st.columns(3)
    headquarters_name = d1.text_input("統括名称", value=editing_record.headquarters_name if editing_record else "")
    region = d2.text_input("地域区分", value=editing_record.region if editing_record else "")
    segment = d3.text_input("セグメント", value=editing_record.segment if editing_record else "")
    d4, d5, d6 = st.columns(3)
    product = d4.text_input("商材", value=editing_record.product if editing_record else "")
    order_status = d5.text_input("受注状況", value=editing_record.order_status if editing_record else "")
    unit_name = d6.text_input("ユニット名称", value=editing_record.unit_name if editing_record else "")

# ---------------------------------------------------------------
# 保存
# ---------------------------------------------------------------
if st.button("保存", type="primary"):
    if editing_record is not None:
        rec = editing_record
    else:
        rec = FinancialRecord(project_id=project.id)
        session.add(rec)

    rec.record_type = record_type
    rec.contract_type_id = contract_type.id
    rec.period_start = period_start
    rec.period_end = period_end
    rec.headquarters_name = headquarters_name
    rec.region = region
    rec.segment = segment
    rec.product = product
    rec.order_status = order_status
    rec.unit_name = unit_name
    session.flush()

    session.query(LineItem).filter(LineItem.financial_record_id == rec.id).delete()
    session.query(CostLine).filter(CostLine.financial_record_id == rec.id).delete()

    billing_item_by_name = {b.item_name: b for b in billing_items}
    for _, row in line_items_df.iterrows():
        if not row.get("請求科目"):
            continue
        pattern = pattern_by_name.get(row.get("支払計算パターン"))
        billing_item = billing_item_by_name.get(row.get("請求科目"))
        session.add(
            LineItem(
                financial_record_id=rec.id,
                billing_item_id=billing_item.id if billing_item else None,
                billing_item_name_free=None if billing_item else row.get("請求科目"),
                insurance_status=row.get("社保加入区分(社内用)") or "済",
                headcount=int(row.get("人数") or 1),
                billing_daily_rate=float(row.get("請求日額単価") or 0),
                billing_days=float(row.get("請求日数") or 0),
                payment_pricing_pattern_id=pattern.id if pattern else None,
                payment_rate=float(row.get("支払単価") or 0),
                payment_qty1=float(row.get("数量1") or 1),
                payment_qty2=float(row.get("数量2") or 1),
                payment_qty3=float(row.get("数量3") or 1),
            )
        )
    for _, row in cost_lines_df.iterrows():
        if not row.get("費目"):
            continue
        pattern = pattern_by_name.get(row.get("計算パターン"))
        session.add(
            CostLine(
                financial_record_id=rec.id,
                category=row.get("費目"),
                pricing_pattern_id=pattern.id if pattern else None,
                rate=float(row.get("単価") or 0),
                qty1=float(row.get("数量1") or 1),
                qty2=float(row.get("数量2") or 1),
                qty3=float(row.get("数量3") or 1),
                timing=row.get("区分") or "ランニング",
            )
        )
    session.commit()
    st.success("保存しました。")
    st.session_state["editing_record_id"] = rec.id

# 概算見積 -> 確定見積のコピー実行(ボタン押下はレコード再読込前に検知しておく)
if st.session_state.get("_copy_to_confirmed"):
    src_id = st.session_state.pop("_copy_to_confirmed")
    src = session.get(FinancialRecord, src_id)
    if src is not None:
        new_rec = FinancialRecord(
            project_id=src.project_id,
            record_type="確定見積",
            contract_type_id=src.contract_type_id,
            copied_from_id=src.id,
            headquarters_name=src.headquarters_name,
            region=src.region,
            segment=src.segment,
            product=src.product,
            order_status=src.order_status,
            unit_name=src.unit_name,
        )
        session.add(new_rec)
        session.flush()
        for li in src.line_items:
            session.add(
                LineItem(
                    financial_record_id=new_rec.id,
                    billing_item_id=li.billing_item_id,
                    billing_item_name_free=li.billing_item_name_free,
                    insurance_status=li.insurance_status,
                    headcount=li.headcount,
                    billing_daily_rate=li.billing_daily_rate,
                    billing_days=li.billing_days,
                    payment_pricing_pattern_id=li.payment_pricing_pattern_id,
                    payment_rate=li.payment_rate,
                    payment_qty1=li.payment_qty1,
                    payment_qty2=li.payment_qty2,
                    payment_qty3=li.payment_qty3,
                )
            )
        for cl in src.cost_lines:
            session.add(
                CostLine(
                    financial_record_id=new_rec.id,
                    category=cl.category,
                    pricing_pattern_id=cl.pricing_pattern_id,
                    rate=cl.rate,
                    qty1=cl.qty1,
                    qty2=cl.qty2,
                    qty3=cl.qty3,
                    timing=cl.timing,
                )
            )
        session.commit()
        st.success("概算見積の内容をコピーして、新しい確定見積レコードを作成しました。元の概算見積はそのまま保持されています。")
        st.session_state["editing_record_id"] = new_rec.id
        st.rerun()

session.close()
