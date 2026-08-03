#!/usr/bin/env python3
"""Fix database migration state."""
import os
import subprocess
import sys

database_url = os.getenv("DATABASE_URL")
if not database_url:
    print("ERROR: DATABASE_URL not set")
    sys.exit(1)

print("Checking database state...")

# Try to run alembic upgrade head
try:
    result = subprocess.run(
        ["alembic", "upgrade", "head"],
        capture_output=True,
        text=True,
        timeout=60
    )

    if result.returncode == 0:
        print("✅ Alembic migrations completed successfully")
    else:
        stderr = result.stderr
        # If error is about tables already existing, that's OK - just stamp the head
        if "DuplicateTable" in stderr or "already exists" in stderr:
            print("⚠️  Tables already exist, stamping current head...")
            stamp_result = subprocess.run(
                ["alembic", "stamp", "head"],
                capture_output=True,
                text=True,
                timeout=60
            )
            if stamp_result.returncode == 0:
                print("✅ Stamped alembic to current head")
            else:
                print(f"⚠️  Could not stamp head (continuing anyway): {stamp_result.stderr}")
        else:
            print(f"❌ Alembic failed: {stderr}")
            sys.exit(1)

except subprocess.TimeoutExpired:
    print("❌ Alembic migration timed out")
    sys.exit(1)
except Exception as e:
    print(f"❌ Error running migrations: {e}")
    sys.exit(1)

print("✅ Database migration check complete")
