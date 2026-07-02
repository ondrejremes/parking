import calendar
from datetime import date
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.enums import Shift, SpotType
from app.services.auth import get_current_user, generate_csrf_token
from app import models

router = APIRouter(prefix="/reporting")
templates = Jinja2Templates(directory="app/templates")

_CZECH_MONTHS_NOM = [
    'Leden', 'Únor', 'Březen', 'Duben', 'Květen', 'Červen',
    'Červenec', 'Srpen', 'Září', 'Říjen', 'Listopad', 'Prosinec',
]


def _require_reports(request: Request):
    user = get_current_user(request)
    if not user.get("is_admin") and not user.get("can_view_reports"):
        raise HTTPException(status_code=403, detail="Nemáte oprávnění zobrazit reporting")
    return user


def _working_days(year: int, month: int) -> list[date]:
    """Returns list of Mon-Fri dates in the given month."""
    cal = calendar.Calendar()
    return [
        d for d in cal.itermonthdates(year, month)
        if d.month == month and d.weekday() < 5
    ]


@router.get("/", response_class=HTMLResponse)
async def report_month(
    request: Request,
    month: str | None = Query(None),
    db: Session = Depends(get_db),
):
    _require_reports(request)

    today = date.today()
    try:
        anchor = date.fromisoformat(f"{month}-01") if month else today.replace(day=1)
    except ValueError:
        anchor = today.replace(day=1)

    year, mon = anchor.year, anchor.month
    prev_month = (anchor.replace(day=1).__class__(year if mon > 1 else year - 1,
                  mon - 1 if mon > 1 else 12, 1)).strftime("%Y-%m")
    next_anchor = anchor.replace(day=28) + __import__('datetime').timedelta(days=4)
    next_month = next_anchor.replace(day=1).strftime("%Y-%m")
    month_label = f"{_CZECH_MONTHS_NOM[mon - 1]} {year}"

    working = _working_days(year, mon)
    start, end = working[0], working[-1]
    total_working = len(working)

    spots = db.query(models.Spot).filter_by(active=True).order_by(
        models.Spot.floor, models.Spot.number
    ).all()

    # All reservations in range
    reservations = (
        db.query(models.Reservation)
        .filter(
            models.Reservation.date >= start,
            models.Reservation.date <= end,
            models.Reservation.cancelled_at.is_(None),
        )
        .all()
    )
    # All guest parkings in range
    guest_parkings = (
        db.query(models.GuestParking)
        .filter(
            models.GuestParking.date >= start,
            models.GuestParking.date <= end,
            models.GuestParking.cancelled_at.is_(None),
        )
        .all()
    )

    # Build per-spot stats
    from app.routers.calendar import _floor_label  # reuse helper
    spot_stats = []
    total_slots = total_working * 3  # 3 shifts per working day

    for spot in spots:
        spot_res = [r for r in reservations if r.spot_id == spot.id]
        spot_guests = [g for g in guest_parkings if g.spot_id == spot.id]

        booked_days: set[date] = set()
        for r in spot_res:
            booked_days.add(r.date)
        for g in spot_guests:
            booked_days.add(g.date)

        # Count reserved slots (each reservation = 1 slot)
        reserved_slots = len(spot_res) + len(spot_guests)
        utilization = round(reserved_slots / total_slots * 100, 1) if total_slots else 0

        # Day-level occupancy (at least one booking on that day)
        day_occupancy = round(len(booked_days) / total_working * 100, 1) if total_working else 0

        spot_stats.append({
            "spot": spot,
            "label": f"{_floor_label(spot.floor)} / {spot.number}",
            "is_assigned": spot.spot_type == SpotType.ASSIGNED,
            "assigned_to": spot.assigned_user.display_name if spot.assigned_user else None,
            "reserved_slots": reserved_slots,
            "booked_days": len(booked_days),
            "total_working": total_working,
            "utilization": utilization,
            "day_occupancy": day_occupancy,
            "reservations": [r for r in spot_res],
            "guest_count": len(spot_guests),
        })

    # Overall stats
    total_reserved = sum(s["reserved_slots"] for s in spot_stats)
    total_possible = total_slots * len(spots)
    overall_utilization = round(total_reserved / total_possible * 100, 1) if total_possible else 0

    return templates.TemplateResponse("reporting/utilization.html", {
        "request": request,
        "user": _require_reports(request),
        "month_label": month_label,
        "prev_month": prev_month,
        "next_month": next_month,
        "spot_stats": spot_stats,
        "total_working": total_working,
        "overall_utilization": overall_utilization,
        "back_url": "/calendar",
        "csrf_token": generate_csrf_token(request),
    })
