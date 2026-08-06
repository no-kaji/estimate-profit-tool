from __future__ import annotations

import datetime as dt

from sqlalchemy import ForeignKey, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class ContractType(Base):
    __tablename__ = "contract_types"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(unique=True)
    description: Mapped[str] = mapped_column(default="")
    active: Mapped[bool] = mapped_column(default=True)

    patterns: Mapped[list["PricingPattern"]] = relationship(
        secondary="contract_type_patterns", back_populates="contract_types"
    )


class PricingPattern(Base):
    __tablename__ = "pricing_patterns"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(unique=True)
    qty1_label: Mapped[str | None] = mapped_column(default=None)
    qty2_label: Mapped[str | None] = mapped_column(default=None)
    qty3_label: Mapped[str | None] = mapped_column(default=None)

    contract_types: Mapped[list["ContractType"]] = relationship(
        secondary="contract_type_patterns", back_populates="patterns"
    )

    @property
    def qty_labels(self) -> list[str]:
        return [lbl for lbl in (self.qty1_label, self.qty2_label, self.qty3_label) if lbl]


class ContractTypePattern(Base):
    __tablename__ = "contract_type_patterns"
    __table_args__ = (UniqueConstraint("contract_type_id", "pricing_pattern_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    contract_type_id: Mapped[int] = mapped_column(ForeignKey("contract_types.id"))
    pricing_pattern_id: Mapped[int] = mapped_column(ForeignKey("pricing_patterns.id"))


class InsuranceRateMaster(Base):
    __tablename__ = "insurance_rate_masters"

    id: Mapped[int] = mapped_column(primary_key=True)
    fiscal_year: Mapped[int] = mapped_column(unique=True)  # 西暦(例: 令和7年度 -> 2025)
    health_insurance_rate: Mapped[float] = mapped_column(default=0.0)
    nursing_care_rate: Mapped[float] = mapped_column(default=0.0)
    pension_rate: Mapped[float] = mapped_column(default=0.0)
    child_allowance_rate: Mapped[float] = mapped_column(default=0.0)
    employment_insurance_rate: Mapped[float] = mapped_column(default=0.0)
    workers_comp_rate: Mapped[float] = mapped_column(default=0.0)
    general_contribution_rate: Mapped[float] = mapped_column(default=0.0)

    @property
    def total_rate(self) -> float:
        return (
            self.health_insurance_rate
            + self.nursing_care_rate
            + self.pension_rate
            + self.child_allowance_rate
            + self.employment_insurance_rate
            + self.workers_comp_rate
            + self.general_contribution_rate
        )


class BillingItemMaster(Base):
    __tablename__ = "billing_item_masters"

    id: Mapped[int] = mapped_column(primary_key=True)
    item_name: Mapped[str] = mapped_column(unique=True)
    item_detail: Mapped[str] = mapped_column(default="")
    category: Mapped[str] = mapped_column(default="")  # 職種 or 経費


class CancellationPolicyMaster(Base):
    __tablename__ = "cancellation_policy_masters"

    id: Mapped[int] = mapped_column(primary_key=True)
    policy_name: Mapped[str] = mapped_column(unique=True)
    policy_text_client: Mapped[str] = mapped_column(default="")
    policy_text_internal: Mapped[str] = mapped_column(default="")


class HeadquartersMaster(Base):
    """組織属性: 統括部門名称マスタ。ユーザーの所属割り当てに使う。"""

    __tablename__ = "headquarters_masters"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(unique=True)


class BranchMaster(Base):
    """組織属性: 拠点名称マスタ(=経営ボード明細の「部門名称」として使う)。ユーザーの所属割り当てに使う。"""

    __tablename__ = "branch_masters"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(unique=True)


class RegionMaster(Base):
    """組織属性: 地域区分マスタ。ユーザーの所属割り当てに使う。"""

    __tablename__ = "region_masters"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(unique=True)


ROLE_SYSTEM_ADMIN = "システム管理者"
ROLE_MANAGER = "マネージャー"
ROLE_USER = "ユーザー"
ROLES = [ROLE_SYSTEM_ADMIN, ROLE_MANAGER, ROLE_USER]


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(unique=True)
    display_name: Mapped[str] = mapped_column(default="")
    password_hash: Mapped[str] = mapped_column(default="")
    role: Mapped[str] = mapped_column(default=ROLE_USER)
    headquarters_id: Mapped[int | None] = mapped_column(ForeignKey("headquarters_masters.id"), default=None)
    branch_id: Mapped[int | None] = mapped_column(ForeignKey("branch_masters.id"), default=None)
    region_id: Mapped[int | None] = mapped_column(ForeignKey("region_masters.id"), default=None)
    active: Mapped[bool] = mapped_column(default=True)

    headquarters: Mapped["HeadquartersMaster | None"] = relationship()
    branch: Mapped["BranchMaster | None"] = relationship()
    region: Mapped["RegionMaster | None"] = relationship()
    seal_svg: Mapped[str | None] = mapped_column(default=None)  # マイページで生成する個人印鑑(SVG文字列)

    @property
    def can_delete(self) -> bool:
        return self.role in (ROLE_SYSTEM_ADMIN, ROLE_MANAGER)

    @property
    def can_restore(self) -> bool:
        return self.role == ROLE_SYSTEM_ADMIN

    @property
    def can_view_logs(self) -> bool:
        return self.role == ROLE_SYSTEM_ADMIN

    @property
    def can_manage_users(self) -> bool:
        return self.role == ROLE_SYSTEM_ADMIN

    @property
    def can_manage_company_seal(self) -> bool:
        return self.role == ROLE_MANAGER

    @property
    def can_approve(self) -> bool:
        return self.role == ROLE_MANAGER

    @property
    def can_self_approve(self) -> bool:
        """自身が作成した確定見積を、他者の承認を経ずに自分で承認済みにできるか。"""
        return self.role in (ROLE_SYSTEM_ADMIN, ROLE_MANAGER)


class CompanySeal(Base):
    """社判(会社印)。マネージャー/システム管理者が登録する(全社で1つを最新として使う)。"""

    __tablename__ = "company_seals"

    id: Mapped[int] = mapped_column(primary_key=True)
    svg: Mapped[str] = mapped_column(default="")
    registered_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), default=None)
    registered_at: Mapped[dt.datetime] = mapped_column(default=dt.datetime.utcnow)


