import secrets
import bcrypt
from fastapi import HTTPException, Request
from sqlalchemy.orm import Session
from app import models
from app.config import ADMIN_USERNAME, ADMIN_PASSWORD_HASH


def get_current_user(request: Request) -> dict:
    user = request.session.get("user")
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user


def get_current_user_or_none(request: Request) -> dict | None:
    return request.session.get("user")


def require_admin(request: Request) -> dict:
    user = get_current_user(request)
    if not user.get("is_admin"):
        raise HTTPException(status_code=403, detail="Admin required")
    return user


def verify_admin_password(username: str, password: str) -> bool:
    if username != ADMIN_USERNAME:
        return False
    if not ADMIN_PASSWORD_HASH:
        return False
    return bcrypt.checkpw(password.encode(), ADMIN_PASSWORD_HASH.encode())


def verify_local_user(db: Session, username: str, password: str) -> models.User | None:
    user = db.query(models.User).filter(
        models.User.email == username,
        models.User.password_hash.isnot(None),
    ).first()
    if not user:
        return None
    if bcrypt.checkpw(password.encode(), user.password_hash.encode()):
        return user
    return None


def upsert_sso_user(db: Session, azure_oid: str | None, email: str, display_name: str) -> models.User:
    # For SSO users match by azure_oid; for local admin match by email
    if azure_oid:
        user = db.query(models.User).filter_by(azure_oid=azure_oid).first()
    else:
        user = db.query(models.User).filter_by(email=email).first()

    if user:
        user.display_name = display_name
        if azure_oid:
            user.email = email
    else:
        user = models.User(azure_oid=azure_oid, email=email, display_name=display_name)
        db.add(user)
    db.commit()
    db.refresh(user)
    return user


def generate_csrf_token(request: Request) -> str:
    if "csrf_token" not in request.session:
        request.session["csrf_token"] = secrets.token_hex(32)
    return request.session["csrf_token"]


def validate_csrf(request: Request, token: str):
    expected = request.session.get("csrf_token")
    if not expected or not secrets.compare_digest(expected, token):
        raise HTTPException(status_code=403, detail="Invalid CSRF token")
