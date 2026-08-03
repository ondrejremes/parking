from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool, text, create_engine
from alembic import context

from app.config import DATABASE_URL
from app.database import Base
import app.models  # noqa: F401 — ensure all models are registered

config = context.config
config.set_main_option("sqlalchemy.url", DATABASE_URL)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Check if we should compare types when running autogenerate
# If alembic_version table doesn't exist, we're in auto-init mode and should compare
try:
    test_engine = create_engine(DATABASE_URL)
    with test_engine.connect() as conn:
        result = conn.execute(text(
            "SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'alembic_version')"
        ))
        alembic_version_exists = result.scalar()
        if not alembic_version_exists:
            # We're initializing, set compare_type to avoid issues
            config.set_section_option("alembic", "compare_type", "false")
    test_engine.dispose()
except Exception:
    # If we can't check, just continue
    pass

target_metadata = Base.metadata


def run_migrations_offline() -> None:
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
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
