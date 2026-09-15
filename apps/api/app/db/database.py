from collections.abc import Generator

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
from sqlalchemy.pool import StaticPool


class Base(DeclarativeBase):
    pass


def create_database(database_url: str) -> tuple[Engine, sessionmaker[Session]]:
    connect_args = {}
    engine_kwargs = {}
    if database_url.startswith("sqlite"):
        connect_args = {"check_same_thread": False}
        if ":memory:" in database_url:
            engine_kwargs["poolclass"] = StaticPool

    engine = create_engine(
        database_url,
        connect_args=connect_args,
        **engine_kwargs,
    )
    session_factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    return engine, session_factory


def ensure_schema(engine: Engine) -> None:
    """Create the local schema and apply small backward-compatible POC migrations."""
    Base.metadata.create_all(bind=engine)
    if engine.dialect.name != "sqlite":
        return

    inspector = inspect(engine)
    action_columns = {column["name"] for column in inspector.get_columns("action_requests")}
    if "result_payload" not in action_columns:
        with engine.begin() as connection:
            connection.execute(
                text(
                    "ALTER TABLE action_requests "
                    "ADD COLUMN result_payload TEXT NOT NULL DEFAULT '{}'"
                )
            )


def session_scope(session_factory: sessionmaker[Session]) -> Generator[Session, None, None]:
    session = session_factory()
    try:
        yield session
    finally:
        session.close()
