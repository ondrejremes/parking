#!/usr/bin/env python3
"""Fix database migration state."""
import os
from sqlalchemy import create_engine, text

database_url = os.getenv("DATABASE_URL")
if not database_url:
    print("ERROR: DATABASE_URL not set")
    exit(1)

# List of all valid migrations in order
VALID_MIGRATIONS = [
    '917ac9762377',  # init
    '001_system_accounts',
    'cedf875aec05',  # add_password_hash_to_users
    '788093be57f5',  # add_can_manage_guests_and_can_manage_
    'e7c666db6ae8',  # add_can_view_reports_to_users
    'f1a2b3c4d5e6',  # add_contact_user_to_guest_parkings
    'f2e3d4c5b6a7',  # add_active_flag_to_users
    'g3h4i5j6k7l8',  # add_audit_and_security_logging
    'i5j6k7l8m9n0',  # fix_migration_chain
]

try:
    engine = create_engine(database_url)
    with engine.begin() as conn:
        # Check if alembic_version table exists
        result = conn.execute(text(
            "SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'alembic_version')"
        ))
        table_exists = result.scalar()

        if not table_exists:
            print("ℹ️  alembic_version table doesn't exist - alembic will create it")
            exit(0)

        # Get current migrations
        result = conn.execute(text("SELECT version_num FROM alembic_version ORDER BY version_num"))
        current = [v[0] for v in result.fetchall()]

        print(f"Current migrations in DB: {len(current)}")
        for v in current:
            print(f"  - {v}")

        # Remove any invalid migrations (h4i5j6k7l8m9)
        invalid = [v for v in current if v not in VALID_MIGRATIONS]
        if invalid:
            print(f"\nRemoving {len(invalid)} invalid migration(s):")
            for v in invalid:
                print(f"  - {v}")
                conn.execute(text(f"DELETE FROM alembic_version WHERE version_num = '{v}'"))

        # Check if we're at the latest valid migration
        result = conn.execute(text("SELECT version_num FROM alembic_version ORDER BY version_num DESC LIMIT 1"))
        last = result.scalar()
        expected_last = VALID_MIGRATIONS[-1]

        if last == expected_last:
            print(f"\n✅ Database is up to date at {last}")
        else:
            print(f"\n⚠️  Database is at {last}, expected {expected_last}")
            print("Alembic will handle remaining migrations")

except Exception as e:
    print(f"⚠️  Warning: {e}")
    # Don't fail - let alembic handle it
    exit(0)
