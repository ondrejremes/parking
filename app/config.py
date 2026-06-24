import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://parking:parking@localhost/parking")
SESSION_SECRET = os.getenv("SESSION_SECRET", "change-me")

AZURE_CLIENT_ID = os.getenv("AZURE_CLIENT_ID", "")
AZURE_CLIENT_SECRET = os.getenv("AZURE_CLIENT_SECRET", "")
AZURE_TENANT_ID = os.getenv("AZURE_TENANT_ID", "")
AZURE_REDIRECT_URI = os.getenv("AZURE_REDIRECT_URI", "http://localhost:8000/auth/callback")

ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD_HASH = os.getenv("ADMIN_PASSWORD_HASH", "")

ACS_CONNECTION_STRING = os.getenv("ACS_CONNECTION_STRING", "")
EMAIL_FROM = os.getenv("EMAIL_FROM", "parking@example.com")

BASE_URL = os.getenv("BASE_URL", "http://localhost:8000")
RESERVATION_HORIZON_DAYS = int(os.getenv("RESERVATION_HORIZON_DAYS", "31"))
