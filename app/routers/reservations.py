from datetime import date
from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.enums import Shift
from app.services.auth import get_current_user, validate_csrf
from app.services.booking import create_reservation, cancel_reservation
from app.services import email as email_service
from app import models

router = APIRouter(prefix="/reservations")


@router.post("/")
async def reserve(
    request: Request,
    spot_id: str = Form(...),
    day: date = Form(...),
    shift: Shift = Form(...),
    csrf_token: str = Form(...),
    db: Session = Depends(get_db),
):
    validate_csrf(request, csrf_token)
    user = get_current_user(request)
    reservation = create_reservation(db, spot_id=spot_id, user_id=user["id"], day=day, shift=shift)

    spot = db.query(models.Spot).filter_by(id=spot_id).first()
    email_service.send_confirmation(user["email"], spot.floor, spot.number, day, shift)

    return RedirectResponse(f"/calendar?month={day.strftime('%Y-%m')}", status_code=303)


@router.post("/{reservation_id}/cancel")
async def cancel(
    reservation_id: str,
    request: Request,
    csrf_token: str = Form(...),
    db: Session = Depends(get_db),
):
    validate_csrf(request, csrf_token)
    user = get_current_user(request)
    cancel_reservation(db, reservation_id=reservation_id, user_id=user["id"])
    return RedirectResponse("/calendar", status_code=303)
