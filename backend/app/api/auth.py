import secrets

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..core.security import create_access_token, hash_password, verify_password
from ..db.models import User, UserPreference
from ..db.session import get_db
from ..schemas import LoginIn, RegisterIn, TokenOut, UserOut

router = APIRouter(prefix="/auth", tags=["auth"])

# Constant dummy hash so login timing does not reveal whether an email exists.
_DUMMY = hash_password("not-a-real-password")


def _token(user: User) -> TokenOut:
    return TokenOut(access_token=create_access_token(user.id), user=UserOut.model_validate(user))


@router.post("/register", response_model=TokenOut, status_code=201)
def register(body: RegisterIn, db: Session = Depends(get_db)):
    email = body.email.lower()
    if db.scalar(select(User).where(User.email == email)):
        raise HTTPException(status.HTTP_409_CONFLICT, "An account with this email already exists")
    user = User(email=email, password_hash=hash_password(body.password), display_name=body.display_name.strip())
    user.preferences = UserPreference()
    db.add(user)
    db.commit()
    return _token(user)


@router.post("/login", response_model=TokenOut)
def login(body: LoginIn, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.email == body.email.lower()))
    ok = verify_password(body.password, user.password_hash if user else _DUMMY)
    if not user or not ok:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Incorrect email or password")
    return _token(user)


@router.post("/demo", response_model=TokenOut, status_code=201)
def demo_guest(db: Session = Depends(get_db)):
    """Creates a throwaway guest account so the full app works with zero sign-up friction."""
    tag = secrets.token_hex(4)
    user = User(email=f"guest-{tag}@demo.neurosonic.local", password_hash=hash_password(secrets.token_urlsafe(16)),
                display_name=f"Guest {tag[:4].upper()}", is_demo=True)
    user.preferences = UserPreference()
    db.add(user)
    db.commit()
    return _token(user)
