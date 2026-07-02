from datetime import date, datetime, time, timezone
from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.enums import SpotType
from app.services.auth import get_current_user, validate_csrf
from app import models

router = APIRouter(prefix="/guest-parkings")


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

    spot = db.query(models.Spot).filter_by(id=spot_id, active=True).first()
    if not spot or spot.spot_type != SpotType.ASSIGNED:
        return RedirectResponse(f"/calendar?month={day.strftime('%Y-%m')}", status_code=303)
    if str(spot.assigned_user_id) != str(user["id"]):
        return RedirectResponse(f"/calendar?month={day.strftime('%Y-%m')}", status_code=303)

    gp = models.GuestParking(
        spot_id=spot_id,
        created_by_user_id=user["id"],
        date=day,
        time_from=time.fromisoformat(time_from),
        time_to=time.fromisoformat(time_to),
        guest_name=guest_name.strip(),
        guest_plate=guest_plate.strip() or None,
        note=note.strip() or None,
        contact=contact.strip() or None,
    )
    db.add(gp)
    db.commit()
    return RedirectResponse(f"/calendar?month={day.strftime('%Y-%m')}", status_code=303)


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
    if gp and str(gp.created_by_user_id) == str(user["id"]) and not gp.cancelled_at:
        gp.cancelled_at = datetime.now(timezone.utc)
        db.commit()

    return RedirectResponse(f"/calendar?month={gp.date.strftime('%Y-%m')}", status_code=303)
