#!/usr/bin/env python3
"""Fix database migration state."""
import os
import subprocess
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
    'j6k7l8m9n0o1',  # add_soc_user
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

        # Check if users table exists
        result = conn.execute(text(
            "SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'users')"
        ))
        users_exists = result.scalar()

        # Get current migrations
        result = conn.execute(text("SELECT version_num FROM alembic_version ORDER BY version_num"))
        current = [v[0] for v in result.fetchall()]

        print(f"Current migrations in DB: {len(current)}")
        for v in current:
            print(f"  - {v}")

        # If users table exists but alembic_version is empty, initialize it
        if users_exists and len(current) == 0:
            print("\n⚠️  users table exists but alembic_version is empty - initializing...")
            for migration in VALID_MIGRATIONS:
                conn.execute(text(f"INSERT INTO alembic_version (version_num) VALUES ('{migration}')"))
                print(f"  ✓ {migration}")
            print("✅ Initialized alembic_version with all migrations")
            exit(0)

        # Remove any invalid migrations
        invalid = [v for v in current if v not in VALID_MIGRATIONS]
        if invalid:
            print(f"\nRemoving {len(invalid)} invalid migration(s):")
            for v in invalid:
                print(f"  - {v}")
                conn.execute(text(f"DELETE FROM alembic_version WHERE version_num = '{v}'"))

        # Check if we're at the latest valid migration
        if current:
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

# Try to run alembic upgrade head
print("\nRunning alembic migrations...")
try:
    result = subprocess.run(["alembic", "upgrade", "head"], check=True, capture_output=True, text=True)
    print("✅ Alembic migrations completed")
except subprocess.CalledProcessError as e:
    if "DuplicateTable" in e.stderr or "already exists" in e.stderr:
        print("⚠️  Tables already exist, stamping current head...")
        try:
            subprocess.run(["alembic", "stamp", "head"], check=True, capture_output=True, text=True)
            print("✅ Stamped alembic to current head")
        except subprocess.CalledProcessError as e2:
            print(f"❌ Failed to stamp head: {e2.stderr}")
            exit(1)
    else:
        print(f"❌ Alembic migration failed: {e.stderr}")
        exit(1)
