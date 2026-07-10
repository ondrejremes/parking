from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from app.config import SESSION_SECRET, BASE_URL
from app.middleware import SecurityHeadersMiddleware
from app.routers import auth, calendar, reservations, releases, admin, guest_parkings, reporting, occupancy

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


@app.get("/")
async def root():
    return RedirectResponse("/calendar")
