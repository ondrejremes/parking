from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool, text
from alembic import context

from app.config import DATABASE_URL

config = context.config
config.set_main_option("sqlalchemy.url", DATABASE_URL)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Empty metadata - we don't use alembic autogenerate
class Base:
    metadata = None

target_metadata = None if Base.metadata is None else Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    # Skip migrations entirely - they're handled by fix_migration.py
    # This prevents CREATE TABLE errors when the database already exists
    print("⚠️  Alembic online mode - skipping migrations (handled elsewhere)")


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
