from datetime import date, datetime, timezone
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from fastapi import HTTPException
from app import models
from app.models.enums import Shift, SpotType, ReleaseType
from app.services.availability import _shifts_conflict


def create_reservation(
    db: Session,
    spot_id,
    user_id,
    day: date,
    shift: Shift,
) -> models.Reservation:
    spot = db.query(models.Spot).filter_by(id=spot_id, active=True).first()
    if not spot:
        raise HTTPException(status_code=404, detail="Spot not found")

    _assert_bookable(db, spot, day, shift, user_id)

    reservation = models.Reservation(spot_id=spot_id, user_id=user_id, date=day, shift=shift)
    db.add(reservation)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Slot already taken")
    db.refresh(reservation)
    return reservation


def cancel_reservation(db: Session, reservation_id, user_id) -> models.Reservation:
    res = db.query(models.Reservation).filter_by(id=reservation_id).first()
    if not res:
        raise HTTPException(status_code=404, detail="Reservation not found")
    if str(res.user_id) != str(user_id):
        raise HTTPException(status_code=403, detail="Not your reservation")
    if res.cancelled_at:
        raise HTTPException(status_code=409, detail="Already cancelled")
    res.cancelled_at = datetime.now(timezone.utc)
    db.commit()
    return res


def create_release(
    db: Session,
    spot_id,
    owner_id,
    day: date,
    shift: Shift,
    release_type: ReleaseType,
    transfer_to_user_id=None,
) -> models.Release:
    spot = db.query(models.Spot).filter_by(id=spot_id, active=True).first()
    if not spot or spot.spot_type != SpotType.ASSIGNED:
        raise HTTPException(status_code=400, detail="Not an assigned spot")
    if str(spot.assigned_user_id) != str(owner_id):
        raise HTTPException(status_code=403, detail="Not your spot")

    release = models.Release(
        spot_id=spot_id,
        date=day,
        shift=shift,
        release_type=release_type,
        transfer_to_user_id=transfer_to_user_id,
    )
    db.add(release)
    db.commit()
    db.refresh(release)
    return release


def retract_release(db: Session, release_id, owner_id) -> models.Release:
    release = db.query(models.Release).filter_by(id=release_id).first()
    if not release:
        raise HTTPException(status_code=404, detail="Release not found")

    spot = db.query(models.Spot).filter_by(id=release.spot_id).first()
    if str(spot.assigned_user_id) != str(owner_id):
        raise HTTPException(status_code=403, detail="Not your spot")
    if release.retracted_at:
        raise HTTPException(status_code=409, detail="Already retracted")

    # Block retraction if someone already reserved this slot
    conflicting = (
        db.query(models.Reservation)
        .filter(
            models.Reservation.spot_id == release.spot_id,
            models.Reservation.date == release.date,
            models.Reservation.cancelled_at.is_(None),
        )
        .all()
    )
    for res in conflicting:
        if _shifts_conflict(res.shift, release.shift):
            raise HTTPException(status_code=409, detail="Slot already reserved by someone else")

    release.retracted_at = datetime.now(timezone.utc)
    db.commit()
    return release


def _user_has_unreleased_assigned_spot(db: Session, user_id, day: date, shift: Shift) -> models.Spot | None:
    """
    Returns the assigned spot if the user has one that is NOT released for the
    given day/shift — meaning they should not be able to book another spot.
    """
    assigned = (
        db.query(models.Spot)
        .filter_by(active=True, spot_type=SpotType.ASSIGNED)
        .filter(models.Spot.assigned_user_id == user_id)
        .first()
    )
    if not assigned:
        return None

    releases = (
        db.query(models.Release)
        .filter(
            models.Release.spot_id == assigned.id,
            models.Release.date == day,
            models.Release.retracted_at.is_(None),
        )
        .all()
    )
    # Spot is considered released if there's a POOL release covering the requested shift
    for rel in releases:
        if rel.release_type == ReleaseType.POOL and _shifts_conflict(rel.shift, shift):
            return None  # Released → user may book elsewhere

    return assigned  # Not released → block


def _assert_bookable(db: Session, spot: models.Spot, day: date, shift: Shift, user_id):
    from app.services.availability import _shift_status

    # Block reservation if user has an unreleased assigned spot (they already have parking)
    # Exception: if they're reserving their own assigned spot (shouldn't normally happen, but guard it)
    blocking_spot = _user_has_unreleased_assigned_spot(db, user_id, day, shift)
    if blocking_spot and str(blocking_spot.id) != str(spot.id):
        raise HTTPException(
            status_code=409,
            detail=(
                f"Máte přidělené místo {blocking_spot.floor}/{blocking_spot.number}, "
                f"které není uvolněno. Nejdříve ho uvolněte do sdíleného poolu."
            ),
        )

    existing_res = (
        db.query(models.Reservation)
        .filter(
            models.Reservation.spot_id == spot.id,
            models.Reservation.date == day,
            models.Reservation.cancelled_at.is_(None),
        )
        .all()
    )
    releases = (
        db.query(models.Release)
        .filter(
            models.Release.spot_id == spot.id,
            models.Release.date == day,
            models.Release.retracted_at.is_(None),
        )
        .all()
    )

    status = _shift_status(spot, shift, user_id, existing_res, releases)
    if status not in ("free",):
        raise HTTPException(status_code=409, detail=f"Slot not available (status: {status})")