class ErrorLog(Base):
    __tablename__ = "error_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    occurred_at: Mapped[dt.datetime] = mapped_column(default=dt.datetime.utcnow)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), default=None)
    page: Mapped[str] = mapped_column(default="")
    message: Mapped[str] = mapped_column(default="")

    user: Mapped["User | None"] = relationship()


class Notification(Base):
    __tablename__ = "notifications"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    message: Mapped[str] = mapped_column(default="")
    created_at: Mapped[dt.datetime] = mapped_column(default=dt.datetime.utcnow)
    read_at: Mapped[dt.datetime | None] = mapped_column(default=None)


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(primary_key=True)
    dept: Mapped[str] = mapped_column(default="")
    client_name: Mapped[str] = mapped_column(default="")
    project_no: Mapped[str] = mapped_column(default="")
    project_name: Mapped[str] = mapped_column(default="")
    contract_start: Mapped[dt.date | None] = mapped_column(default=None)
    contract_end: Mapped[dt.date | None] = mapped_column(default=None)
    copied_from_project_id: Mapped[int | None] = mapped_column(ForeignKey("projects.id"), default=None)
    deleted_at: Mapped[dt.datetime | None] = mapped_column(default=None)

    financial_records: Mapped[list["FinancialRecord"]] = relationship(back_populates="project")


