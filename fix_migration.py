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
    with engine.connect() as conn:
        # Check if h4i5j6k7l8m9 exists
        result = conn.execute(text("SELECT version_num FROM alembic_version WHERE version_num = 'h4i5j6k7l8m9'"))
        rows = result.fetchall()

        if rows:
            print(f"Found orphaned migration: {rows[0][0]}")
            conn.execute(text("DELETE FROM alembic_version WHERE version_num = 'h4i5j6k7l8m9'"))
            conn.commit()
            print("✅ Deleted orphaned migration h4i5j6k7l8m9")
        else:
            print("✅ No orphaned migration found")

        # Show current migrations
        result = conn.execute(text("SELECT version_num FROM alembic_version ORDER BY version_num"))
        versions = result.fetchall()
        print(f"\nCurrent migrations ({len(versions)}):")
        for v in versions[-5:]:
            print(f"  - {v[0]}")
except Exception as e:
    print(f"ERROR: {e}")
    exit(1)
