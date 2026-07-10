from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from datetime import date
from app.database import get_db
from app import models
from app.services.auth import get_current_user

templates = Jinja2Templates(directory="app/templates")

router = APIRouter(prefix="/occupancy", tags=["occupancy"])


@router.get("/", response_class=HTMLResponse)
async def view_occupancy(
    request: Request,
    db: Session = Depends(get_db),
):
    """View current occupancy of all parking spots (role-based visibility)."""
    user = get_current_user(request)
    if not user:
        raise HTTPException(status_code=403, detail="Unauthorized")

    # Only admin, spot manager, or reporting viewer can see occupancy
    if not (user.get("is_admin") or user.get("can_manage_spots") or user.get("can_view_reports")):
        raise HTTPException(status_code=403, detail="Nemáte oprávnění zobrazit obsazení")

    today = date.today()

    spots = db.query(models.Spot).filter_by(active=True).order_by(models.Spot.floor, models.Spot.number).all()

    def _floor_label(floor: str) -> str:
        try:
            f = int(floor)
            return f"{f} PP" if f < 0 else str(f)
        except ValueError:
            return floor

    occupancy_data = []
    for spot in spots:
        # Find current reservations (today or in the future)
        active_reservations = (
            db.query(models.Reservation)
            .filter(
                models.Reservation.spot_id == spot.id,
                models.Reservation.date >= today,
                models.Reservation.cancelled_at.is_(None),
            )
            .order_by(models.Reservation.date)
            .all()
        )

        # Find current releases (today or in the future)
        active_releases = (
            db.query(models.Release)
            .filter(
                models.Release.spot_id == spot.id,
                models.Release.date >= today,
                models.Release.retracted_at.is_(None),
            )
            .order_by(models.Release.date)
            .all()
        )

        # Find current guest parkings
        active_guests = (
            db.query(models.GuestParking)
            .filter(
                models.GuestParking.spot_id == spot.id,
                models.GuestParking.date >= today,
                models.GuestParking.cancelled_at.is_(None),
            )
            .order_by(models.GuestParking.date)
            .all()
        )

        occupancy_data.append({
            "spot": spot,
            "label": f"{_floor_label(spot.floor)} / {spot.number}",
            "reservations": active_reservations,
            "releases": active_releases,
            "guests": active_guests,
        })

    return templates.TemplateResponse("occupancy/current.html", {
        "request": request,
        "user": user,
        "occupancy": occupancy_data,
        "today": today,
    })
