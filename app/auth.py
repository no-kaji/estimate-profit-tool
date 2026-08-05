from __future__ import annotations

import hashlib
import hmac
import os
import traceback
from contextlib import contextmanager

import streamlit as st
from sqlalchemy.orm import Session

from app.models import ErrorLog, User

_PASSWORD_SALT = os.environ.get("ESTIMATE_TOOL_PASSWORD_SALT", "estimate-tool-default-salt")


def hash_password(raw_password: str) -> str:
    return hashlib.sha256((_PASSWORD_SALT + raw_password).encode("utf-8")).hexdigest()


def verify_password(raw_password: str, password_hash: str) -> bool:
    return hmac.compare_digest(hash_password(raw_password), password_hash)


def get_current_user(session: Session) -> User | None:
    user_id = st.session_state.get("auth_user_id")
    if user_id is None:
        return None
    return session.get(User, user_id)


def require_login(session: Session) -> User:
    """未ログインならログインフォームを表示してst.stop()する。ログイン済みならUserを返す。"""
    user = get_current_user(session)
    if user is not None and user.active:
        return user

    st.title("見積収支計算書ツール")
    st.subheader("ログイン")
    with st.form("login_form"):
        username = st.text_input("ユーザーID")
        password = st.text_input("パスワード", type="password")
        submitted = st.form_submit_button("ログイン")
    if submitted:
        candidate = session.query(User).filter(User.username == username, User.active.is_(True)).one_or_none()
        if candidate is not None and verify_password(password, candidate.password_hash):
            st.session_state["auth_user_id"] = candidate.id
            st.rerun()
        else:
            st.error("ユーザーIDまたはパスワードが正しくありません。")
    st.stop()
    raise RuntimeError("unreachable")  # st.stop()で必ず終了するが型チェッカー向けに明示


def logout_button() -> None:
    if st.sidebar.button("ログアウト"):
        st.session_state.pop("auth_user_id", None)
        st.rerun()


@contextmanager
def log_errors(session: Session, page_name: str, user: User | None):
    """ページ本体を囲み、未処理の例外をErrorLogに記録してから再送出する。"""
    try:
        yield
    except Exception as exc:  # noqa: BLE001 - 記録が目的のため意図的に全例外を捕捉
        try:
            session.add(
                ErrorLog(
                    user_id=user.id if user else None,
                    page=page_name,
                    message=f"{exc}\n{traceback.format_exc()}",
                )
            )
            session.commit()
        except Exception:
            session.rollback()
        raise
