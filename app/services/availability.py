from datetime import date
from sqlalchemy.orm import Session
from app import models
from app.models.enums import Shift, SpotType, ReleaseType

# Shifts that conflict with FULL_DAY
_FULL_DAY_CONFLICTS = {Shift.DAY, Shift.NIGHT}


def _shifts_conflict(a: Shift, b: Shift) -> bool:
    if a == b:
        return True
    if Shift.FULL_DAY in (a, b):
        return True
    return False


def get_week_availability(db: Session, week_dates: list[date], current_user_id) -> dict:
    """
    Returns a nested dict: {date: {spot_id: {shift: status}}}
    status: "mine" | "taken" | "free" | "blocked"
      - mine: reserved by current user
      - taken: reserved by someone else
      - free: bookable by current user
      - blocked: assigned to someone else, not released
    """
    spots = db.query(models.Spot).filter_by(active=True).all()
    start, end = week_dates[0], week_dates[-1]

    reservations = (
        db.query(models.Reservation)
        .filter(
            models.Reservation.date >= start,
            models.Reservation.date <= end,
            models.Reservation.cancelled_at.is_(None),
        )
        .all()
    )

    releases = (
        db.query(models.Release)
        .filter(
            models.Release.date >= start,
            models.Release.date <= end,
            models.Release.retracted_at.is_(None),
        )
        .all()
    )

    # Index by (spot_id, date)
    res_index: dict[tuple, list[models.Reservation]] = {}
    for r in reservations:
        res_index.setdefault((r.spot_id, r.date), []).append(r)

    release_index: dict[tuple, list[models.Release]] = {}
    for r in releases:
        release_index.setdefault((r.spot_id, r.date), []).append(r)

    result = {}
    for d in week_dates:
        result[d] = {}
        for spot in spots:
            result[d][spot.id] = _spot_day_status(
                spot, d, current_user_id,
                res_index.get((spot.id, d), []),
                release_index.get((spot.id, d), []),
            )

    return result


def _spot_day_status(
    spot: models.Spot,
    day: date,
    current_user_id,
    reservations: list[models.Reservation],
    releases: list[models.Release],
) -> dict[Shift, str]:
    status = {}
    for shift in Shift:
        status[shift] = _shift_status(spot, shift, current_user_id, reservations, releases)
    return status


def _shift_status(
    spot: models.Spot,
    shift: Shift,
    current_user_id,
    reservations: list[models.Reservation],
    releases: list[models.Release],
) -> str:
    # Check if there's a conflicting reservation
    for res in reservations:
        if _shifts_conflict(res.shift, shift):
            if str(res.user_id) == str(current_user_id):
                return "mine"
            return "taken"

    if spot.spot_type == SpotType.SHARED:
        return "free"

    # ASSIGNED spot — check for a release that covers this shift
    for rel in releases:
        if not _shifts_conflict(rel.shift, shift):
            continue
        if rel.release_type == ReleaseType.POOL:
            return "free"
        if rel.release_type == ReleaseType.TRANSFER:
            if str(rel.transfer_to_user_id) == str(current_user_id):
                return "free"
            return "taken"

    # No release — spot is blocked unless current user is the owner
    if str(spot.assigned_user_id) == str(current_user_id):
        return "mine"  # their own spot, implicitly "held"
    return "blocked"
