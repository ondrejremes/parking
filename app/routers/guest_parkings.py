from datetime import date, datetime, time, timezone
from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.auth import get_current_user, validate_csrf
from app.services.availability import get_week_availability
from app import models

router = APIRouter(prefix="/guest-parkings")


def _spot_is_free_for_day(db: Session, spot_id, day: date, user_id: str) -> bool:
    """Check that the spot has at least one free shift available on the given day."""
    spots = db.query(models.Spot).filter_by(id=spot_id, active=True).all()
    if not spots:
        return False
    avail = get_week_availability(db, [day], user_id)
    shifts = avail.get(day, {}).get(spots[0].id, {})
    return any(status == "free" for status in shifts.values())


@router.post("/")
async def create(
    request: Request,
    spot_id: str = Form(...),
    day: date = Form(...),
    time_from: str = Form(...),
    time_to: str = Form(...),
    guest_name: str = Form(...),
    guest_plate: str = Form(""),
    note: str = Form(""),
    contact: str = Form(""),
    csrf_token: str = Form(...),
    db: Session = Depends(get_db),
):
    validate_csrf(request, csrf_token)
    user = get_current_user(request)
    back = f"/calendar?month={day.strftime('%Y-%m')}"

    if not user.get("can_manage_guests") and not user.get("is_admin"):
        from fastapi import HTTPException
        raise HTTPException(status_code=403, detail="Nemáte oprávnění rezervovat pro hosty")

    spot = db.query(models.Spot).filter_by(id=spot_id, active=True).first()
    if not spot:
        return RedirectResponse(back, status_code=303)

    t_from = time.fromisoformat(time_from)
    t_to = time.fromisoformat(time_to)
    if t_to <= t_from:
        return RedirectResponse(back, status_code=303)

    # Check overlap with existing guest parkings on the same spot+day
    existing = (
        db.query(models.GuestParking)
        .filter(
            models.GuestParking.spot_id == spot_id,
            models.GuestParking.date == day,
            models.GuestParking.cancelled_at.is_(None),
        )
        .all()
    )
    for eg in existing:
        if eg.time_from < t_to and eg.time_to > t_from:
            # Overlapping guest parking already exists — redirect without creating
            return RedirectResponse(back, status_code=303)

    gp = models.GuestParking(
        spot_id=spot_id,
        created_by_user_id=user["id"],
        date=day,
        time_from=t_from,
        time_to=t_to,
        guest_name=guest_name.strip(),
        guest_plate=guest_plate.strip() or None,
        note=note.strip() or None,
        contact=contact.strip() or None,
    )
    db.add(gp)
    db.commit()
    return RedirectResponse(back, status_code=303)


@router.post("/{gp_id}/cancel")
async def cancel(
    gp_id: str,
    request: Request,
    csrf_token: str = Form(...),
    db: Session = Depends(get_db),
):
    validate_csrf(request, csrf_token)
    user = get_current_user(request)

    gp = db.query(models.GuestParking).filter_by(id=gp_id).first()
    if not gp or str(gp.created_by_user_id) != str(user["id"]) or gp.cancelled_at:
        return RedirectResponse("/calendar", status_code=303)

    gp.cancelled_at = datetime.now(timezone.utc)
    db.commit()
    return RedirectResponse(f"/calendar?month={gp.date.strftime('%Y-%m')}", status_code=303)
