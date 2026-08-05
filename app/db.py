from __future__ import annotations

import os
import tempfile

from sqlalchemy import create_engine, inspect
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


def _schema_matches(engine) -> bool:
    """既存DBのテーブル/カラムが、現在のモデル定義と一致しているか確認する。

    このアプリには本格的なマイグレーション機構がない(既知の制約)。
    Streamlit Cloud上のDBはどのみち一時領域で永続化されないため、
    スキーマ不一致を検知したら丸ごと作り直す方式にする。
    """
    inspector = inspect(engine)
    existing_tables = set(inspector.get_table_names())
    for table in Base.metadata.sorted_tables:
        if table.name not in existing_tables:
            return False
        existing_cols = {c["name"] for c in inspector.get_columns(table.name)}
        expected_cols = {c.name for c in table.columns}
        if not expected_cols.issubset(existing_cols):
            return False
    return True


def init_db() -> None:
    engine = get_engine()
    Base.metadata.create_all(engine)
    if not _schema_matches(engine):
        Base.metadata.drop_all(engine)
        Base.metadata.create_all(engine)
