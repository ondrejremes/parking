#!/usr/bin/env python3
"""Fix database migration state."""
import os
import sys
from sqlalchemy import create_engine, text

database_url = os.getenv("DATABASE_URL")
if not database_url:
    print("ERROR: DATABASE_URL not set")
    sys.exit(1)

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
    'j6k7l8m9n0o1',  # add_soc_user
]

print("Checking database migration state...")

try:
    engine = create_engine(database_url)
    with engine.begin() as conn:
        # Check if alembic_version table exists
        result = conn.execute(text(
            "SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'alembic_version')"
        ))
        table_exists = result.scalar()

        if not table_exists:
            print("ℹ️  alembic_version table doesn't exist yet")
        else:
            # Get current migrations
            result = conn.execute(text("SELECT version_num FROM alembic_version ORDER BY version_num"))
            current = [v[0] for v in result.fetchall()]

            print(f"Current migrations in DB: {len(current)}")

            if len(current) == 0:
                # alembic_version exists but is empty - check if users table exists
                result = conn.execute(text(
                    "SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'users')"
                ))
                users_exists = result.scalar()

                if users_exists:
                    print("⚠️  users table exists but alembic_version is empty - initializing...")
                    for migration in VALID_MIGRATIONS:
                        conn.execute(text(f"INSERT INTO alembic_version (version_num) VALUES ('{migration}')"))
                        print(f"  ✓ {migration}")
                    print("✅ Initialized alembic_version with all migrations")
                else:
                    print("⚠️  alembic_version is empty and users table doesn't exist")
            else:
                # Check if we're at the latest migration
                last = current[-1]
                expected = VALID_MIGRATIONS[-1]
                if last == expected:
                    print(f"✅ Database is at latest migration: {last}")
                else:
                    print(f"⚠️  Database at {last}, expected {expected}")

except Exception as e:
    print(f"⚠️  Could not check migration state: {e}")

print("✅ Migration check complete")
