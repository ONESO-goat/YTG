"""migrate_sqlite brings a database created by an older version up to date."""

from sqlalchemy import create_engine, inspect, text
from sqlmodel import SQLModel

from db import migrate_sqlite


def test_old_database_is_upgraded(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'old.db'}")
    with engine.begin() as conn:
        # A trimmed-down guardian_session as the first versions created it
        conn.execute(
            text(
                "CREATE TABLE guardian_session (id VARCHAR PRIMARY KEY, user_id VARCHAR NOT NULL, "
                "guardian_id VARCHAR NOT NULL, active BOOLEAN NOT NULL, total_alerts INTEGER NOT NULL, "
                "streak INTEGER NOT NULL, events JSON)"
            )
        )
        conn.execute(text("CREATE TABLE user_history (id VARCHAR PRIMARY KEY)"))
        conn.execute(text("INSERT INTO guardian_session VALUES ('s1', 'u1', 'g1', 0, 3, 2, '[]')"))

    SQLModel.metadata.create_all(engine)  # creates the tables that don't exist yet
    migrate_sqlite(engine)

    inspector = inspect(engine)
    columns = {c["name"] for c in inspector.get_columns("guardian_session")}
    assert {"total_alerts", "streak", "events"}.isdisjoint(columns)
    assert {"last_frame_hash", "episode_penalties", "warning_started_at"} <= columns
    assert not inspector.has_table("user_history")
    assert "ix_guardian_session_user_guardian" in {
        i["name"] for i in inspector.get_indexes("guardian_session")
    }

    with engine.begin() as conn:
        # Existing rows survive, and new rows no longer need the legacy NOT NULL columns
        assert conn.execute(text("SELECT active, episode_penalties FROM guardian_session")).one() == (0, 0)
        conn.execute(
            text("INSERT INTO guardian_session (id, user_id, guardian_id, active) VALUES ('s2','u','g',1)")
        )

    # Running it again is a no-op
    migrate_sqlite(engine)
