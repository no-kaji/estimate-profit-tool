from __future__ import annotations

import os
import tempfile

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import Session, sessionmaker

from app.models import Base

# Streamlit Community Cloud上ではGitHubから取り込んだソースツリー(/mount/src/...)が
# 書き込み禁止のため、そこにSQLiteファイルを作成できない。OS標準の一時ディレクトリ配下に
# 保存する(=書き込みは確実に通るが、再デプロイ・再起動でデータは消える/永続化されない)。
# 本番運用では永続ボリュームまたは外部DB(例: Postgres)への切り替えが必要(既知の制約)。
DB_PATH = os.environ.get("ESTIMATE_TOOL_DB_PATH") or os.path.join(tempfile.gettempdir(), "estimate_tool_v3", "app.db")
_engine = None
_SessionLocal: sessionmaker[Session] | None = None
_schema_checked = False


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


def _add_missing_columns(engine) -> None:
    """モデルにあってDBに無い列を、既存データを消さずにALTER TABLEで追加する。

    2026-08-06: 以前はスキーマ不一致を検知したらテーブルを丸ごと作り直していたが、
    そのたびに登録済みユーザー等のデータが消えてしまい「登録情報を維持してほしい」との
    指摘を受けた。列の追加はSQLiteのALTER TABLE ADD COLUMNで既存データを保持したまま行える
    ため、この方式に変更する(列の削除・型変更には対応しない。使われなくなった列は
    残ったままになるが実害はない)。
    """
    inspector = inspect(engine)
    existing_tables = set(inspector.get_table_names())
    with engine.begin() as conn:
        for table in Base.metadata.sorted_tables:
            if table.name not in existing_tables:
                continue
            existing_cols = {c["name"] for c in inspector.get_columns(table.name)}
            for column in table.columns:
                if column.name in existing_cols:
                    continue
                col_type = column.type.compile(dialect=engine.dialect)
                conn.execute(text(f'ALTER TABLE "{table.name}" ADD COLUMN "{column.name}" {col_type}'))


def init_db() -> None:
    """DB初期化。init_db()はStreamlitの全ページ・全rerunで毎回呼ばれるため、
    スキーマ整合性チェックはプロセス起動後の最初の1回だけ実行する。
    """
    global _schema_checked
    engine = get_engine()
    Base.metadata.create_all(engine)  # まだ存在しないテーブルを新規作成(既存データには影響しない)
    if not _schema_checked:
        _add_missing_columns(engine)
        _schema_checked = True
