from datetime import date, time
from sqlalchemy.orm import Session
from app import models
from app.models.enums import Shift, SpotType, ReleaseType
from typing import Any

# Shift time ranges for guest-parking conflict detection
_SHIFT_RANGES: dict[Shift, list[tuple[time, time]]] = {
    Shift.FULL_DAY: [(time(0, 0), time(23, 59))],
    Shift.DAY:      [(time(8, 0),  time(18, 0))],
    Shift.NIGHT:    [(time(18, 0), time(23, 59)), (time(0, 0), time(8, 0))],
}


def _guest_blocks_shift(time_from: time, time_to: time, shift: Shift) -> bool:
    """True if guest parking [time_from, time_to) overlaps with the shift's time range."""
    for r_from, r_to in _SHIFT_RANGES.get(shift, []):
        if time_from < r_to and time_to > r_from:
            return True
    return False

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

    # User's existing reservations (to block duplicate bookings on other spots)
    user_reservations_all = (
        db.query(models.Reservation)
        .filter(
            models.Reservation.user_id == current_user_id,
            models.Reservation.date >= start,
            models.Reservation.date <= end,
            models.Reservation.cancelled_at.is_(None),
        )
        .all()
    )
    # Index: date → set of shifts already booked by user (on any spot)
    user_booked: dict[date, set] = {}
    for r in user_reservations_all:
        user_booked.setdefault(r.date, set()).add(r.shift)

    # Determine if the current user has an assigned spot and which days it's unreleased
    # If assigned spot is not released for a day, user cannot book other spots that day
    user_assigned_spot = (
        db.query(models.Spot)
        .filter_by(active=True, spot_type=SpotType.ASSIGNED)
        .filter(models.Spot.assigned_user_id == current_user_id)
        .first()
    )
    # Build set of (date, shift) where user's assigned spot IS released to pool
    user_released: set[tuple] = set()
    if user_assigned_spot:
        user_releases = (
            db.query(models.Release)
            .filter(
                models.Release.spot_id == user_assigned_spot.id,
                models.Release.date >= start,
                models.Release.date <= end,
                models.Release.release_type == ReleaseType.POOL,
                models.Release.retracted_at.is_(None),
            )
            .all()
        )
        for rel in user_releases:
            for shift in Shift:
                if _shifts_conflict(rel.shift, shift):
                    user_released.add((rel.date, shift))

    # Guest parkings — only block shifts whose time range overlaps with the guest's time
    guest_parkings = (
        db.query(models.GuestParking)
        .filter(
            models.GuestParking.date >= start,
            models.GuestParking.date <= end,
            models.GuestParking.cancelled_at.is_(None),
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

    # Index: (spot_id, date) → list of guest parkings
    guest_index: dict[tuple, list] = {}
    for gp in guest_parkings:
        guest_index.setdefault((gp.spot_id, gp.date), []).append(gp)

    result = {}
    for d in week_dates:
        result[d] = {}
        for spot in spots:
            day_status = _spot_day_status(
                spot, d, current_user_id,
                res_index.get((spot.id, d), []),
                release_index.get((spot.id, d), []),
            )

            # Apply guest parking time-based blocking per shift
            day_guests = guest_index.get((spot.id, d), [])
            if day_guests:
                for shift in Shift:
                    if day_status[shift] == "free":
                        if any(_guest_blocks_shift(gp.time_from, gp.time_to, shift)
                               for gp in day_guests):
                            day_status[shift] = "taken"

            # If user has an unreleased assigned spot, mark free slots on OTHER spots as blocked
            if user_assigned_spot and str(spot.id) != str(user_assigned_spot.id):
                for shift in Shift:
                    if day_status[shift] == "free" and (d, shift) not in user_released:
                        day_status[shift] = "blocked"

            # If user already has a reservation on another spot for this day,
            # mark conflicting shifts as blocked
            booked_shifts = user_booked.get(d, set())
            if booked_shifts:
                for shift in Shift:
                    if day_status[shift] == "free":
                        for booked in booked_shifts:
                            if _shifts_conflict(booked, shift):
                                day_status[shift] = "blocked"
                                break

            result[d][spot.id] = day_status

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


def get_week_detail(db: Session, week_dates: list[date], current_user_id, spots: list) -> dict:
    """
    Like get_week_availability but returns richer per-slot dicts for the weekly view:
    {date: {spot_id: {shift: {"status": str, "reservation_id": UUID|None, "is_assigned_held": bool}}}}
    """
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

    res_index: dict[tuple, list] = {}
    for r in reservations:
        res_index.setdefault((r.spot_id, r.date), []).append(r)

    release_index: dict[tuple, list] = {}
    for r in releases:
        release_index.setdefault((r.spot_id, r.date), []).append(r)

    result: dict = {}
    for d in week_dates:
        result[d] = {}
        for spot in spots:
            day_res   = res_index.get((spot.id, d), [])
            day_rel   = release_index.get((spot.id, d), [])
            slot_detail: dict[Shift, dict] = {}
            for shift in Shift:
                status = _shift_status(spot, shift, current_user_id, day_res, day_rel)
                res_id = None
                is_assigned_held = False
                if status == "mine":
                    # Find the actual reservation (if any)
                    for res in day_res:
                        if _shifts_conflict(res.shift, shift) and str(res.user_id) == str(current_user_id):
                            res_id = res.id
                            break
                    if res_id is None:
                        # "mine" without reservation = implicitly held assigned spot
                        is_assigned_held = True
                slot_detail[shift] = {
                    "status": status,
                    "reservation_id": res_id,
                    "is_assigned_held": is_assigned_held,
                    "spot_id": spot.id,
                }
            result[d][spot.id] = slot_detail
    return result


def get_month_summary(
    db: Session,
    dates: list[date],
    user_id: Any,
    spots: list[models.Spot],
) -> dict[date, dict]:
    """
    Returns per-day summary for monthly calendar.
    {date: {
        'reservations': [(spot, shift), ...],     # actual DB reservations by user
        'assigned_held': [spot, ...],             # user's assigned spots held without explicit reservation
        'free_spots': [spot, ...],                # spots with at least one free shift
    }}
    """
    if not dates:
        return {}

    import uuid as _uuid
    try:
        _uuid.UUID(str(user_id))
    except (ValueError, AttributeError):
        # Non-UUID user_id (e.g. stale session) — return empty summary
        return {d: {"reservations": [], "assigned_held": [], "free_spots": []} for d in dates}

    start, end = min(dates), max(dates)
    spot_map = {spot.id: spot for spot in spots}

    # User's actual reservations in range
    user_reservations = (
        db.query(models.Reservation)
        .filter(
            models.Reservation.user_id == user_id,
            models.Reservation.date >= start,
            models.Reservation.date <= end,
            models.Reservation.cancelled_at.is_(None),
        )
        .all()
    )
    # Index: date → list of (spot, shift, reservation_id)
    res_by_date: dict[date, list] = {}
    for r in user_reservations:
        spot = spot_map.get(r.spot_id)
        if spot:
            res_by_date.setdefault(r.date, []).append((spot, r.shift, r.id))

    # Spots assigned to this user (held implicitly — no reservation needed)
    assigned_spots = [s for s in spots if str(s.assigned_user_id) == str(user_id)]

    # Active releases by the owner (days when they released their spot)
    released = set()
    if assigned_spots:
        releases = (
            db.query(models.Release)
            .filter(
                models.Release.spot_id.in_([s.id for s in assigned_spots]),
                models.Release.date >= start,
                models.Release.date <= end,
                models.Release.retracted_at.is_(None),
            )
            .all()
        )
        # A spot is fully released on a day if FULL_DAY or both DAY+NIGHT released
        release_shifts: dict[tuple, set] = {}
        for rel in releases:
            key = (rel.spot_id, rel.date)
            release_shifts.setdefault(key, set()).add(rel.shift)

        for spot in assigned_spots:
            for d in dates:
                key = (spot.id, d)
                shifts_released = release_shifts.get(key, set())
                fully_released = (
                    Shift.FULL_DAY in shifts_released
                    or (Shift.DAY in shifts_released and Shift.NIGHT in shifts_released)
                )
                if not fully_released:
                    released_tuple = (spot.id, d)
                    # not released = held by owner
                else:
                    released.add((spot.id, d))

    # Free spots per day (from full availability — only for future dates, performance)
    future_dates = [d for d in dates if d >= date.today()]
    full_avail = get_week_availability(db, future_dates, user_id) if future_dates else {}

    summary: dict[date, dict] = {}
    # Guest parkings created by this user in range
    guest_parkings_list = (
        db.query(models.GuestParking)
        .filter(
            models.GuestParking.created_by_user_id == user_id,
            models.GuestParking.date >= start,
            models.GuestParking.date <= end,
            models.GuestParking.cancelled_at.is_(None),
        )
        .all()
    )
    guest_by_date: dict[date, list] = {}
    for gp in guest_parkings_list:
        guest_by_date.setdefault(gp.date, []).append(gp)

    for d in dates:
        # Actual reservations: (spot, shift, res_id)
        my_res = res_by_date.get(d, [])

        # Assigned spots held implicitly: (spot, spot_id)
        reserved_spot_ids = {spot.id for spot, _, _ in my_res}
        held = [
            (s, s.id) for s in assigned_spots
            if (s.id, d) not in released and s.id not in reserved_spot_ids
        ]

        # Free options: (spot, shift) pairs available to book, grouped for dialog
        free_options: list = []
        free_spots: list = []
        if d in full_avail:
            seen_spots: set = set()
            for shift in Shift:
                for spot_id, shifts in full_avail[d].items():
                    if shifts.get(shift) == "free":
                        spot = spot_map[spot_id]
                        free_options.append((spot, shift))
                        seen_spots.add(spot_id)
            free_spots = [spot_map[sid] for sid in seen_spots]

        summary[d] = {
            "reservations": my_res,
            "assigned_held": held,
            "free_spots": free_spots,
            "free_options": free_options,
            "guest_parkings": guest_by_date.get(d, []),
        }
    return summary
