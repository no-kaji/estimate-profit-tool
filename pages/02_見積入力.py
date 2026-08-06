import datetime as dt

import pandas as pd
import streamlit as st
from sqlalchemy import select

from app.auth import logout_button, require_login
from app.db import get_session, init_db
from app.models import (
    ROLE_MANAGER,
    BillingItemMaster,
    ContractType,
    CostLine,
    FinancialRecord,
    InsuranceRateMaster,
    LineItem,
    PricingPattern,
    Project,
    User,
)
from app.seal import seal_img_tag
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

st.set_page_config(page_title="見積入力 | 収支ワークフローツール", page_icon="📊", layout="wide")
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

_preselected_id = st.session_state.get("editing_record_id")
_preselected_valid = _preselected_id is not None and any(r.id == _preselected_id for r in existing_records)
mode = st.radio(
    "操作", ["新規に見積を作成", "既存レコードを編集"], horizontal=True,
    index=1 if _preselected_valid else 0,
)

editing_record: FinancialRecord | None = None
if mode == "既存レコードを編集":
    if not existing_records:
        st.info("この案件にはまだレコードがありません。「新規に見積を作成」を選んでください。")
        st.stop()
    rec_labels = {r.id: f"{r.record_type} / {r.period_start or '期間未定'}〜{r.period_end or ''}" for r in existing_records}
    rec_ids = list(rec_labels.keys())
    rec_id = st.selectbox(
        "編集するレコード", options=rec_ids, format_func=lambda i: rec_labels[i],
        index=rec_ids.index(_preselected_id) if _preselected_valid else 0,
    )
    editing_record = session.get(FinancialRecord, rec_id)
    st.session_state["estimate_step"] = "detail"
    st.session_state["selected_contract_type_id"] = editing_record.contract_type_id
    st.session_state["editing_record_id"] = editing_record.id
else:
    st.session_state.setdefault("estimate_step", "contract_type")
    if st.session_state.get("editing_record_id") is not None and mode == "新規に見積を作成":
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
    ["概算見積", "確定見積"],
    horizontal=True,
    index=["概算見積", "確定見積"].index(editing_record.record_type) if editing_record else 0,
)
st.caption("実績は「収支管理」メニューで、確定見積を選んで週次入力します。")

period_start = period_end = None
if record_type == "確定見積":
    pc1, pc2 = st.columns(2)
    period_start = pc1.date_input("開始月(1日を選択)", value=editing_record.period_start if editing_record else dt.date.today().replace(day=1))
    period_end = pc2.date_input("終了月(1日を選択)", value=editing_record.period_end if editing_record else dt.date.today().replace(day=1))
else:
    st.caption("概算見積のため期間は未定でも登録できます。")

if record_type == "概算見積" and editing_record is not None:
    if st.button("この内容で確定見積を作成 →"):
        st.session_state["_copy_to_confirmed"] = editing_record.id

