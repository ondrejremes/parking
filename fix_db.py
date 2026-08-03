#!/usr/bin/env python3
"""Fix alembic_version in Azure PostgreSQL database."""
import os
from sqlalchemy import create_engine, text, inspect

database_url = os.getenv("DATABASE_URL")
if not database_url:
    print("ERROR: DATABASE_URL not set")
    exit(1)

try:
    engine = create_engine(database_url)

    with engine.begin() as conn:
        # Check if tables exist
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        print(f"📋 Tables in database: {len(tables)}")

        # Check if alembic_version exists
        if 'alembic_version' not in tables:
            print("❌ alembic_version table doesn't exist!")
            print("This means database is completely uninitialized.")
            exit(1)

        # Get current migrations
        result = conn.execute(text("SELECT version_num FROM alembic_version ORDER BY version_num"))
        versions = [v[0] for v in result.fetchall()]
        print(f"\n📊 Current migrations in alembic_version ({len(versions)}):")
        for v in versions:
            print(f"  - {v}")

        # Find orphaned/invalid migrations
        VALID = [
            '917ac9762377', '001_system_accounts', 'cedf875aec05',
            '788093be57f5', 'e7c666db6ae8', 'f1a2b3c4d5e6',
            'f2e3d4c5b6a7', 'g3h4i5j6k7l8', 'i5j6k7l8m9n0'
        ]

        invalid = [v for v in versions if v not in VALID]
        if invalid:
            print(f"\n⚠️  Found {len(invalid)} invalid migration(s):")
            for v in invalid:
                print(f"  Deleting: {v}")
                conn.execute(text(f"DELETE FROM alembic_version WHERE version_num = '{v}'"))

        # Show final state
        result = conn.execute(text("SELECT version_num FROM alembic_version ORDER BY version_num"))
        final = [v[0] for v in result.fetchall()]
        print(f"\n✅ Final migrations ({len(final)}):")
        for v in final:
            print(f"  - {v}")

except Exception as e:
    print(f"❌ ERROR: {e}")
    import traceback
    traceback.print_exc()
    exit(1)
