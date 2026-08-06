from __future__ import annotations

import datetime as dt
from collections import defaultdict

import pandas as pd
from sqlalchemy.orm import Session

from app.models import CostLine, FinancialRecord, InsuranceRateMaster, LineItem, WeeklyActual
from app.services.calc import LineItemInput, calc_line_item, fiscal_year_of

BOARD_COLUMNS = [
    "会社", "区分", "常勤・CA", "年月", "統括名称", "部門名称", "取引先名称", "地域区分",
    "セグメント", "商材", "売上高", "売上原価", "粗利", "常勤数", "販売管理費", "ポジ数",
    "受注状況", "ユニット名称", "QT",
]

COMPANY_NAME = "Backs"


def _month_range(start: dt.date, end: dt.date) -> list[dt.date]:
    months = []
    cur = start.replace(day=1)
    last = end.replace(day=1)
    while cur <= last:
        months.append(cur)
        if cur.month == 12:
            cur = cur.replace(year=cur.year + 1, month=1)
        else:
            cur = cur.replace(month=cur.month + 1)
    return months


def _qt_of(month_date: dt.date, fiscal_start_month: int = 4) -> str:
    offset = (month_date.month - fiscal_start_month) % 12
    return f"{offset // 3 + 1}QT"


def _department_name(record: FinancialRecord) -> str:
    """部門名称は作成者の所属拠点(=経営ボード明細上の部門名称)を優先し、
    未設定の場合のみ案件の部署名にフォールバックする。"""
    if record.created_by is not None and record.created_by.branch is not None:
        return record.created_by.branch.name
    return record.project.dept


def _record_sales_cost(session: Session, record: FinancialRecord, insurance_rate: float) -> tuple[float, float, int]:
    line_items = session.query(LineItem).filter(LineItem.financial_record_id == record.id).all()
    total_sales = 0.0
    total_cost = 0.0
    headcount = 0
    for li in line_items:
        result = calc_line_item(
            LineItemInput(
                billing_daily_rate=li.billing_daily_rate,
                billing_days=li.billing_days,
                headcount=li.headcount,
                payment_hourly_rate=li.payment_hourly_rate,
                hours_per_day=li.standard_hours_daily,
                payment_days=li.payment_days,
                overtime_hours_monthly=li.overtime_hours_monthly,
                night_overtime_hours_monthly=li.night_overtime_hours_monthly,
                unbilled_leave_hours_monthly=li.unbilled_leave_hours_monthly,
            ),
            insurance_rate,
        )
        total_sales += result.sales
        total_cost += result.cost_total
        headcount += li.headcount
    return total_sales, total_cost, headcount


