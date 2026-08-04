from __future__ import annotations

import os

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.models import Base

# Streamlit Community Cloud のファイルシステムは再デプロイ・再起動で消える(永続化されない)。
# 初期リリースではローカル/社内共有ドライブ上のSQLiteファイルを想定し、
# クラウド上での長期運用には外部DB(例: Postgres)への切り替えが必要になる(既知の制約)。
DB_PATH = os.environ.get("ESTIMATE_TOOL_DB_PATH", "data/app.db")
_engine = None
_SessionLocal: sessionmaker[Session] | None = None


def get_engine():
    global _engine
    if _engine is None:
        os.makedirs(os.path.dirname(DB_PATH) or ".", exist_ok=True)
        _engine = create_engine(f"sqlite:///{DB_PATH}", echo=False)
    return _engine


def get_session() -> Session:
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(bind=get_engine())
    return _SessionLocal()


def init_db() -> None:
    Base.metadata.create_all(get_engine())
