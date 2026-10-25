"""Database engine, sessions and lightweight schema migrations."""

import logging

from sqlalchemy import event, inspect, text
from sqlalchemy.engine import Engine
from sqlmodel import Session, SQLModel, create_engine

from helpers.config import Config

log = logging.getLogger(__name__)

_is_sqlite = Config.database_url.startswith("sqlite")
engine = create_engine(
    Config.database_url,
    echo=Config.database_echo,
    connect_args={"check_same_thread": False} if _is_sqlite else {},
)


if _is_sqlite:

    @event.listens_for(engine, "connect")
    def _sqlite_pragmas(dbapi_connection, _record):
        cursor = dbapi_connection.cursor()
        # WAL lets the scan endpoint write while dashboards read; busy_timeout waits instead of failing
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA busy_timeout=5000")
        cursor.execute("PRAGMA synchronous=NORMAL")
        cursor.close()


def get_session():
    with Session(engine) as session:
        yield session


# Columns and tables that earlier versions created but nothing uses any more.
# Old NOT NULL columns without a default would otherwise break inserts.
LEGACY_COLUMNS = {
    "guardian_session": [
        "total_alerts",
        "amount_of_warnings_ignored",
        "amount_of_warnings_listened",
        "points_pending",
        "points_gain_daily_limit",
        "streak",
        "previous_image_bytes",
        "events",
    ],
    "guardian": ["code"],
}
LEGACY_TABLES = ["user_history", "device_ip", "recent_activity", "createdfirstfewrewards"]


def _column_default_sql(column) -> str:
    default = getattr(column.default, "arg", None)
    if isinstance(default, bool):
        return f" DEFAULT {int(default)}"
    if isinstance(default, (int, float)):
        return f" DEFAULT {default}"
    if isinstance(default, str):
        return " DEFAULT '{}'".format(default.replace("'", "''"))
    return ""


def migrate_sqlite(bind: Engine) -> None:
    """Bring an existing SQLite database up to the current models.

    `create_all` only creates missing tables, so this adds new columns and indexes and removes
    legacy ones. It handles additive changes; anything more involved needs a real migration tool.
    """
    if bind.dialect.name != "sqlite":
        return
    inspector = inspect(bind)
    with bind.begin() as conn:
        for table in SQLModel.metadata.sorted_tables:
            if not inspector.has_table(table.name):
                continue
            existing = {col["name"] for col in inspector.get_columns(table.name)}
            for column in table.columns:
                if column.name not in existing:
                    col_type = column.type.compile(dialect=bind.dialect)
                    conn.execute(
                        text(
                            f'ALTER TABLE "{table.name}" ADD COLUMN "{column.name}" '
                            f"{col_type}{_column_default_sql(column)}"
                        )
                    )
                    log.info("Added column %s.%s", table.name, column.name)
            for legacy in LEGACY_COLUMNS.get(table.name, []):
                if legacy in existing:
                    conn.execute(text(f'ALTER TABLE "{table.name}" DROP COLUMN "{legacy}"'))
                    log.info("Dropped legacy column %s.%s", table.name, legacy)
            for index in table.indexes:
                index.create(conn, checkfirst=True)

        for legacy_table in LEGACY_TABLES:
            if inspector.has_table(legacy_table):
                conn.execute(text(f'DROP TABLE "{legacy_table}"'))
                log.info("Dropped legacy table %s", legacy_table)


def init_db() -> None:
    # Importing the model modules registers their tables
    import models.guardian_session  # noqa: F401
    import models.models  # noqa: F401
    import models.progress  # noqa: F401

    SQLModel.metadata.create_all(engine)
    migrate_sqlite(engine)
