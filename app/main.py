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

# Security check: in production, secrets must be from environment
is_production = BASE_URL.startswith("https") and not os.getenv("DEBUG")
if is_production:
    if not os.getenv("SESSION_SECRET"):
        logger.critical("❌ SESSION_SECRET must be set in production environment")
        sys.exit(1)
    if not os.getenv("DATABASE_URL"):
        logger.critical("❌ DATABASE_URL must be set in production environment")
        sys.exit(1)
    if SESSION_SECRET.startswith("dev-"):
        logger.critical("❌ SESSION_SECRET is using development default in production!")
        sys.exit(1)
    if not DATABASE_URL.startswith("postgresql://"):
        logger.critical("❌ DATABASE_URL is not valid in production!")
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
