import os
import subprocess
from dotenv import load_dotenv

load_dotenv()

# Get version from git commit or use default
try:
    GIT_COMMIT = subprocess.check_output(['git', 'rev-parse', '--short', 'HEAD'], cwd=os.path.dirname(os.path.dirname(__file__))).decode().strip()
    APP_VERSION = f"v1.5.0+{GIT_COMMIT}"
except:
    APP_VERSION = "v1.5.0"

_DB_URL = os.getenv("DATABASE_URL")
_SESSION_SECRET = os.getenv("SESSION_SECRET")

# Defaults only for local development
if _DB_URL:
    DATABASE_URL = _DB_URL
else:
    DATABASE_URL = "postgresql://parking:parking@localhost/parking"

if _SESSION_SECRET:
    SESSION_SECRET = _SESSION_SECRET
else:
    SESSION_SECRET = "dev-key-change-in-production"

AZURE_CLIENT_ID = os.getenv("AZURE_CLIENT_ID", "")
AZURE_CLIENT_SECRET = os.getenv("AZURE_CLIENT_SECRET", "")
AZURE_TENANT_ID = os.getenv("AZURE_TENANT_ID", "")

ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD_HASH = os.getenv("ADMIN_PASSWORD_HASH", "")

ACS_CONNECTION_STRING = os.getenv("ACS_CONNECTION_STRING", "")
EMAIL_FROM = os.getenv("EMAIL_FROM", "DoNotReply@alintrust.cz")

BASE_URL = os.getenv("BASE_URL", "http://localhost:8000")
AZURE_REDIRECT_URI = os.getenv("AZURE_REDIRECT_URI", f"{BASE_URL}/auth/callback")
RESERVATION_HORIZON_DAYS = int(os.getenv("RESERVATION_HORIZON_DAYS", "31"))
