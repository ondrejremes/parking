from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware
from apscheduler.schedulers.background import BackgroundScheduler
import logging
import os
import sys

from app.config import SESSION_SECRET, BASE_URL, DATABASE_URL
from app.middleware import SecurityHeadersMiddleware
from app.routers import auth, calendar, reservations, releases, admin, guest_parkings, reporting, occupancy
from app.services import background_tasks

logger = logging.getLogger(__name__)

# Security check: validate secrets are properly configured
def _validate_secrets():
    """Validate that critical secrets are properly configured."""
    # Check if using development defaults (weak secrets)
    if SESSION_SECRET.startswith("dev-") or SESSION_SECRET == "change-me-in-production":
        if os.getenv("SESSION_SECRET"):  # Explicitly set to dev value
            raise RuntimeError("SESSION_SECRET is using development default in production")

    if not DATABASE_URL.startswith("postgresql://"):
        raise RuntimeError("DATABASE_URL is not properly configured or missing")

    # Ensure credentials are actually from environment in production
    env_db = os.getenv("DATABASE_URL")
    env_secret = os.getenv("SESSION_SECRET")
    if BASE_URL.startswith("https"):
        # Production: all secrets must come from environment, not defaults
        if not env_db:
            raise RuntimeError("DATABASE_URL must be set from environment in production")
        if not env_secret:
            raise RuntimeError("SESSION_SECRET must be set from environment in production")
        if len(env_secret) < 32:
            raise RuntimeError("SESSION_SECRET too weak for production (min 32 chars)")

try:
    _validate_secrets()
except RuntimeError as e:
    logger.critical(f"Security validation failed: {e}")
    sys.exit(1)

app = FastAPI(title="Parking", docs_url=None, redoc_url=None)

app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(
    SessionMiddleware,
    secret_key=SESSION_SECRET,
    https_only=BASE_URL.startswith("https"),
    same_site="lax",
)

app.mount("/static", StaticFiles(directory="app/static"), name="static")

app.include_router(auth.router)
app.include_router(calendar.router)
app.include_router(reservations.router)
app.include_router(releases.router)
app.include_router(admin.router)
app.include_router(guest_parkings.router)
app.include_router(occupancy.router)
app.include_router(reporting.router)


@app.on_event("startup")
async def startup_event():
    """Inicializuj background scheduler"""
    scheduler = BackgroundScheduler()

    # Reminder emails - každý den v 19:00
    scheduler.add_job(
        background_tasks.send_reservation_reminders,
        "cron",
        hour=19,
        minute=0,
        id="send_reminders",
        name="Send reservation reminders",
    )

    scheduler.start()
    logger.info("✅ Background scheduler spuštěn")


@app.get("/")
async def root():
    return RedirectResponse("/calendar")
