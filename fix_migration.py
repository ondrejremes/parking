#!/usr/bin/env python3
"""Fix orphaned migration in alembic_version table."""
import os
from sqlalchemy import create_engine, text

database_url = os.getenv("DATABASE_URL")
if not database_url:
    print("ERROR: DATABASE_URL not set")
    exit(1)

try:
    engine = create_engine(database_url)
    with engine.begin() as conn:
        # Check if alembic_version table exists
        result = conn.execute(text(
            "SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'alembic_version')"
        ))
        table_exists = result.scalar()

        if not table_exists:
            print("ℹ️  alembic_version table doesn't exist - will be created by alembic")
            exit(0)

        # Check if h4i5j6k7l8m9 exists and remove it
        result = conn.execute(text("SELECT version_num FROM alembic_version WHERE version_num = 'h4i5j6k7l8m9'"))
        rows = result.fetchall()

        if rows:
            print(f"Found orphaned migration: {rows[0][0]}")
            conn.execute(text("DELETE FROM alembic_version WHERE version_num = 'h4i5j6k7l8m9'"))
            print("✅ Deleted orphaned migration h4i5j6k7l8m9")
        else:
            print("ℹ️  No orphaned migration found")

        # Show current migrations
        result = conn.execute(text("SELECT version_num FROM alembic_version ORDER BY version_num"))
        versions = result.fetchall()
        print(f"\n📋 Current migrations in database ({len(versions)}):")
        for v in versions[-10:]:
            print(f"  - {v[0]}")
except Exception as e:
    print(f"⚠️  Warning during migration fix: {e}")
    # Don't exit with error - let alembic handle it
    exit(0)
