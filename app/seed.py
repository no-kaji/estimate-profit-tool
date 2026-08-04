from __future__ import annotations

from sqlalchemy.orm import Session

from app.db import get_session, init_db
from app.models import (
    BillingItemMaster,
    CancellationPolicyMaster,
    ContractType,
    ContractTypePattern,
    InsuranceRateMaster,
    PricingPattern,
)

PRICING_PATTERNS = [
    {"name": "人日×日数", "qty1_label": "日数", "qty2_label": None, "qty3_label": None},
    {"name": "人月×月数", "qty1_label": "月数", "qty2_label": None, "qty3_label": None},
    {"name": "式×日数", "qty1_label": "日数", "qty2_label": None, "qty3_label": None},
    {"name": "式×月数", "qty1_label": "月数", "qty2_label": None, "qty3_label": None},
    {"name": "式のみ", "qty1_label": None, "qty2_label": None, "qty3_label": None},
    {"name": "時間×日数×月数", "qty1_label": "時間数(1日)", "qty2_label": "日数", "qty3_label": "月数"},
]

CONTRACT_TYPES = [
    {"name": "業務委託", "description": "人日・人月・式単位で支払う委託契約", "patterns": ["人日×日数", "人月×月数", "式×日数", "式×月数"]},
    {"name": "派遣", "description": "時給×時間数×日数×月数で計算", "patterns": ["時間×日数×月数"]},
    {"name": "システム利用料", "description": "月額・都度払いの利用料", "patterns": ["式×月数", "式のみ"]},
    {"name": "その他", "description": "上記に当てはまらない契約", "patterns": ["式×日数", "式×月数", "式のみ"]},
]

# 令和7年度(西暦2025年度、2025-04〜2026-03)の法定福利費率。
# 参照資料 references/雛型_見積収支計算書_Ver2.xlsx の料率マスタ(AN1:AR11)より。
INSURANCE_RATE_2025 = {
    "fiscal_year": 2025,
    "health_insurance_rate": 0.04955,
    "nursing_care_rate": 0.00795,
    "pension_rate": 0.0915,
    "child_allowance_rate": 0.0036,
    "employment_insurance_rate": 0.009,
    "workers_comp_rate": 0.00264,
    "general_contribution_rate": 0.00002,
}

BILLING_ITEMS = [
    {"item_name": "プロモーションスタッフ", "category": "職種", "item_detail": "イベントのプロモーション活動(企画・デザイン・販売促進)を行うスタッフ"},
    {"item_name": "フィールドスタッフ", "category": "職種", "item_detail": "店頭で消費者や店員等とコミュニケーションを取り販売・案内・説明・受付などの業務と売り場改善を行うスタッフ"},
    {"item_name": "ラウンダー", "category": "職種", "item_detail": "担当する店舗や企業を定期的に巡回し、商品のアフターフォローを行う営業をするスタッフ"},
    {"item_name": "マネージャー", "category": "職種", "item_detail": "本部に籍を置きながら複数の店舗を巡回して管理・監督するスタッフ"},
    {"item_name": "事務局長", "category": "職種", "item_detail": "事務局等の運営管理の統括を行うスタッフ"},
    {"item_name": "オペレーター", "category": "職種", "item_detail": "コールセンター等でのアウトバウンド・インバウンドを行うスタッフ"},
    {"item_name": "事務受付スタッフ", "category": "職種", "item_detail": "企業等での事務や受付、内勤業務を行うスタッフ"},
]

CANCELLATION_POLICIES = [
    {
        "policy_name": "顧客都合のみ",
        "policy_text_client": "貴社に起因する事由によって、本業務の全部又は一部の実施を中止又は延期した場合、本書記載の委託料の100%相当額を請求するものとします。",
        "policy_text_internal": "当社に起因する事由によって、本業務の全部又は一部の実施を中止又は延期した場合、本書記載の委託料の100%相当額を支払うものとする。",
    },
    {
        "policy_name": "天災等の不可抗力も可",
        "policy_text_client": "貴社に起因する事由による中止・延期は委託料の100%相当額を請求します。天災等の不可抗力による中止・延期は、貴社との協議の上、委託料の60%〜100%相当額を請求するものとします。",
        "policy_text_internal": "当社に起因する事由による中止・延期は委託料の100%相当額を支払います。天災等の不可抗力による中止・延期は、貴社との協議の上、委託料の60%〜100%相当額を支払うものとする。",
    },
    {"policy_name": "基本契約書で締結済", "policy_text_client": "(基本契約書の定めによる)", "policy_text_internal": ""},
    {"policy_name": "覚書で締結済", "policy_text_client": "(覚書の定めによる)", "policy_text_internal": ""},
]


def seed_if_empty(session: Session) -> None:
    if session.query(PricingPattern).count() == 0:
        for p in PRICING_PATTERNS:
            session.add(PricingPattern(**p))
        session.flush()

    if session.query(ContractType).count() == 0:
        pattern_by_name = {p.name: p for p in session.query(PricingPattern).all()}
        for c in CONTRACT_TYPES:
            ct = ContractType(name=c["name"], description=c["description"])
            session.add(ct)
            session.flush()
            for pname in c["patterns"]:
                session.add(ContractTypePattern(contract_type_id=ct.id, pricing_pattern_id=pattern_by_name[pname].id))

    if session.query(InsuranceRateMaster).count() == 0:
        session.add(InsuranceRateMaster(**INSURANCE_RATE_2025))

    if session.query(BillingItemMaster).count() == 0:
        for b in BILLING_ITEMS:
            session.add(BillingItemMaster(**b))

    if session.query(CancellationPolicyMaster).count() == 0:
        for c in CANCELLATION_POLICIES:
            session.add(CancellationPolicyMaster(**c))

    session.commit()


def main() -> None:
    init_db()
    session = get_session()
    try:
        seed_if_empty(session)
    finally:
        session.close()


if __name__ == "__main__":
    main()
