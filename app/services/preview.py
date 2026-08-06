from __future__ import annotations

import datetime as dt

from sqlalchemy.orm import Session

from app.models import FinancialRecord, InsuranceRateMaster
from app.services.calc import CostLineInput, LineItemInput, calc_cost_line_amount, calc_line_item, fiscal_year_of


def build_quote_preview_rows(session: Session, record: FinancialRecord) -> list[dict]:
    """見積書プレビュー用の行を作る。請求科目・経費の項目名と金額のみ(顧客提出物には
    社保加入区分・契約形式・計算パターンなど社内用の情報を一切含めない)。
    """
    insurance_master = session.query(InsuranceRateMaster).filter(
        InsuranceRateMaster.fiscal_year == fiscal_year_of(record.period_start or dt.date.today())
    ).one_or_none()
    insurance_rate = insurance_master.total_rate if insurance_master else 0.0

    rows: list[dict] = []
    for li in record.line_items:
        result = calc_line_item(
            LineItemInput(
                billing_daily_rate=li.billing_daily_rate,
                billing_days=li.billing_days,
                headcount=li.headcount,
                billing_commute_monthly=li.billing_commute_monthly,
                billing_admin_fee_monthly=li.billing_admin_fee_monthly,
                billing_allowance_monthly=li.billing_allowance_monthly,
            ),
            insurance_rate,
        )
        if li.billing_item_display and li.billing_item_display != "(未設定)":
            rows.append({"項目": li.billing_item_display, "数量": f"{li.headcount}名 × {li.billing_days}日", "金額": result.sales})

    for cl in record.cost_lines:
        pattern = cl.billing_pricing_pattern
        amount = calc_cost_line_amount(
            CostLineInput(
                rate=cl.billing_rate,
                qty1=cl.billing_qty1 if pattern and pattern.qty1_label else None,
                qty2=cl.billing_qty2 if pattern and pattern.qty2_label else None,
                qty3=cl.billing_qty3 if pattern and pattern.qty3_label else None,
            )
        )
        if cl.category:
            rows.append({"項目": cl.category, "数量": "—", "金額": amount})

    return rows