# ---------------------------------------------------------------
# 承認申請(確定見積の見積書発行フロー)
# マネージャー/システム管理者が自ら作成した場合: その場で自己承認(社判も自分で配置)
# ユーザーが作成した場合: 個人印鑑を押し、所属拠点のマネージャーを選んで承認を申請
# ---------------------------------------------------------------
if record_type == "確定見積" and editing_record is not None:
    status = editing_record.approval_status
    badge_map = {"下書き": "⚪ 下書き", "申請中": "🟡 承認申請中", "承認済み": "🟢 承認済み(社判配置済み)", "却下": "🔴 却下"}
    st.info(f"承認ステータス: {badge_map.get(status, status)}")

    if status in ("下書き", "却下") and not user.seal_svg:
        st.warning("承認フローに進める前に、マイページで個人印鑑を生成してください。")
    elif status in ("下書き", "却下") and user.can_self_approve:

        @st.dialog("承認フロー")
        def _self_approve_dialog(record_id: int):
            st.write("あなた自身の承認として、この内容を承認済みにします(社判もあわせて配置されます)。")
            st.markdown(seal_img_tag(user.seal_svg, size=70), unsafe_allow_html=True)
            dc1, dc2 = st.columns(2)
            if dc1.button("承認する", type="primary", use_container_width=True):
                rec = session.get(FinancialRecord, record_id)
                now = dt.datetime.utcnow()
                rec.approval_status = "承認済み"
                rec.requested_by_id = user.id
                rec.requested_at = now
                rec.approved_by_id = user.id
                rec.approved_at = now
                rec.reject_reason = None
                session.commit()
                st.session_state["_approval_submitted"] = "self"
                st.rerun()
            if dc2.button("キャンセル", use_container_width=True):
                st.rerun()

        if st.button("完了(自己承認・社判配置)", type="primary"):
            _self_approve_dialog(editing_record.id)
    elif status in ("下書き", "却下"):
        candidate_managers = session.execute(
            select(User).where(User.role == ROLE_MANAGER, User.branch_id == user.branch_id, User.active.is_(True))
        ).scalars().all()
        if not candidate_managers:
            st.warning("あなたの所属拠点に承認可能なマネージャーが登録されていません。システム管理者にお問い合わせください。")
        else:
            mgr_options = {m.id: m.display_name or m.username for m in candidate_managers}
            approver_id = st.selectbox("承認を依頼するマネージャー", options=list(mgr_options.keys()), format_func=lambda i: mgr_options[i])

            @st.dialog("承認フロー申請")
            def _confirm_submit_dialog(record_id: int, approver_id: int):
                st.write(f"「{mgr_options[approver_id]}」さんに承認を申請しますか?")
                st.markdown(seal_img_tag(user.seal_svg, size=70), unsafe_allow_html=True)
                st.caption("↑あなたの個人印鑑がこの見積書に配置されます。")
                dc1, dc2 = st.columns(2)
                if dc1.button("申請する", type="primary", use_container_width=True):
                    rec = session.get(FinancialRecord, record_id)
                    rec.approval_status = "申請中"
                    rec.requested_by_id = user.id
                    rec.requested_at = dt.datetime.utcnow()
                    rec.assigned_approver_id = approver_id
                    rec.reject_reason = None
                    session.commit()
                    st.session_state["_approval_submitted"] = "requested"
                    st.rerun()
                if dc2.button("キャンセル", use_container_width=True):
                    st.rerun()

            if st.button("完了(承認フローに申請)", type="primary"):
                _confirm_submit_dialog(editing_record.id, approver_id)
    elif status == "申請中":
        st.caption(
            f"申請日時: {editing_record.requested_at} / "
            f"承認依頼先: {editing_record.assigned_approver.display_name if editing_record.assigned_approver else ''} "
            "からの回答をお待ちください。"
        )
    elif status == "承認済み":
        st.caption(f"承認日時: {editing_record.approved_at} / 承認者: {editing_record.approved_by.display_name if editing_record.approved_by else ''}")

    _submitted = st.session_state.pop("_approval_submitted", None)
    if _submitted == "self":
        st.success("承認済みにしました。社判が配置されます。")
    elif _submitted == "requested":
        st.success("承認フローに申請しました。マネージャーの承認をお待ちください。")

# ---------------------------------------------------------------
# 明細行(人件費)
# ---------------------------------------------------------------
st.subheader("明細行(人件費)")
st.caption(
    "個人名ではなく「請求科目」を単位として入力します。列名の【請求】はお客様への請求額、"
    "【原価】は実際にかかる費用です。社保加入区分は社内用で、見積書には表示されません。"
)

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

LINE_ITEM_COLUMNS = [
    "請求科目", "社保加入区分(社内用)", "人数",
    "【請求】日額単価", "【請求】日数",
    "【原価】計算パターン", "【原価】単価", "【原価】数量1", "【原価】数量2", "【原価】数量3",
]

