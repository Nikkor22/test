from sqlalchemy.ext.asyncio import AsyncAttrs, create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import text
from app.config import get_settings


class Base(AsyncAttrs, DeclarativeBase):
    pass


settings = get_settings()

engine = create_async_engine(
    settings.database_url,
    echo=settings.debug,
)

async_session = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_session() -> AsyncSession:
    async with async_session() as session:
        yield session


async def run_migrations(conn):
    """Run manual migrations to add missing columns."""
    # List of columns to check/add: (table, column, type, default)
    migrations = [
        ("users", "ical_url", "VARCHAR(500)", None),
        ("users", "last_schedule_sync", "TIMESTAMP", None),
    ]

    for table, column, col_type, default in migrations:
        # Check if column exists
        result = conn.execute(text(f"""
            SELECT column_name FROM information_schema.columns
            WHERE table_name = '{table}' AND column_name = '{column}'
        """))
        if result.fetchone() is None:
            # Add column
            default_clause = f" DEFAULT {default}" if default else ""
            conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} {col_type}{default_clause}"))
            print(f"Added column {column} to {table}")


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        # Run migrations for existing tables
        await conn.run_sync(run_migrations)
