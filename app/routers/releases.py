from datetime import date
from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.enums import Shift, ReleaseType
from app.services.auth import get_current_user, validate_csrf
from app.services.booking import create_release, retract_release

router = APIRouter(prefix="/releases")


@router.post("/")
async def release(
    request: Request,
    spot_id: str = Form(...),
    day: date = Form(...),
    shift: Shift = Form(...),
    release_type: ReleaseType = Form(...),
    transfer_to_user_id: str | None = Form(None),
    csrf_token: str = Form(...),
    db: Session = Depends(get_db),
):
    validate_csrf(request, csrf_token)
    user = get_current_user(request)
    create_release(
        db,
        spot_id=spot_id,
        owner_id=user["id"],
        day=day,
        shift=shift,
        release_type=release_type,
        transfer_to_user_id=transfer_to_user_id or None,
    )
    return RedirectResponse(f"/calendar?month={day.strftime('%Y-%m')}", status_code=303)


@router.post("/{release_id}/retract")
async def retract(
    release_id: str,
    request: Request,
    csrf_token: str = Form(...),
    db: Session = Depends(get_db),
):
    validate_csrf(request, csrf_token)
    user = get_current_user(request)
    rel = retract_release(db, release_id=release_id, owner_id=user["id"])
    return RedirectResponse(f"/calendar?month={rel.date.strftime('%Y-%m')}", status_code=303)
