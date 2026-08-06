import datetime as dt
import random

import streamlit as st
from sqlalchemy import select

from app.auth import log_errors, logout_button, require_login
from app.db import get_session, init_db
from app.models import FinancialRecord, Notification, Project
from app.seed import DEFAULT_ADMIN_PASSWORD, DEFAULT_ADMIN_USERNAME
from app.ui import apply_theme

init_db()
session = get_session()
user = require_login(session)
apply_theme()
logout_button()

GREETINGS = ["おはようございます", "こんにちは", "こんばんは"]
TIPS = [
    "見積入力の「見積書プレビューを表示」ボタンで、お客様向けの見た目をいつでも確認できます。",
    "確定見積は、承認されると自動的に社判が配置されます。",
    "収支管理は「受注」を選んだ確定見積だけが対象です。",
    "マイページから、自分がこれまで作った見積の履歴を一覧で振り返れます。",
    "計算パターンやマスタは、システム管理から自由に増やせます。",
]

with log_errors(session, "00_ホーム", user):
    hour = dt.datetime.now().hour
    greeting = GREETINGS[0] if hour < 11 else GREETINGS[1] if hour < 18 else GREETINGS[2]

    st.markdown(
        f"""
        <div style="
            background: linear-gradient(120deg, #6a5fd3 0%, #8f7ff0 55%, #a99cf5 100%);
            border-radius: 22px; padding: 28px 32px; color: white; margin-bottom: 22px;
            box-shadow: 0 10px 30px rgba(106, 95, 211, 0.25);">
            <div style="font-size: 14px; opacity: 0.85;">{greeting}、{user.display_name}さん 👋</div>
            <div style="font-size: 28px; font-weight: 800; margin-top: 4px;">収支ワークフローツール</div>
            <div style="font-size: 13px; opacity: 0.85; margin-top: 6px;">
                ロール: {user.role} ・ 今日も見積と収支の管理、おまかせください。
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    unread = session.execute(
        select(Notification).where(Notification.user_id == user.id, Notification.read_at.is_(None)).order_by(Notification.created_at.desc())
    ).scalars().all()
    if unread:
        st.subheader("🔔 通知")
        for n in unread:
            nc1, nc2 = st.columns([5, 1])
            nc1.info(f"{n.created_at}: {n.message}")
            if nc2.button("既読にする", key=f"read_{n.id}"):
                n.read_at = dt.datetime.utcnow()
                session.commit()
                st.rerun()

    # ---------------------------------------------------------------
    # クイック統計
    # ---------------------------------------------------------------
    project_count = session.execute(select(Project).where(Project.deleted_at.is_(None))).scalars().all()
    confirmed_count = session.execute(select(FinancialRecord).where(FinancialRecord.record_type == "確定見積", FinancialRecord.deleted_at.is_(None))).scalars().all()
    won_count = [r for r in confirmed_count if r.order_result == "受注"]
    pending_for_me = []
    if user.can_approve:
        pending_for_me = [
            r for r in session.execute(
                select(FinancialRecord).where(FinancialRecord.approval_status == "申請中")
            ).scalars().all()
            if r.assigned_approver_id in (None, user.id)
        ]

    stat_cols = st.columns(4 if user.can_approve else 3)
    stats = [
        ("📁", "登録案件数", len(project_count)),
        ("📝", "確定見積", len(confirmed_count)),
        ("🟢", "受注済み", len(won_count)),
    ]
    if user.can_approve:
        stats.append(("🟡", "あなたの承認待ち", len(pending_for_me)))
    for col, (icon, label, value) in zip(stat_cols, stats):
        with col:
            st.markdown(
                f"""
                <div style="background: var(--bg, #f5f6f8); border: 1px solid rgba(58,53,100,0.12);
                    border-radius: 16px; padding: 14px 16px; text-align: center;">
                    <div style="font-size: 22px;">{icon}</div>
                    <div style="font-size: 22px; font-weight: 800; font-family: ui-monospace, monospace;">{value}</div>
                    <div style="font-size: 11.5px; color: #7a739e;">{label}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    st.markdown(
        f"<div style='margin: 18px 0 6px; font-size: 12.5px; color: #7a739e;'>💡 {random.choice(TIPS)}</div>",
        unsafe_allow_html=True,
    )

    # ---------------------------------------------------------------
    # メニューカード
    # ---------------------------------------------------------------
    st.markdown("<div style='height: 8px;'></div>", unsafe_allow_html=True)
    MENU_CARDS = [
        ("📁", "案件一覧", "案件の検索・新規登録・複製・削除ができます。"),
        ("📝", "見積入力", "契約形式を選んで見積(概算/確定)を作成。収支は自動計算されます。"),
        ("💰", "収支管理", "受注が決まった確定見積を選んで、週次の実績を入力します。"),
        ("📈", "データ連携", "確定見積と週次実績を、経営ボード明細形式で書き出せます。"),
    ]
    if user.can_manage_users:
        MENU_CARDS.append(("🗂️", "マスタ管理", "契約形式・計算パターン・請求項目などの各種マスタを編集します。"))
        MENU_CARDS.append(("⚙️", "システム管理", "ユーザーの権限・組織属性の割り当て、エラーログの確認ができます。"))
    else:
        MENU_CARDS.append(("🙋", "マイページ", "個人印鑑の作成と、自分が作った見積の履歴を確認できます。"))
    if user.can_manage_company_seal:
        MENU_CARDS.append(("🔖", "社判管理", "確定見積の承認時に配置される社判を登録します。"))
    if user.can_approve:
        MENU_CARDS.append(("✅", "承認", "確定見積の承認申請を確認し、承認・却下できます。"))

    card_cols = st.columns(2)
    for i, (icon, title, desc) in enumerate(MENU_CARDS):
        with card_cols[i % 2]:
            st.markdown(
                f"""
                <div style="border: 1px solid rgba(58,53,100,0.12); border-radius: 18px;
                    padding: 16px 18px; margin-bottom: 14px; background: white;
                    transition: transform 0.15s ease, box-shadow 0.15s ease;">
                    <div style="font-size: 22px;">{icon}</div>
                    <div style="font-weight: 800; font-size: 15px; margin-top: 4px;">{title}</div>
                    <div style="font-size: 12.5px; color: #7a739e; margin-top: 4px;">{desc}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
    st.caption("↑ 実際に開くには、左のサイドバーから選んでください。")

    if user.username == DEFAULT_ADMIN_USERNAME:
        st.warning(
            f"初期管理者アカウント(ID: {DEFAULT_ADMIN_USERNAME} / 初期パスワード: {DEFAULT_ADMIN_PASSWORD})でログインしています。"
            "システム管理からユーザーを作成し、初期パスワードは早めに変更してください。"
        )
        st.info(
            "動作確認用のサンプルアカウントも自動投入されています。\n\n"
            "- マネージャー: ID `manager1` / パスワード `manager123`\n"
            "- ユーザー: ID `user1` / パスワード `user123`\n\n"
            "この2アカウントは同じ拠点に所属しているため、承認フロー(ユーザーが申請しマネージャーが"
            "承認する)をすぐに試せます。"
        )

session.close()