class FinancialRecord(Base):
    __tablename__ = "financial_records"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"))
    record_type: Mapped[str]  # "概算見積" / "確定見積"(2026-08-06: 「実績」は廃止し、収支管理の週次実績に移行)
    contract_type_id: Mapped[int | None] = mapped_column(ForeignKey("contract_types.id"), default=None)
    copied_from_id: Mapped[int | None] = mapped_column(ForeignKey("financial_records.id"), default=None)
    period_start: Mapped[dt.date | None] = mapped_column(default=None)
    period_end: Mapped[dt.date | None] = mapped_column(default=None)
    cancellation_policy_id: Mapped[int | None] = mapped_column(ForeignKey("cancellation_policy_masters.id"), default=None)
    sga_cost: Mapped[float] = mapped_column(default=0.0)
    segment: Mapped[str] = mapped_column(default="")
    product: Mapped[str] = mapped_column(default="")
    region: Mapped[str] = mapped_column(default="")
    order_status: Mapped[str] = mapped_column(default="")
    unit_name: Mapped[str] = mapped_column(default="")
    headquarters_name: Mapped[str] = mapped_column(default="")
    employment_type: Mapped[str] = mapped_column(default="")  # 常勤・CA(見積単位の単一選択、経営ボード明細用)
    deleted_at: Mapped[dt.datetime | None] = mapped_column(default=None)

    # 承認フロー(確定見積の見積書発行用): 下書き -> 申請中 -> 承認済み/却下
    # マネージャー・システム管理者が自ら作成した場合は申請不要でその場で承認済みにできる。
    # ユーザーが作成した場合は、所属拠点(部門)のマネージャーを選んで申請する。
    approval_status: Mapped[str] = mapped_column(default="下書き")
    assigned_approver_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), default=None)
    requested_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), default=None)
    requested_at: Mapped[dt.datetime | None] = mapped_column(default=None)
    approved_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), default=None)
    approved_at: Mapped[dt.datetime | None] = mapped_column(default=None)
    reject_reason: Mapped[str | None] = mapped_column(default=None)
    created_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), default=None)
    created_at: Mapped[dt.datetime] = mapped_column(default=dt.datetime.utcnow)
    updated_at: Mapped[dt.datetime] = mapped_column(default=dt.datetime.utcnow, onupdate=dt.datetime.utcnow)

    project: Mapped["Project"] = relationship(back_populates="financial_records")
    contract_type: Mapped["ContractType | None"] = relationship()
    line_items: Mapped[list["LineItem"]] = relationship(back_populates="financial_record", cascade="all, delete-orphan")
    cost_lines: Mapped[list["CostLine"]] = relationship(back_populates="financial_record", cascade="all, delete-orphan")
    requested_by: Mapped["User | None"] = relationship(foreign_keys=[requested_by_id])
    approved_by: Mapped["User | None"] = relationship(foreign_keys=[approved_by_id])
    created_by: Mapped["User | None"] = relationship(foreign_keys=[created_by_id])
    assigned_approver: Mapped["User | None"] = relationship(foreign_keys=[assigned_approver_id])
    weekly_actuals: Mapped[list["WeeklyActual"]] = relationship(back_populates="financial_record", cascade="all, delete-orphan")


class LineItem(Base):
    """明細行(人件費)。個人名は持たず、請求科目(billing_item)を単位とする。"""

    __tablename__ = "line_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    financial_record_id: Mapped[int] = mapped_column(ForeignKey("financial_records.id"))
    billing_item_id: Mapped[int | None] = mapped_column(ForeignKey("billing_item_masters.id"), default=None)
    billing_item_name_free: Mapped[str | None] = mapped_column(default=None)  # マスタ未登録の自由入力用
    insurance_status: Mapped[str] = mapped_column(default="済")  # 済/未/外注(社内用、顧客提出物には出さない)
    headcount: Mapped[int] = mapped_column(default=1)
    employment_type: Mapped[str] = mapped_column(default="")  # 常勤・CA区分(経営ボード明細用、社内用)
    remarks: Mapped[str] = mapped_column(default="")

    billing_daily_rate: Mapped[float] = mapped_column(default=0.0)
    billing_hourly_rate: Mapped[float] = mapped_column(default=0.0)
    billing_days: Mapped[float] = mapped_column(default=0.0)
    billing_commute_monthly: Mapped[float] = mapped_column(default=0.0)
    billing_admin_fee_monthly: Mapped[float] = mapped_column(default=0.0)
    billing_allowance_monthly: Mapped[float] = mapped_column(default=0.0)

    # 2026-08-06修正: 人件費の原価は請求側のマスタ(契約形式・計算パターン)によらず、
    # 常に「時給×1日の時間数×日数」の固定式で計算する(指摘を受けて汎用パターン式から変更)。
    payment_hourly_rate: Mapped[float] = mapped_column(default=0.0)
    payment_days: Mapped[float] = mapped_column(default=0.0)
    payment_commute_monthly: Mapped[float] = mapped_column(default=0.0)
    payment_allowance_monthly: Mapped[float] = mapped_column(default=0.0)

    standard_hours_daily: Mapped[float] = mapped_column(default=8.0)  # 1日の時間数
    standard_hours_monthly: Mapped[float] = mapped_column(default=0.0)
    overtime_hours_monthly: Mapped[float] = mapped_column(default=0.0)
    night_overtime_hours_monthly: Mapped[float] = mapped_column(default=0.0)
    unbilled_leave_hours_monthly: Mapped[float] = mapped_column(default=0.0)

    financial_record: Mapped["FinancialRecord"] = relationship(back_populates="line_items")
    billing_item: Mapped["BillingItemMaster | None"] = relationship()

    @property
    def billing_item_display(self) -> str:
        if self.billing_item is not None:
            return self.billing_item.item_name
        return self.billing_item_name_free or "(未設定)"


