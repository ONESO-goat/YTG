# uvicorn main:app --reload --port 8000
import fastapi
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import inspect, text
from sqlmodel import Session, SQLModel, create_engine

from helpers.config import Config

app = fastapi.FastAPI(title="YTG API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=Config.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

connect_args = {"check_same_thread": False} if Config.database_url.startswith("sqlite") else {}
engine = create_engine(Config.database_url, echo=Config.database_echo, connect_args=connect_args)


def get_session():
    with Session(engine) as session:
        yield session


def _add_missing_sqlite_columns():
    """`create_all` never alters existing tables, so add columns introduced after a table was created.

    Only nullable columns or columns with a scalar default can be added this way, which covers
    everything added so far. Anything more involved needs a real migration tool.
    """
    if engine.dialect.name != "sqlite":
        return
    inspector = inspect(engine)
    with engine.begin() as conn:
        for table in SQLModel.metadata.sorted_tables:
            if not inspector.has_table(table.name):
                continue
            existing = {col["name"] for col in inspector.get_columns(table.name)}
            for column in table.columns:
                if column.name in existing:
                    continue
                col_type = column.type.compile(dialect=engine.dialect)
                default_sql = ""
                default = getattr(column.default, "arg", None)
                if isinstance(default, bool):
                    default_sql = f" DEFAULT {int(default)}"
                elif isinstance(default, (int, float)):
                    default_sql = f" DEFAULT {default}"
                elif isinstance(default, str):
                    default_sql = " DEFAULT '{}'".format(default.replace("'", "''"))
                conn.execute(text(f'ALTER TABLE "{table.name}" ADD COLUMN "{column.name}" {col_type}{default_sql}'))


def create_db_and_tables():
    SQLModel.metadata.create_all(engine)
    _add_missing_sqlite_columns()
