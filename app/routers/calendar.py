import calendar
from datetime import date, timedelta
from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.enums import Shift
from app.services.auth import get_current_user_or_none, generate_csrf_token
from app.services.availability import get_week_availability, get_week_detail, get_month_summary
from app import models

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

_CZECH_DAYS_SHORT  = ['Po', 'Út', 'St', 'Čt', 'Pá', 'So', 'Ne']
_CZECH_MONTHS_GEN  = ['ledna', 'února', 'března', 'dubna', 'května', 'června',
                      'července', 'srpna', 'září', 'října', 'listopadu', 'prosince']
_CZECH_MONTHS_NOM  = ['Leden', 'Únor', 'Březen', 'Duben', 'Květen', 'Červen',
                      'Červenec', 'Srpen', 'Září', 'Říjen', 'Listopad', 'Prosinec']

SHIFT_LABELS = {
    Shift.FULL_DAY: "Celý den",
    Shift.DAY:      "Denní směna (8:00–18:00)",
    Shift.NIGHT:    "Noční směna (18:00–09:00)",
}
SHIFT_SHORT = {
    Shift.FULL_DAY: "Celý den",
    Shift.DAY:      "Denní (8–18)",
    Shift.NIGHT:    "Noční (18–09)",
}


def _floor_label(floor: str) -> str:
    try:
        f = int(floor)
        return f"{f} PP" if f < 0 else str(f)
    except ValueError:
        return floor


def _month_calendar_weeks(year: int, month: int) -> list[list[date | None]]:
    """Returns list of weeks (each week = 7 dates or None for days outside month)."""
    cal = calendar.Calendar(firstweekday=0)  # Monday first
    weeks = []
    for week in cal.monthdatescalendar(year, month):
        weeks.append([d if d.month == month else None for d in week])
    return weeks


def _week_dates(anchor: date) -> list[date]:
    monday = anchor - timedelta(days=anchor.weekday())
    return [monday + timedelta(days=i) for i in range(5)]


def _base_ctx(request: Request, user: dict) -> dict:
    return {
        "request": request,
        "user": user,
        "czech_days": _CZECH_DAYS_SHORT,
        "shift_labels": SHIFT_LABELS,
        "shift_short": SHIFT_SHORT,
        "shifts": list(Shift),
        "floor_label": _floor_label,
    }


# ── Monthly view (default) ────────────────────────────────────────────────

@router.get("/", response_class=HTMLResponse)
@router.get("/calendar", response_class=HTMLResponse)
async def calendar_month(
    request: Request,
    month: str | None = Query(None),
    db: Session = Depends(get_db),
):
    user = get_current_user_or_none(request)
    if not user:
        return RedirectResponse("/auth/admin-login")

    today = date.today()
    try:
        anchor = date.fromisoformat(f"{month}-01") if month else today.replace(day=1)
    except ValueError:
        anchor = today.replace(day=1)

    year, mon = anchor.year, anchor.month
    prev_month = (anchor - timedelta(days=1)).replace(day=1)
    next_month = (anchor.replace(day=28) + timedelta(days=4)).replace(day=1)

    weeks = _month_calendar_weeks(year, mon)
    all_dates = [d for w in weeks for d in w if d is not None]

    spots = db.query(models.Spot).filter_by(active=True).order_by(models.Spot.floor, models.Spot.number).all()
    summary = get_month_summary(db, all_dates, user["id"], spots)

    ctx = _base_ctx(request, user)
    ctx.update({
        "weeks": weeks,
        "summary": summary,
        "month_label": f"{_CZECH_MONTHS_NOM[mon - 1]} {year}",
        "prev_month": prev_month.strftime("%Y-%m"),
        "next_month": next_month.strftime("%Y-%m"),
        "today": today,
        "csrf_token": generate_csrf_token(request),
    })
    return templates.TemplateResponse("calendar_month.html", ctx)


# ── Weekly detail view ────────────────────────────────────────────────────

@router.get("/calendar/week", response_class=HTMLResponse)
async def calendar_week(
    request: Request,
    week: str | None = Query(None),
    db: Session = Depends(get_db),
):
    user = get_current_user_or_none(request)
    if not user:
        return RedirectResponse("/auth/admin-login")

    today = date.today()
    try:
        anchor = date.fromisoformat(week) if week else today
    except ValueError:
        anchor = today

    week_dates = _week_dates(anchor)
    prev_week = (week_dates[0] - timedelta(days=7)).isoformat()
    next_week = (week_dates[0] + timedelta(days=7)).isoformat()
    back_month = week_dates[0].strftime("%Y-%m")

    spots = db.query(models.Spot).filter_by(active=True).order_by(models.Spot.floor, models.Spot.number).all()
    availability = get_week_detail(db, week_dates, user["id"], spots)

    week_label = f"{week_dates[0].day}. {_CZECH_MONTHS_GEN[week_dates[0].month - 1]}"

    ctx = _base_ctx(request, user)
    ctx.update({
        "spots": spots,
        "week_dates": week_dates,
        "availability": availability,
        "prev_week": prev_week,
        "next_week": next_week,
        "back_month": back_month,
        "week_label": week_label,
        "today": today,
        "csrf_token": generate_csrf_token(request),
        "back_url": f"/calendar?month={back_month}",
    })
    return templates.TemplateResponse("calendar.html", ctx)
