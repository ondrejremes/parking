from datetime import date, timedelta
from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.auth import get_current_user_or_none, generate_csrf_token
from app.services.availability import get_week_availability
from app import models

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


def _week_dates(anchor: date) -> list[date]:
    monday = anchor - timedelta(days=anchor.weekday())
    return [monday + timedelta(days=i) for i in range(5)]  # Po–Pá


@router.get("/", response_class=HTMLResponse)
@router.get("/calendar", response_class=HTMLResponse)
async def calendar_view(
    request: Request,
    week: str | None = Query(None),
    db: Session = Depends(get_db),
):
    user = get_current_user_or_none(request)
    if not user:
        return RedirectResponse("/auth/admin-login")

    try:
        anchor = date.fromisoformat(week) if week else date.today()
    except ValueError:
        anchor = date.today()

    week_dates = _week_dates(anchor)
    prev_week = (week_dates[0] - timedelta(days=7)).isoformat()
    next_week = (week_dates[0] + timedelta(days=7)).isoformat()

    spots = db.query(models.Spot).filter_by(active=True).order_by(models.Spot.floor, models.Spot.number).all()
    availability = get_week_availability(db, week_dates, user["id"])

    return templates.TemplateResponse("calendar.html", {
        "request": request,
        "user": user,
        "spots": spots,
        "week_dates": week_dates,
        "availability": availability,
        "prev_week": prev_week,
        "next_week": next_week,
        "csrf_token": generate_csrf_token(request),
        "today": date.today(),
    })