if "line_items_df" not in st.session_state or st.session_state.get("_line_items_loaded_for") != (project.id, editing_record.id if editing_record else None):
    if editing_record:
        rows = [
            {
                "請求科目": li.billing_item_display,
                "社保加入区分(社内用)": li.insurance_status,
                "人数": li.headcount,
                "【請求】日額単価": li.billing_daily_rate,
                "【請求】日数": li.billing_days,
                "【原価】計算パターン": (li.payment_pricing_pattern.name if li.payment_pricing_pattern else patterns_for_contract[0]),
                "【原価】単価": li.payment_rate,
                "【原価】数量1": li.payment_qty1,
                "【原価】数量2": li.payment_qty2,
                "【原価】数量3": li.payment_qty3,
            }
            for li in editing_record.line_items
        ]
    else:
        rows = []
    st.session_state["line_items_df"] = pd.DataFrame(rows, columns=LINE_ITEM_COLUMNS)
    st.session_state["_line_items_loaded_for"] = (project.id, editing_record.id if editing_record else None)

line_items_df = st.data_editor(
    st.session_state["line_items_df"],
    num_rows="dynamic",
    use_container_width=True,
    column_config={
        "請求科目": st.column_config.SelectboxColumn(options=billing_item_names, required=False),
        "社保加入区分(社内用)": st.column_config.SelectboxColumn(options=["済", "未", "外注"]),
        "人数": st.column_config.NumberColumn(min_value=0, step=1),
        "【請求】日額単価": st.column_config.NumberColumn(format="¥%d", min_value=0, step=100),
        "【請求】日数": st.column_config.NumberColumn(min_value=0, step=1),
        "【原価】計算パターン": st.column_config.SelectboxColumn(options=patterns_for_contract),
        "【原価】単価": st.column_config.NumberColumn(format="¥%d", min_value=0, step=100),
        "【原価】数量1": st.column_config.NumberColumn(min_value=0, step=1),
        "【原価】数量2": st.column_config.NumberColumn(min_value=0, step=1),
        "【原価】数量3": st.column_config.NumberColumn(min_value=0, step=1),
    },
    key="line_items_editor",
)
# ここで st.session_state["line_items_df"] に編集結果を書き戻さないこと(Streamlitの既知の挙動で
# 1回目の編集が反映されず2回目でようやく反映される不具合につながる)。以降はローカル変数を使う。

# ---------------------------------------------------------------
# 経費行(請求側・原価側を別々に入力する)
# ---------------------------------------------------------------
st.subheader("経費")
st.caption("契約形式に縛られず、計算パターンを直接選択できます。【請求】お客様への請求額、【原価】実際にかかる費用、を別々に入力します。")

COST_LINE_COLUMNS = [
    "費目",
    "【請求】計算パターン", "【請求】単価", "【請求】数量1", "【請求】数量2", "【請求】数量3",
    "【原価】計算パターン", "【原価】単価", "【原価】数量1", "【原価】数量2", "【原価】数量3",
    "区分",
]

if "cost_lines_df" not in st.session_state or st.session_state.get("_cost_lines_loaded_for") != (project.id, editing_record.id if editing_record else None):
    if editing_record:
        rows = [
            {
                "費目": cl.category,
                "【請求】計算パターン": (cl.billing_pricing_pattern.name if cl.billing_pricing_pattern else all_patterns[0]),
                "【請求】単価": cl.billing_rate,
                "【請求】数量1": cl.billing_qty1,
                "【請求】数量2": cl.billing_qty2,
                "【請求】数量3": cl.billing_qty3,
                "【原価】計算パターン": (cl.cost_pricing_pattern.name if cl.cost_pricing_pattern else all_patterns[0]),
                "【原価】単価": cl.cost_rate,
                "【原価】数量1": cl.cost_qty1,
                "【原価】数量2": cl.cost_qty2,
                "【原価】数量3": cl.cost_qty3,
                "区分": cl.timing,
            }
            for cl in editing_record.cost_lines
        ]
    else:
        rows = []
    st.session_state["cost_lines_df"] = pd.DataFrame(rows, columns=COST_LINE_COLUMNS)
    st.session_state["_cost_lines_loaded_for"] = (project.id, editing_record.id if editing_record else None)

