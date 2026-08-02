from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
import uuid

from app.database import get_db
from app.models.enums import SpotType
from app.services.auth import require_admin, get_current_user, generate_csrf_token, validate_csrf
from app.services.entra_id import get_entra_users
from app.services.audit import log_action
from app import models

router = APIRouter(prefix="/admin")
templates = Jinja2Templates(directory="app/templates")


def _require_spots_manager(request: Request):
    user = get_current_user(request)
    if not user.get("is_admin") and not user.get("can_manage_spots"):
        raise HTTPException(status_code=403, detail="Nemáte oprávnění spravovat parkovací místa")
    return user


# ── Spots ──────────────────────────────────────────────────────────────────

@router.get("/spots", response_class=HTMLResponse)
async def spots(request: Request, db: Session = Depends(get_db)):
    _require_spots_manager(request)
    all_spots = db.query(models.Spot).order_by(models.Spot.floor, models.Spot.number).all()
    all_users = db.query(models.User).order_by(models.User.display_name).all()
    return templates.TemplateResponse("admin/spots.html", {
        "request": request,
        "user": get_current_user(request),
        "spots": all_spots,
        "users": all_users,
        "csrf_token": generate_csrf_token(request),
        "back_url": "/calendar",
    })


@router.post("/spots")
async def create_spot(
    request: Request,
    floor: str = Form(...),
    number: str = Form(...),
    spot_type: SpotType = Form(...),
    assigned_user_id: str | None = Form(None),
    csrf_token: str = Form(...),
    db: Session = Depends(get_db),
):
    validate_csrf(request, csrf_token)
    current_user = _require_spots_manager(request)
    spot = models.Spot(
        floor=floor,
        number=number,
        spot_type=spot_type,
        assigned_user_id=assigned_user_id or None,
    )
    db.add(spot)
    db.commit()

    log_action(
        db=db,
        admin_user_id=str(current_user["id"]),
        action="spot_created",
        target_resource="spot",
        new_value={"floor": floor, "number": number, "spot_type": spot_type.value, "assigned_user_id": assigned_user_id},
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    return RedirectResponse("/admin/spots", status_code=303)


@router.post("/spots/{spot_id}/assign")
async def assign_spot(
    spot_id: str,
    request: Request,
    user_id: str | None = Form(None),
    csrf_token: str = Form(...),
    db: Session = Depends(get_db),
):
    validate_csrf(request, csrf_token)
    current_user = _require_spots_manager(request)
    spot = db.query(models.Spot).filter_by(id=spot_id).first()
    old_assigned = spot.assigned_user_id
    spot.assigned_user_id = user_id or None
    spot.spot_type = SpotType.ASSIGNED if user_id else SpotType.SHARED
    db.commit()

    log_action(
        db=db,
        admin_user_id=str(current_user["id"]),
        action="spot_assigned",
        target_resource="spot",
        old_value={"assigned_user_id": str(old_assigned) if old_assigned else None},
        new_value={"assigned_user_id": user_id, "spot_type": spot.spot_type.value},
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    return RedirectResponse("/admin/spots", status_code=303)


@router.post("/spots/{spot_id}/edit")
async def edit_spot(
    spot_id: str,
    request: Request,
    floor: str = Form(...),
    number: str = Form(...),
    spot_type: SpotType = Form(...),
    assigned_user_id: str | None = Form(None),
    active: str = Form(None),
    csrf_token: str = Form(...),
    db: Session = Depends(get_db),
):
    validate_csrf(request, csrf_token)
    current_user = _require_spots_manager(request)
    if not floor or not floor.replace("-", "").replace("P", "").isalnum():
        raise HTTPException(status_code=400, detail="Neplatné patro")
    if not number or not number.isalnum():
        raise HTTPException(status_code=400, detail="Neplatné číslo místa")
    spot = db.query(models.Spot).filter_by(id=spot_id).first()
    old_values = {
        "floor": spot.floor,
        "number": spot.number,
        "spot_type": spot.spot_type.value,
        "assigned_user_id": str(spot.assigned_user_id) if spot.assigned_user_id else None,
        "active": spot.active,
    }
    spot.floor = floor
    spot.number = number
    spot.spot_type = spot_type
    spot.assigned_user_id = assigned_user_id or None
    spot.active = active == "on"
    db.commit()

    log_action(
        db=db,
        admin_user_id=str(current_user["id"]),
        action="spot_edited",
        target_resource="spot",
        old_value=old_values,
        new_value={
            "floor": floor,
            "number": number,
            "spot_type": spot_type.value,
            "assigned_user_id": assigned_user_id,
            "active": spot.active,
        },
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    return RedirectResponse("/admin/spots", status_code=303)


@router.post("/spots/{spot_id}/deactivate")
async def deactivate_spot(
    spot_id: str,
    request: Request,
    csrf_token: str = Form(...),
    db: Session = Depends(get_db),
):
    validate_csrf(request, csrf_token)
    current_user = _require_spots_manager(request)
    spot = db.query(models.Spot).filter_by(id=spot_id).first()
    spot.active = False
    db.commit()

    log_action(
        db=db,
        admin_user_id=str(current_user["id"]),
        action="spot_deactivated",
        target_resource="spot",
        old_value={"active": True},
        new_value={"active": False},
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    return RedirectResponse("/admin/spots", status_code=303)


# ── Users ──────────────────────────────────────────────────────────────────

@router.get("/users", response_class=HTMLResponse)
async def users(request: Request, db: Session = Depends(get_db)):
    require_admin(request)
    all_users = db.query(models.User).order_by(models.User.display_name).all()
    return templates.TemplateResponse("admin/users.html", {
        "request": request,
        "user": get_current_user(request),
        "users": all_users,
        "csrf_token": generate_csrf_token(request),
        "back_url": "/calendar",
    })


@router.post("/users/{user_id}/toggle-admin")
async def toggle_admin(
    user_id: str,
    request: Request,
    csrf_token: str = Form(...),
    db: Session = Depends(get_db),
):
    validate_csrf(request, csrf_token)
    current_user = require_admin(request)
    user = db.query(models.User).filter_by(id=user_id).first()
    old_admin = user.is_admin
    user.is_admin = not user.is_admin
    db.commit()

    log_action(
        db=db,
        admin_user_id=str(current_user["id"]),
        action="user_admin_toggled",
        target_user_id=str(user.id),
        target_resource="user",
        old_value={"is_admin": old_admin},
        new_value={"is_admin": user.is_admin},
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    return RedirectResponse("/admin/users", status_code=303)


@router.post("/users/{user_id}/toggle-guests")
async def toggle_guests(
    user_id: str,
    request: Request,
    csrf_token: str = Form(...),
    db: Session = Depends(get_db),
):
    validate_csrf(request, csrf_token)
    current_user = require_admin(request)
    user = db.query(models.User).filter_by(id=user_id).first()
    old_guests = user.can_manage_guests
    user.can_manage_guests = not user.can_manage_guests
    db.commit()

    log_action(
        db=db,
        admin_user_id=str(current_user["id"]),
        action="user_guests_toggled",
        target_user_id=str(user.id),
        target_resource="user",
        old_value={"can_manage_guests": old_guests},
        new_value={"can_manage_guests": user.can_manage_guests},
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    return RedirectResponse("/admin/users", status_code=303)


@router.post("/users/{user_id}/toggle-reports")
async def toggle_reports(
    user_id: str,
    request: Request,
    csrf_token: str = Form(...),
    db: Session = Depends(get_db),
):
    validate_csrf(request, csrf_token)
    current_user = require_admin(request)
    user = db.query(models.User).filter_by(id=user_id).first()
    old_reports = user.can_view_reports
    user.can_view_reports = not user.can_view_reports
    db.commit()

    log_action(
        db=db,
        admin_user_id=str(current_user["id"]),
        action="user_reports_toggled",
        target_user_id=str(user.id),
        target_resource="user",
        old_value={"can_view_reports": old_reports},
        new_value={"can_view_reports": user.can_view_reports},
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    return RedirectResponse("/admin/users", status_code=303)


@router.post("/users/{user_id}/toggle-spots")
async def toggle_spots(
    user_id: str,
    request: Request,
    csrf_token: str = Form(...),
    db: Session = Depends(get_db),
):
    validate_csrf(request, csrf_token)
    current_user = require_admin(request)
    user = db.query(models.User).filter_by(id=user_id).first()
    old_spots = user.can_manage_spots
    user.can_manage_spots = not user.can_manage_spots
    db.commit()

    log_action(
        db=db,
        admin_user_id=str(current_user["id"]),
        action="user_spots_toggled",
        target_user_id=str(user.id),
        target_resource="user",
        old_value={"can_manage_spots": old_spots},
        new_value={"can_manage_spots": user.can_manage_spots},
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    return RedirectResponse("/admin/users", status_code=303)


@router.post("/users/{user_id}/toggle-active")
async def toggle_active(
    user_id: str,
    request: Request,
    csrf_token: str = Form(...),
    db: Session = Depends(get_db),
):
    validate_csrf(request, csrf_token)
    current_user = require_admin(request)
    target_user = db.query(models.User).filter_by(id=user_id).first()

    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")

    # Prevent user from deactivating themselves
    if str(current_user["id"]) == str(user_id):
        raise HTTPException(status_code=400, detail="Nelze deaktivovat sebe sama")

    old_active = target_user.active
    target_user.active = not target_user.active
    db.commit()

    log_action(
        db=db,
        admin_user_id=str(current_user["id"]),
        action="user_active_toggled",
        target_user_id=str(target_user.id),
        target_resource="user",
        old_value={"active": old_active},
        new_value={"active": target_user.active},
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    return RedirectResponse("/admin/users", status_code=303)


# ── Entra ID Sync ──────────────────────────────────────────────────────────

@router.get("/users/entra-sync")
async def sync_entra_users(
    request: Request,
    db: Session = Depends(get_db),
):
    require_admin(request)
    entra_users = await get_entra_users()

    # Check which users are already registered
    registered = {}
    for user in db.query(models.User).filter(models.User.azure_oid != None).all():
        registered[user.azure_oid] = user

    new_users = []
    for eu in entra_users:
        if eu["id"] not in registered:
            new_users.append(eu)

    return JSONResponse({
        "new_users": new_users,
        "total_entra_users": len(entra_users),
        "registered_users": len(registered),
    })


@router.post("/users/entra-register")
async def register_entra_user(
    request: Request,
    azure_oid: str = Form(...),
    display_name: str = Form(...),
    email: str = Form(...),
    csrf_token: str = Form(...),
    db: Session = Depends(get_db),
):
    validate_csrf(request, csrf_token)
    current_user = require_admin(request)

    # Check if already exists
    existing = db.query(models.User).filter_by(azure_oid=azure_oid).first()
    if existing:
        return RedirectResponse("/admin/users", status_code=303)

    # Create new user
    user = models.User(
        id=str(uuid.uuid4()),
        azure_oid=azure_oid,
        email=email,
        display_name=display_name,
        is_admin=False,
    )
    db.add(user)
    db.commit()

    log_action(
        db=db,
        admin_user_id=str(current_user["id"]),
        action="user_created",
        target_user_id=str(user.id),
        target_resource="user",
        new_value={"email": email, "display_name": display_name},
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )

    return RedirectResponse("/admin/users", status_code=303)


@router.post("/users/{user_id}/toggle-active")
async def toggle_active(
    user_id: str,
    request: Request,
    csrf_token: str = Form(...),
    db: Session = Depends(get_db),
):
    validate_csrf(request, csrf_token)
    current_user = require_admin(request)
    user = db.query(models.User).filter_by(id=user_id).first()
    old_active = user.active
    user.active = not user.active
    db.commit()

    log_action(
        db=db,
        admin_user_id=str(current_user["id"]),
        action="user_active_toggled",
        target_user_id=str(user.id),
        target_resource="user",
        old_value={"active": old_active},
        new_value={"active": user.active},
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    return RedirectResponse("/admin/users", status_code=303)


# ── Security & Audit ──────────────────────────────────────────────────────────

@router.get("/security/stats")
async def security_stats(request: Request, db: Session = Depends(get_db)):
    require_admin(request)
    from datetime import datetime, timedelta

    try:
        last_24h = datetime.utcnow().replace(tzinfo=None) - timedelta(days=1)

        failed_logins = db.query(models.SecurityEvent).filter(
            models.SecurityEvent.event_type == "failed_login",
            models.SecurityEvent.created_at >= last_24h,
        ).count()

        csrf_failures = db.query(models.SecurityEvent).filter(
            models.SecurityEvent.event_type == "csrf_failure",
            models.SecurityEvent.created_at >= last_24h,
        ).count()

        admin_actions = db.query(models.AuditLog).filter(
            models.AuditLog.created_at >= last_24h,
        ).count()

        unique_ips = db.query(models.SecurityEvent.ip_address).filter(
            models.SecurityEvent.created_at >= last_24h,
        ).distinct().count()
    except Exception as e:
        # Tables might not exist yet or migration pending
        return JSONResponse({
            "error": "Security tables not yet initialized",
            "message": str(e),
            "failed_logins_24h": 0,
            "csrf_failures_24h": 0,
            "admin_actions_24h": 0,
            "unique_ips_24h": 0,
        }, status_code=200)

    return JSONResponse({
        "failed_logins_24h": failed_logins,
        "csrf_failures_24h": csrf_failures,
        "admin_actions_24h": admin_actions,
        "unique_ips_24h": unique_ips,
    })
