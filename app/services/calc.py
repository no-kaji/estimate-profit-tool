from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, field


def fiscal_year_of(d: dt.date) -> int:
    """4月始まりの日本の会計年度(西暦)を返す。例: 2026-03 -> 2025年度。"""
    return d.year if d.month >= 4 else d.year - 1


def pattern_amount(rate: float, qty1: float | None, qty2: float | None, qty3: float | None) -> float:
    """単価 x 数量1 x 数量2 x 数量3。未使用のスロットは1として扱う。"""
    total = rate
    for qty in (qty1, qty2, qty3):
        if qty is not None:
            total *= qty
    return total


@dataclass
class LineItemInput:
    billing_daily_rate: float = 0.0
    billing_days: float = 0.0
    billing_commute_monthly: float = 0.0
    billing_admin_fee_monthly: float = 0.0
    billing_allowance_monthly: float = 0.0
    headcount: int = 1

    payment_rate: float = 0.0
    payment_qty1: float | None = 1.0
    payment_qty2: float | None = 1.0
    payment_qty3: float | None = 1.0
    payment_commute_monthly: float = 0.0
    payment_allowance_monthly: float = 0.0

    # 残業等は、支払パターンが「時給」相当(時間×日数×月数)の場合のみ
    # payment_rate を時給とみなして計算する。それ以外のパターン(人日/人月/式)では
    # 時給換算の根拠がないため、残業関連の追加コストは0として扱う
    # (雛形の元の数式は未取得のため、QAで実データと突き合わせて要調整)。
    is_hourly_pattern: bool = False
    overtime_hours_monthly: float = 0.0
    night_overtime_hours_monthly: float = 0.0
    unbilled_leave_hours_monthly: float = 0.0
    overtime_multiplier: float = 1.25
    night_overtime_multiplier: float = 1.5


@dataclass
class LineItemResult:
    sales: float
    payment_base: float
    overtime_pay: float
    night_overtime_pay: float
    unbilled_leave_pay: float
    statutory_insurance: float
    cost_total: float
    profit: float
    margin: float


def calc_line_item(item: LineItemInput, insurance_total_rate: float) -> LineItemResult:
    sales = (
        item.billing_daily_rate * item.billing_days
        + item.billing_commute_monthly
        + item.billing_admin_fee_monthly
        + item.billing_allowance_monthly
    ) * item.headcount

    payment_base = pattern_amount(item.payment_rate, item.payment_qty1, item.payment_qty2, item.payment_qty3) * item.headcount

    hourly_rate = item.payment_rate if item.is_hourly_pattern else 0.0
    overtime_pay = hourly_rate * item.overtime_hours_monthly * item.overtime_multiplier * item.headcount
    night_overtime_pay = hourly_rate * item.night_overtime_hours_monthly * item.night_overtime_multiplier * item.headcount
    unbilled_leave_pay = hourly_rate * item.unbilled_leave_hours_monthly * item.headcount

    labor_cost_base = (
        payment_base
        + overtime_pay
        + night_overtime_pay
        + unbilled_leave_pay
        + item.payment_commute_monthly * item.headcount
        + item.payment_allowance_monthly * item.headcount
    )
    statutory_insurance = labor_cost_base * insurance_total_rate

    cost_total = labor_cost_base + statutory_insurance
    profit = sales - cost_total
    margin = profit / sales if sales else 0.0

    return LineItemResult(
        sales=sales,
        payment_base=payment_base,
        overtime_pay=overtime_pay,
        night_overtime_pay=night_overtime_pay,
        unbilled_leave_pay=unbilled_leave_pay,
        statutory_insurance=statutory_insurance,
        cost_total=cost_total,
        profit=profit,
        margin=margin,
    )


@dataclass
class CostLineInput:
    rate: float = 0.0
    qty1: float | None = 1.0
    qty2: float | None = 1.0
    qty3: float | None = 1.0


def calc_cost_line_amount(item: CostLineInput) -> float:
    return pattern_amount(item.rate, item.qty1, item.qty2, item.qty3)


@dataclass
class FinancialRecordSummary:
    sales: float = 0.0
    cost: float = 0.0
    profit: float = 0.0
    margin: float = 0.0
    sga_cost: float = 0.0
    operating_profit: float = 0.0


def calc_financial_record_summary(
    line_item_results: list[LineItemResult],
    cost_line_amounts: list[float],
    sga_cost: float = 0.0,
) -> FinancialRecordSummary:
    """経費行(COST_LINE)は、実額の根拠(原価計上比率)がQA未確定のため、
    現時点では売上・原価の両方に同額を計上するパススルー方式とする(粗利ゼロ寄与)。
    外注費等でマージンを載せる運用が必要な場合は、QA時に雛形の実データと突き合わせて調整する。
    """
    sales = sum(r.sales for r in line_item_results) + sum(cost_line_amounts)
    cost = sum(r.cost_total for r in line_item_results) + sum(cost_line_amounts)
    profit = sales - cost
    margin = profit / sales if sales else 0.0
    operating_profit = profit - sga_cost
    return FinancialRecordSummary(
        sales=sales, cost=cost, profit=profit, margin=margin, sga_cost=sga_cost, operating_profit=operating_profit
    )