cost_lines_df = st.data_editor(
    st.session_state["cost_lines_df"],
    num_rows="dynamic",
    use_container_width=True,
    column_config={
        "【請求】計算パターン": st.column_config.SelectboxColumn(options=all_patterns),
        "【請求】単価": st.column_config.NumberColumn(format="¥%d", min_value=0, step=100),
        "【請求】数量1": st.column_config.NumberColumn(min_value=0, step=1),
        "【請求】数量2": st.column_config.NumberColumn(min_value=0, step=1),
        "【請求】数量3": st.column_config.NumberColumn(min_value=0, step=1),
        "【原価】計算パターン": st.column_config.SelectboxColumn(options=all_patterns),
        "【原価】単価": st.column_config.NumberColumn(format="¥%d", min_value=0, step=100),
        "【原価】数量1": st.column_config.NumberColumn(min_value=0, step=1),
        "【原価】数量2": st.column_config.NumberColumn(min_value=0, step=1),
        "【原価】数量3": st.column_config.NumberColumn(min_value=0, step=1),
        "区分": st.column_config.SelectboxColumn(options=["イニシャル", "ランニング"]),
    },
    key="cost_lines_editor",
)
# line_items_dfと同じ理由で、st.session_state["cost_lines_df"]への書き戻しはしない。
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
    pattern = pattern_by_name.get(row.get("【原価】計算パターン"))
    is_hourly = pattern is not None and pattern.name == "時間×日数×月数"
    item_input = LineItemInput(
        billing_daily_rate=float(row.get("【請求】日額単価") or 0),
        billing_days=float(row.get("【請求】日数") or 0),
        headcount=int(row.get("人数") or 1),
        payment_rate=float(row.get("【原価】単価") or 0),
        payment_qty1=float(row.get("【原価】数量1") or 1) if pattern and pattern.qty1_label else None,
        payment_qty2=float(row.get("【原価】数量2") or 1) if pattern and pattern.qty2_label else None,
        payment_qty3=float(row.get("【原価】数量3") or 1) if pattern and pattern.qty3_label else None,
        is_hourly_pattern=is_hourly,
    )
    line_results.append(calc_line_item(item_input, insurance_rate))

cost_billing_amounts = []
cost_cost_amounts = []
for _, row in cost_lines_df.iterrows():
    billing_pattern = pattern_by_name.get(row.get("【請求】計算パターン"))
    billing_input = CostLineInput(
        rate=float(row.get("【請求】単価") or 0),
        qty1=float(row.get("【請求】数量1") or 1) if billing_pattern and billing_pattern.qty1_label else None,
        qty2=float(row.get("【請求】数量2") or 1) if billing_pattern and billing_pattern.qty2_label else None,
        qty3=float(row.get("【請求】数量3") or 1) if billing_pattern and billing_pattern.qty3_label else None,
    )
    cost_billing_amounts.append(calc_cost_line_amount(billing_input))

    cost_pattern = pattern_by_name.get(row.get("【原価】計算パターン"))
    cost_input = CostLineInput(
        rate=float(row.get("【原価】単価") or 0),
        qty1=float(row.get("【原価】数量1") or 1) if cost_pattern and cost_pattern.qty1_label else None,
        qty2=float(row.get("【原価】数量2") or 1) if cost_pattern and cost_pattern.qty2_label else None,
        qty3=float(row.get("【原価】数量3") or 1) if cost_pattern and cost_pattern.qty3_label else None,
    )
    cost_cost_amounts.append(calc_cost_line_amount(cost_input))

summary: FinancialRecordSummary = calc_financial_record_summary(line_results, cost_billing_amounts, cost_cost_amounts)

st.subheader("収支サマリ")
m1, m2, m3, m4, m5 = st.columns(5)
m1.metric("売上高", f"¥{summary.sales:,.0f}")
m2.metric("売上原価", f"¥{summary.cost:,.0f}")
m3.metric("粗利", f"¥{summary.profit:,.0f}")
m4.metric("粗利率", f"{summary.margin * 100:.1f}%")
m5.metric("営業利益", f"¥{summary.operating_profit:,.0f}")

st.caption(
    f"統括名称: {user.headquarters.name if user.headquarters else '未設定'} / "
    f"部門名称: {user.branch.name if user.branch else '未設定'} / "
    f"地域区分: {user.region.name if user.region else '未設定'}"
    "(あなたのプロフィールから自動的にタグ付けされます。マイページでは変更できません。"
    "システム管理者にご相談ください)"
)

