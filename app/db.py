from __future__ import annotations

import io
import os
import tempfile

import streamlit as st
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import Session, sessionmaker

from app.models import Base

# 2026-08-06: 永続化のためPostgreSQL(VPS上、SSHトンネル経由)への接続に対応した。
# Streamlit Secrets(st.secrets)に [postgres]/[ssh_tunnel] セクションが設定されていれば
# そちらを使い、無ければ従来通りローカル開発用のSQLite(一時ディレクトリ、非永続)にフォールバックする。
_engine = None
_SessionLocal: sessionmaker[Session] | None = None
_schema_checked = False
_tunnel = None


def _secrets_available() -> bool:
    try:
        return "postgres" in st.secrets and bool(st.secrets["postgres"].get("enabled", False))
    except Exception:
        return False


def _start_ssh_tunnel():
    """SSHトンネルを1プロセスにつき1回だけ張り、以降は使い回す。
    PostgreSQL自体はVPS上でlocalhost(127.0.0.1)のみで待ち受けており、外部には公開していない
    (セキュリティ方針に合わせ、ポート開放やpg_hba.confの変更は行わない)。
    """
    global _tunnel
    if _tunnel is not None and _tunnel.is_active:
        return _tunnel

    from sshtunnel import SSHTunnelForwarder
    import paramiko

    ssh_cfg = st.secrets["ssh_tunnel"]
    pg_cfg = st.secrets["postgres"]

    pkey = paramiko.Ed25519Key.from_private_key(io.StringIO(ssh_cfg["ssh_private_key"]))

    tunnel = SSHTunnelForwarder(
        (ssh_cfg["ssh_host"], int(ssh_cfg.get("ssh_port", 22))),
        ssh_username=ssh_cfg["ssh_user"],
        ssh_pkey=pkey,
        remote_bind_address=(pg_cfg.get("db_host", "127.0.0.1"), int(pg_cfg.get("db_port", 5432))),
    )
    tunnel.start()
    _tunnel = tunnel
    return tunnel


def get_engine():
    global _engine
    if _engine is not None:
        return _engine

    if _secrets_available():
        tunnel = _start_ssh_tunnel()
        pg_cfg = st.secrets["postgres"]
        url = (
            f"postgresql+psycopg2://{pg_cfg['db_user']}:{pg_cfg['db_password']}"
            f"@127.0.0.1:{tunnel.local_bind_port}/{pg_cfg['db_name']}"
        )
        _engine = create_engine(url, echo=False, pool_pre_ping=True)
    else:
        # フォールバック: ローカル開発用のSQLite。Streamlit Community Cloud上では
        # ソースツリーが読み取り専用のため、OS標準の一時ディレクトリに保存する
        # (=永続化されない。本番運用ではPostgreSQL接続の設定を推奨)。
        db_path = os.environ.get("ESTIMATE_TOOL_DB_PATH") or os.path.join(
            tempfile.gettempdir(), "estimate_tool_v3", "app.db"
        )
        os.makedirs(os.path.dirname(db_path) or ".", exist_ok=True)
        _engine = create_engine(f"sqlite:///{db_path}", echo=False)

    return _engine


def get_session() -> Session:
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(bind=get_engine())
    return _SessionLocal()


def _add_missing_columns(engine) -> None:
    """モデルにあってDBに無い列を、既存データを消さずにALTER TABLEで追加する
    (SQLite・PostgreSQLどちらでも動く)。列の削除・型変更には対応しない。
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
