from __future__ import annotations

import os
import tempfile

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.models import Base

# Streamlit Community Cloud上ではGitHubから取り込んだソースツリー(/mount/src/...)が
# 書き込み禁止のため、そこにSQLiteファイルを作成できない。OS標準の一時ディレクトリ配下に
# 保存する(=書き込みは確実に通るが、再デプロイ・再起動でデータは消える/永続化されない)。
# 本番運用では永続ボリュームまたは外部DB(例: Postgres)への切り替えが必要(既知の制約)。
DB_PATH = os.environ.get("ESTIMATE_TOOL_DB_PATH") or os.path.join(tempfile.gettempdir(), "estimate_tool", "app.db")
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
