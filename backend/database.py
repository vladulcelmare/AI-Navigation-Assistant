from collections.abc import Generator
from sqlalchemy import URL, create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from backend import config

database_url = URL.create(
    drivername="mssql+pyodbc",
    username=config.DB_USER,
    password=config.DB_PASSWORD,
    host=config.DB_SERVER,
    port=config.DB_PORT,
    database=config.DB_NAME,
    query={
        "driver": config.DB_DRIVER,
        "TrustServerCertificate": "yes",
    },
)

engine = create_engine(
    database_url,
    pool_pre_ping=True,
    echo=False,
)

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
)


def get_db() -> Generator[Session]:
    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()


def test_connection() -> int:
    with engine.connect() as connection:
        return connection.execute(text("SELECT 1")).scalar_one()