from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
import msal

from app.database import get_db
from app.config import (
    AZURE_CLIENT_ID, AZURE_CLIENT_SECRET, AZURE_TENANT_ID, AZURE_REDIRECT_URI, BASE_URL
)
from app.services.auth import verify_admin_password, verify_local_user, upsert_sso_user, generate_csrf_token, validate_csrf

router = APIRouter(prefix="/auth")
templates = Jinja2Templates(directory="app/templates")


def _msal_app():
    return msal.ConfidentialClientApplication(
        AZURE_CLIENT_ID,
        authority=f"https://login.microsoftonline.com/{AZURE_TENANT_ID}",
        client_credential=AZURE_CLIENT_SECRET,
    )


@router.get("/login")
async def login(request: Request):
    flow = _msal_app().initiate_auth_code_flow(
        scopes=["User.Read"],
        redirect_uri=AZURE_REDIRECT_URI,
    )
    request.session["auth_flow"] = flow
    return RedirectResponse(flow["auth_uri"])


@router.get("/callback")
async def callback(request: Request, db: Session = Depends(get_db)):
    flow = request.session.pop("auth_flow", None)
    if not flow:
        return RedirectResponse("/auth/admin-login")

    result = _msal_app().acquire_token_by_auth_code_flow(flow, dict(request.query_params))
    if "error" in result:
        return RedirectResponse("/auth/admin-login")

    claims = result.get("id_token_claims", {})
    user = upsert_sso_user(
        db,
        azure_oid=claims["oid"],
        email=claims.get("preferred_username", claims.get("email", "")),
        display_name=claims.get("name", ""),
    )
    request.session["user"] = {
        "id": str(user.id),
        "email": user.email,
        "display_name": user.display_name,
        "is_admin": user.is_admin,
        "can_manage_guests": user.can_manage_guests,
        "can_manage_spots": user.can_manage_spots,
    }
    return RedirectResponse("/")


@router.get("/admin-login", response_class=HTMLResponse)
async def admin_login_form(request: Request):
    csrf = generate_csrf_token(request)
    return templates.TemplateResponse("auth/login.html", {"request": request, "csrf_token": csrf})


@router.post("/admin-login", response_class=HTMLResponse)
async def admin_login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    csrf_token: str = Form(...),
    db: Session = Depends(get_db),
):
    validate_csrf(request, csrf_token)

    if verify_admin_password(username, password):
        # Ensure local admin has a proper DB user record (needed for reservations FK)
        admin_user = upsert_sso_user(db, azure_oid=None, email=username, display_name="Admin")
        if not admin_user.is_admin:
            admin_user.is_admin = True
            db.commit()
        request.session["user"] = {
            "id": str(admin_user.id),
            "email": admin_user.email,
            "display_name": admin_user.display_name,
            "is_admin": True,
            "can_manage_guests": admin_user.can_manage_guests,
            "can_manage_spots": admin_user.can_manage_spots,
        }
        return RedirectResponse("/", status_code=303)

    local_user = verify_local_user(db, username, password)
    if local_user:
        request.session["user"] = {
            "id": str(local_user.id),
            "email": local_user.email,
            "display_name": local_user.display_name,
            "is_admin": local_user.is_admin,
            "can_manage_guests": local_user.can_manage_guests,
            "can_manage_spots": local_user.can_manage_spots,
        }
        return RedirectResponse("/", status_code=303)

    csrf = generate_csrf_token(request)
    return templates.TemplateResponse(
        "auth/login.html",
        {"request": request, "csrf_token": csrf, "error": "Nesprávné přihlašovací údaje"},
        status_code=401,
    )


@router.get("/logout")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/auth/admin-login")
