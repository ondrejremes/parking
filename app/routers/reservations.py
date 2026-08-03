from datetime import date
from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
import asyncio

from app.database import get_db
from app.models.enums import Shift
from app.services.auth import get_current_user, validate_csrf
from app.services.booking import create_reservation, cancel_reservation
from app.services import email_notifications
from app.models.enums import SpotType
from app import models

router = APIRouter(prefix="/reservations")


@router.post("/")
def reserve(
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

    # Send confirmation email synchronously (blocking) to ensure delivery
    spot_dict = {
        "floor": spot.floor,
        "number": spot.number,
        "spot_type": spot.spot_type.value if spot.spot_type else "Sdílené"
    }

    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"📧 Attempting to send confirmation email to {user['email']}")

    # Send appropriate confirmation email based on spot type
    # Using asyncio.run() to run async email functions synchronously in the request context
    try:
        if spot.spot_type == SpotType.ASSIGNED:
            asyncio.run(
                email_notifications.send_assigned_spot_reservation_confirmation(
                    user["email"],
                    user.get("display_name", ""),
                    spot_dict,
                    day.strftime("%d.%m.%Y"),
                    shift.value
                )
            )
        else:
            asyncio.run(
                email_notifications.send_reservation_confirmation(
                    user["email"],
                    user.get("display_name", ""),
                    spot_dict,
                    day.strftime("%d.%m.%Y"),
                    shift.value
                )
            )
        logger.info(f"✅ Confirmation email successfully sent to {user['email']}")
    except Exception as e:
        logger.error(f"❌ Failed to send confirmation email to {user['email']}: {e}", exc_info=True)

    return RedirectResponse(f"/calendar?month={day.strftime('%Y-%m')}", status_code=303)


@router.post("/{reservation_id}/cancel")
def cancel(
    reservation_id: str,
    request: Request,
    csrf_token: str = Form(...),
    db: Session = Depends(get_db),
):
    validate_csrf(request, csrf_token)
    user = get_current_user(request)

    # Get reservation details before cancellation
    reservation = db.query(models.Reservation).filter_by(id=reservation_id).first()
    if reservation:
        spot = db.query(models.Spot).filter_by(id=reservation.spot_id).first()

    cancel_reservation(db, reservation_id=reservation_id, user_id=user["id"])

    # Send cancellation email synchronously (blocking) to ensure delivery
    if reservation and spot:
        spot_dict = {
            "floor": spot.floor,
            "number": spot.number,
            "spot_type": spot.spot_type.value if spot.spot_type else "Sdílené"
        }
        try:
            asyncio.run(
                email_notifications.send_reservation_cancellation(
                    user["email"],
                    user.get("display_name", ""),
                    spot_dict,
                    reservation.date.strftime("%d.%m.%Y"),
                    reservation.shift.value
                )
            )
            logger.info(f"✅ Cancellation email successfully sent to {user['email']}")
        except Exception as e:
            logger.error(f"❌ Failed to send cancellation email to {user['email']}: {e}", exc_info=True)

    return RedirectResponse("/calendar", status_code=303)