with st.expander("経営ボード明細用の追加項目(セグメント・商材・常勤/CA 等)"):
    d1, d2, d3 = st.columns(3)
    segment = d1.text_input("セグメント", value=editing_record.segment if editing_record else "")
    product = d2.text_input("商材", value=editing_record.product if editing_record else "")
    employment_type = d3.selectbox(
        "常勤・CA", options=["常勤", "CA"],
        index=(["常勤", "CA"].index(editing_record.employment_type) if editing_record and editing_record.employment_type in ("常勤", "CA") else 0),
    )
    d4, d5 = st.columns(2)
    order_status = d4.text_input("受注状況", value=editing_record.order_status if editing_record else "")
    unit_name = d5.text_input("ユニット名称", value=editing_record.unit_name if editing_record else "")

# ---------------------------------------------------------------
# 保存
# ---------------------------------------------------------------
if st.button("保存", type="primary"):
    if editing_record is not None:
        rec = editing_record
    else:
        rec = FinancialRecord(project_id=project.id, created_by_id=user.id)
        session.add(rec)

    rec.record_type = record_type
    rec.contract_type_id = contract_type.id
    rec.period_start = period_start
    rec.period_end = period_end
    rec.headquarters_name = user.headquarters.name if user.headquarters else ""
    rec.region = user.region.name if user.region else ""
    rec.segment = segment
    rec.product = product
    rec.employment_type = employment_type
    rec.order_status = order_status
    rec.unit_name = unit_name
    session.flush()

    session.query(LineItem).filter(LineItem.financial_record_id == rec.id).delete()
    session.query(CostLine).filter(CostLine.financial_record_id == rec.id).delete()

    billing_item_by_name = {b.item_name: b for b in billing_items}
    for _, row in line_items_df.iterrows():
        if not row.get("請求科目"):
            continue
        pattern = pattern_by_name.get(row.get("【原価】計算パターン"))
        billing_item = billing_item_by_name.get(row.get("請求科目"))
        session.add(
            LineItem(
                financial_record_id=rec.id,
                billing_item_id=billing_item.id if billing_item else None,
                billing_item_name_free=None if billing_item else row.get("請求科目"),
                insurance_status=row.get("社保加入区分(社内用)") or "済",
                headcount=int(row.get("人数") or 1),
                billing_daily_rate=float(row.get("【請求】日額単価") or 0),
                billing_days=float(row.get("【請求】日数") or 0),
                payment_pricing_pattern_id=pattern.id if pattern else None,
                payment_rate=float(row.get("【原価】単価") or 0),
                payment_qty1=float(row.get("【原価】数量1") or 1),
                payment_qty2=float(row.get("【原価】数量2") or 1),
                payment_qty3=float(row.get("【原価】数量3") or 1),
            )
        )
    for _, row in cost_lines_df.iterrows():
        if not row.get("費目"):
            continue
        billing_pattern = pattern_by_name.get(row.get("【請求】計算パターン"))
        cost_pattern = pattern_by_name.get(row.get("【原価】計算パターン"))
        session.add(
            CostLine(
                financial_record_id=rec.id,
                category=row.get("費目"),
                billing_pricing_pattern_id=billing_pattern.id if billing_pattern else None,
                billing_rate=float(row.get("【請求】単価") or 0),
                billing_qty1=float(row.get("【請求】数量1") or 1),
                billing_qty2=float(row.get("【請求】数量2") or 1),
                billing_qty3=float(row.get("【請求】数量3") or 1),
                cost_pricing_pattern_id=cost_pattern.id if cost_pattern else None,
                cost_rate=float(row.get("【原価】単価") or 0),
                cost_qty1=float(row.get("【原価】数量1") or 1),
                cost_qty2=float(row.get("【原価】数量2") or 1),
                cost_qty3=float(row.get("【原価】数量3") or 1),
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
            employment_type=src.employment_type,
            order_status=src.order_status,
            unit_name=src.unit_name,
            created_by_id=user.id,
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
        st.success("概算見積の内容をコピーして、新しい確定見積レコードを作成しました。元の概算見積はそのまま保持されています。")
        st.session_state["editing_record_id"] = new_rec.id
        st.rerun()

session.close()