def build_confirmed_estimate_rows(session: Session, record: FinancialRecord) -> list[dict]:
    """確定見積(区分=予算)を、period_start〜period_endの各月に展開する。

    イニシャル費目はperiod_startの月のみ、ランニング費目は展開後の全月に計上する
    (30_architecture.md ADR-4の方針に基づく簡易実装)。
    """
    if record.period_start is None or record.period_end is None:
        return []

    insurance_master = session.query(InsuranceRateMaster).filter(
        InsuranceRateMaster.fiscal_year == fiscal_year_of(record.period_start)
    ).one_or_none()
    insurance_rate = insurance_master.total_rate if insurance_master else 0.0

    line_sales, line_cost, headcount = _record_sales_cost(session, record, insurance_rate)

    cost_lines = session.query(CostLine).filter(CostLine.financial_record_id == record.id).all()
    initial_billing = sum(
        c.billing_rate * (c.billing_qty1 or 1) * (c.billing_qty2 or 1) * (c.billing_qty3 or 1)
        for c in cost_lines if c.timing == "イニシャル"
    )
    running_billing = sum(
        c.billing_rate * (c.billing_qty1 or 1) * (c.billing_qty2 or 1) * (c.billing_qty3 or 1)
        for c in cost_lines if c.timing != "イニシャル"
    )
    initial_cost = sum(
        c.cost_rate * (c.cost_qty1 or 1) * (c.cost_qty2 or 1) * (c.cost_qty3 or 1)
        for c in cost_lines if c.timing == "イニシャル"
    )
    running_cost = sum(
        c.cost_rate * (c.cost_qty1 or 1) * (c.cost_qty2 or 1) * (c.cost_qty3 or 1)
        for c in cost_lines if c.timing != "イニシャル"
    )

    months = _month_range(record.period_start, record.period_end)
    rows = []
    for i, month in enumerate(months):
        month_sales = line_sales + running_billing + (initial_billing if i == 0 else 0)
        month_cost = line_cost + running_cost + (initial_cost if i == 0 else 0)
        rows.append(
            {
                "会社": COMPANY_NAME,
                "区分": "予算",
                "常勤・CA": record.employment_type,
                "年月": month.strftime("%Y%m"),
                "統括名称": record.headquarters_name,
                "部門名称": _department_name(record),
                "取引先名称": record.project.client_name,
                "地域区分": record.region,
                "セグメント": record.segment,
                "商材": record.product,
                "売上高": month_sales,
                "売上原価": month_cost,
                "粗利": month_sales - month_cost,
                "常勤数": headcount,
                "販売管理費": record.sga_cost,
                "ポジ数": 0,
                "受注状況": record.order_result,
                "ユニット名称": record.unit_name,
                "QT": _qt_of(month),
            }
        )
    return rows


def build_actual_rows(session: Session, record: FinancialRecord) -> list[dict]:
    """週次実績(WeeklyActual)を、週の月曜日が属する月に合算して月次の実績行にする。"""
    weeklies = session.query(WeeklyActual).filter(WeeklyActual.financial_record_id == record.id).all()
    by_month: dict[str, dict] = defaultdict(lambda: {"sales": 0.0, "cost": 0.0, "sga": 0.0, "reg": 0, "pos": 0})
    for w in weeklies:
        key = w.week_start.strftime("%Y%m")
        by_month[key]["sales"] += w.sales
        by_month[key]["cost"] += w.cost
        by_month[key]["sga"] += w.sga_cost
        by_month[key]["reg"] = max(by_month[key]["reg"], w.headcount_regular)
        by_month[key]["pos"] = max(by_month[key]["pos"], w.headcount_position)

    rows = []
    for ym, agg in sorted(by_month.items()):
        month_date = dt.date(int(ym[:4]), int(ym[4:6]), 1)
        rows.append(
            {
                "会社": COMPANY_NAME,
                "区分": "実績",
                "常勤・CA": record.employment_type,
                "年月": ym,
                "統括名称": record.headquarters_name,
                "部門名称": _department_name(record),
                "取引先名称": record.project.client_name,
                "地域区分": record.region,
                "セグメント": record.segment,
                "商材": record.product,
                "売上高": agg["sales"],
                "売上原価": agg["cost"],
                "粗利": agg["sales"] - agg["cost"],
                "常勤数": agg["reg"],
                "販売管理費": agg["sga"],
                "ポジ数": agg["pos"],
                "受注状況": record.order_result,
                "ユニット名称": record.unit_name,
                "QT": _qt_of(month_date),
            }
        )
    return rows


def build_board_dataframe(session: Session, records: list[FinancialRecord]) -> pd.DataFrame:
    """経営ボード明細の対象は「確定見積」かつ「受注」が確定したレコードのみ
    (収支管理は受注した案件のみを扱う方針のため、失注・未定は対象外)。
    """
    rows: list[dict] = []
    for record in records:
        if record.record_type != "確定見積" or record.order_result != "受注":
            continue
        rows.extend(build_confirmed_estimate_rows(session, record))
        rows.extend(build_actual_rows(session, record))
    return pd.DataFrame(rows, columns=BOARD_COLUMNS)
