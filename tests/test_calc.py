import datetime as dt

from app.services.calc import (
    CostLineInput,
    LineItemInput,
    calc_cost_line_amount,
    calc_financial_record_summary,
    calc_line_item,
    fiscal_year_of,
    pattern_amount,
)


def test_pattern_amount_single_qty():
    assert pattern_amount(rate=16000, qty1=21, qty2=None, qty3=None) == 336000


def test_pattern_amount_no_qty():
    assert pattern_amount(rate=50000, qty1=None, qty2=None, qty3=None) == 50000


def test_pattern_amount_three_qty_dispatch():
    # 派遣: 時給 x 時間数(1日) x 日数 x 月数
    assert pattern_amount(rate=1400, qty1=8, qty2=20, qty3=1) == 1400 * 8 * 20


def test_fiscal_year_of_april_boundary():
    assert fiscal_year_of(dt.date(2026, 4, 1)) == 2026
    assert fiscal_year_of(dt.date(2026, 3, 31)) == 2025


def test_calc_line_item_outsource_pattern():
    item = LineItemInput(
        billing_daily_rate=16000,
        billing_days=21,
        headcount=1,
        payment_rate=14000,
        payment_qty1=21,
        payment_qty2=1,
        payment_qty3=1,
        is_hourly_pattern=False,
    )
    result = calc_line_item(item, insurance_total_rate=0.157)
    assert result.sales == 336000
    assert result.payment_base == 294000
    assert result.overtime_pay == 0
    assert round(result.statutory_insurance, 2) == round(294000 * 0.157, 2)
    assert round(result.cost_total, 2) == round(294000 * 1.157, 2)
    assert round(result.profit, 2) == round(336000 - 294000 * 1.157, 2)


def test_calc_line_item_hourly_pattern_with_overtime():
    item = LineItemInput(
        billing_daily_rate=17440,
        billing_days=23,
        headcount=1,
        payment_rate=1400,
        payment_qty1=8,
        payment_qty2=23,
        payment_qty3=1,
        is_hourly_pattern=True,
        overtime_hours_monthly=2,
    )
    result = calc_line_item(item, insurance_total_rate=0.0)
    expected_base = 1400 * 8 * 23
    expected_overtime = 1400 * 2 * 1.25
    assert result.payment_base == expected_base
    assert result.overtime_pay == expected_overtime
    assert result.cost_total == expected_base + expected_overtime


def test_calc_cost_line_amount():
    item = CostLineInput(rate=15000, qty1=None, qty2=None, qty3=None)
    assert calc_cost_line_amount(item) == 15000


def test_calc_financial_record_summary_pass_through_cost_lines():
    line_result = calc_line_item(
        LineItemInput(billing_daily_rate=10000, billing_days=10, payment_rate=8000, payment_qty1=10),
        insurance_total_rate=0.1,
    )
    summary = calc_financial_record_summary([line_result], cost_line_amounts=[50000], sga_cost=1000)
    assert summary.sales == line_result.sales + 50000
    assert summary.cost == line_result.cost_total + 50000
    assert round(summary.profit, 2) == round(summary.sales - summary.cost, 2)
    assert round(summary.operating_profit, 2) == round(summary.profit - 1000, 2)
