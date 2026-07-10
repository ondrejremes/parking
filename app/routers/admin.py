from fastapi import APIRouter, Depends, Form, HTTPException, Request as FastAPIRequest
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.enums import SpotType
from app.services.auth import require_admin, get_current_user, generate_csrf_token, validate_csrf
from app import models

def _template_ctx(request: FastAPIRequest, **extra) -> dict:
    """Base template context with request, user, and app_version"""
    user = get_current_user(request)
    ctx = {
        "request": request,
        "user": user,
    }
    ctx.update(extra)
    return ctx

router = APIRouter(prefix="/admin")
templates = Jinja2Templates(directory="app/templates")


def _require_spots_manager(request: FastAPIRequest):
    user = get_current_user(request)
    if not user.get("is_admin") and not user.get("can_manage_spots"):
        raise HTTPException(status_code=403, detail="Nemáte oprávnění spravovat parkovací místa")
    return user


# ── Spots ──────────────────────────────────────────────────────────────────

@router.get("/spots", response_class=HTMLResponse)
async def spots(request: FastAPIRequest, db: Session = Depends(get_db)):
    _require_spots_manager(request)
    all_spots = db.query(models.Spot).order_by(models.Spot.floor, models.Spot.number).all()
    all_users = db.query(models.User).order_by(models.User.display_name).all()
    return templates.TemplateResponse("admin/spots.html", _template_ctx(request,
        spots=all_spots,
        users=all_users,
        csrf_token=generate_csrf_token(request),
        back_url="/calendar",
    ))


@router.post("/spots")
async def create_spot(
    request: FastAPIRequest,
    floor: str = Form(...),
    number: str = Form(...),
    spot_type: SpotType = Form(...),
    assigned_user_id: str | None = Form(None),
    csrf_token: str = Form(...),
    db: Session = Depends(get_db),
):
    validate_csrf(request, csrf_token)
    _require_spots_manager(request)
    spot = models.Spot(
        floor=floor,
        number=number,
        spot_type=spot_type,
        assigned_user_id=assigned_user_id or None,
    )
    db.add(spot)
    db.commit()
    return RedirectResponse("/admin/spots", status_code=303)


@router.post("/spots/{spot_id}/assign")
async def assign_spot(
    spot_id: str,
    request: FastAPIRequest,
    user_id: str | None = Form(None),
    csrf_token: str = Form(...),
    db: Session = Depends(get_db),
):
    validate_csrf(request, csrf_token)
    _require_spots_manager(request)
    spot = db.query(models.Spot).filter_by(id=spot_id).first()
    spot.assigned_user_id = user_id or None
    spot.spot_type = SpotType.ASSIGNED if user_id else SpotType.SHARED
    db.commit()
    return RedirectResponse("/admin/spots", status_code=303)


@router.post("/spots/{spot_id}/edit")
async def edit_spot(
    spot_id: str,
    request: FastAPIRequest,
    floor: str = Form(...),
    number: str = Form(...),
    spot_type: SpotType = Form(...),
    assigned_user_id: str | None = Form(None),
    active: str = Form(None),
    csrf_token: str = Form(...),
    db: Session = Depends(get_db),
):
    validate_csrf(request, csrf_token)
    _require_spots_manager(request)
    if not floor or not floor.replace("-", "").replace("P", "").isalnum():
        raise HTTPException(status_code=400, detail="Neplatné patro")
    if not number or not number.isalnum():
        raise HTTPException(status_code=400, detail="Neplatné číslo místa")
    spot = db.query(models.Spot).filter_by(id=spot_id).first()
    spot.floor = floor
    spot.number = number
    spot.spot_type = spot_type
    spot.assigned_user_id = assigned_user_id or None
    spot.active = active == "on"
    db.commit()
    return RedirectResponse("/admin/spots", status_code=303)


@router.post("/spots/{spot_id}/deactivate")
async def deactivate_spot(
    spot_id: str,
    request: FastAPIRequest,
    csrf_token: str = Form(...),
    db: Session = Depends(get_db),
):
    validate_csrf(request, csrf_token)
    _require_spots_manager(request)
    spot = db.query(models.Spot).filter_by(id=spot_id).first()
    spot.active = False
    db.commit()
    return RedirectResponse("/admin/spots", status_code=303)


# ── Users ──────────────────────────────────────────────────────────────────

@router.get("/users", response_class=HTMLResponse)
async def users(request: FastAPIRequest, db: Session = Depends(get_db)):
    require_admin(request)
    all_users = db.query(models.User).order_by(models.User.display_name).all()
    return templates.TemplateResponse("admin/users.html", _template_ctx(request,
        users=all_users,
        csrf_token=generate_csrf_token(request),
        back_url="/calendar",
    ))


@router.post("/users/{user_id}/toggle-admin")
async def toggle_admin(
    user_id: str,
    request: FastAPIRequest,
    csrf_token: str = Form(...),
    db: Session = Depends(get_db),
):
    validate_csrf(request, csrf_token)
    require_admin(request)
    user = db.query(models.User).filter_by(id=user_id).first()
    user.is_admin = not user.is_admin
    db.commit()
    return RedirectResponse("/admin/users", status_code=303)


@router.post("/users/{user_id}/toggle-guests")
async def toggle_guests(
    user_id: str,
    request: FastAPIRequest,
    csrf_token: str = Form(...),
    db: Session = Depends(get_db),
):
    validate_csrf(request, csrf_token)
    require_admin(request)
    user = db.query(models.User).filter_by(id=user_id).first()
    user.can_manage_guests = not user.can_manage_guests
    db.commit()
    return RedirectResponse("/admin/users", status_code=303)


@router.post("/users/{user_id}/toggle-reports")
async def toggle_reports(
    user_id: str,
    request: FastAPIRequest,
    csrf_token: str = Form(...),
    db: Session = Depends(get_db),
):
    validate_csrf(request, csrf_token)
    require_admin(request)
    user = db.query(models.User).filter_by(id=user_id).first()
    user.can_view_reports = not user.can_view_reports
    db.commit()
    return RedirectResponse("/admin/users", status_code=303)


@router.post("/users/{user_id}/toggle-spots")
async def toggle_spots(
    user_id: str,
    request: FastAPIRequest,
    csrf_token: str = Form(...),
    db: Session = Depends(get_db),
):
    validate_csrf(request, csrf_token)
    require_admin(request)
    user = db.query(models.User).filter_by(id=user_id).first()
    user.can_manage_spots = not user.can_manage_spots
    db.commit()
    return RedirectResponse("/admin/users", status_code=303)