class CostLine(Base):
    """経費行。請求側(顧客への請求額)と原価側(実際にかかる費用)を別々に持つ。

    2026-08-06修正: 従来は単一の単価×数量を売上・原価の両方にパススルー計上していたが、
    「経費の原価入力がない」との指摘を受け、LineItemと同様に請求側/原価側を分離した。
    """

    __tablename__ = "cost_lines"

    id: Mapped[int] = mapped_column(primary_key=True)
    financial_record_id: Mapped[int] = mapped_column(ForeignKey("financial_records.id"))
    category: Mapped[str] = mapped_column(default="")

    billing_pricing_pattern_id: Mapped[int | None] = mapped_column(ForeignKey("pricing_patterns.id"), default=None)
    billing_rate: Mapped[float] = mapped_column(default=0.0)
    billing_qty1: Mapped[float] = mapped_column(default=1.0)
    billing_qty2: Mapped[float] = mapped_column(default=1.0)
    billing_qty3: Mapped[float] = mapped_column(default=1.0)

    cost_pricing_pattern_id: Mapped[int | None] = mapped_column(ForeignKey("pricing_patterns.id"), default=None)
    cost_rate: Mapped[float] = mapped_column(default=0.0)
    cost_qty1: Mapped[float] = mapped_column(default=1.0)
    cost_qty2: Mapped[float] = mapped_column(default=1.0)
    cost_qty3: Mapped[float] = mapped_column(default=1.0)

    timing: Mapped[str] = mapped_column(default="ランニング")  # イニシャル/ランニング

    financial_record: Mapped["FinancialRecord"] = relationship(back_populates="cost_lines")
    billing_pricing_pattern: Mapped["PricingPattern | None"] = relationship(foreign_keys=[billing_pricing_pattern_id])
    cost_pricing_pattern: Mapped["PricingPattern | None"] = relationship(foreign_keys=[cost_pricing_pattern_id])


class WeeklyActual(Base):
    """収支管理メニューで入力する週次実績。対象の確定見積(FinancialRecord)に紐づく。

    経営ボード明細への出力時は、対象月に含まれる週の実績を合算して月次に丸める。
    """

    __tablename__ = "weekly_actuals"

    id: Mapped[int] = mapped_column(primary_key=True)
    financial_record_id: Mapped[int] = mapped_column(ForeignKey("financial_records.id"))
    week_start: Mapped[dt.date] = mapped_column()  # その週の月曜日
    sales: Mapped[float] = mapped_column(default=0.0)
    cost: Mapped[float] = mapped_column(default=0.0)
    sga_cost: Mapped[float] = mapped_column(default=0.0)
    headcount_regular: Mapped[int] = mapped_column(default=0)  # 常勤数
    headcount_position: Mapped[int] = mapped_column(default=0)  # ポジ数
    entered_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), default=None)
    entered_at: Mapped[dt.datetime] = mapped_column(default=dt.datetime.utcnow, onupdate=dt.datetime.utcnow)

    financial_record: Mapped["FinancialRecord"] = relationship(back_populates="weekly_actuals")
    entered_by: Mapped["User | None"] = relationship()

    @property
    def profit(self) -> float:
        return self.sales - self.cost
