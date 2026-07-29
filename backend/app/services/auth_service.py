"""Account business rules independent of HTTP routing."""

from dataclasses import dataclass

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.security import create_access_token, hash_password, verify_password
from app.crud import users as user_crud
from app.models.user import User
from app.schemas.user import UserCreate, UserLogin
from app.services.errors import AuthenticationError, ConflictError


@dataclass(slots=True)
class AuthResult:
    """Successful authentication result."""

    user: User
    access_token: str
    token_type: str = "bearer"


def register_user(db: Session, payload: UserCreate) -> AuthResult:
    """Register a unique email account and return its first access token."""

    email = str(payload.email).strip().lower()
    if user_crud.get_user_by_email(db, email) is not None:
        raise ConflictError("이미 가입된 이메일입니다.")
    consent_values = {consent.consent_type.value: consent.is_agreed for consent in payload.consents}
    if len(consent_values) != len(payload.consents):
        raise ConflictError("동일한 동의 항목을 중복 제출할 수 없습니다.")
    if not consent_values.get("TERMS_REQUIRED") or not consent_values.get("PRIVACY_REQUIRED"):
        raise ConflictError("필수 약관과 개인정보 수집에 동의해야 합니다.")
    try:
        user = user_crud.create_user(
            db,
            email=email,
            password_hash=hash_password(payload.password),
            nickname=payload.nickname,
        )
        user_crud.replace_user_consents(
            db,
            user_id=user.id,
            consents=[consent.model_dump() for consent in payload.consents],
        )
    except IntegrityError as exc:
        db.rollback()
        raise ConflictError("이미 가입된 이메일입니다.") from exc
    token = create_access_token({"sub": str(user.id)})
    return AuthResult(user=user, access_token=token)


def authenticate_user(db: Session, payload: UserLogin) -> AuthResult:
    """Verify credentials for an active account."""

    user = user_crud.get_user_by_email(db, str(payload.email))
    if user is None or not verify_password(payload.password, user.password_hash):
        raise AuthenticationError("이메일 또는 비밀번호가 올바르지 않습니다.")
    if str(user.account_status).split(".")[-1] != "ACTIVE":
        raise AuthenticationError("사용할 수 없는 계정입니다.")
    user_crud.record_login(db, user)
    token = create_access_token({"sub": str(user.id)})
    return AuthResult(user=user, access_token=token)


def verify_current_password(user: User, password: str) -> None:
    """Require the current password before sensitive account changes."""

    if not verify_password(password, user.password_hash):
        raise AuthenticationError("현재 비밀번호가 올바르지 않습니다.")


def change_account(
    db: Session,
    *,
    user: User,
    current_password: str,
    email: str | None,
    new_password: str | None,
    nickname: str | None,
) -> User:
    """Change account identity or password after re-authentication."""

    verify_current_password(user, current_password)
    if email is not None:
        existing = user_crud.get_user_by_email(db, email)
        if existing is not None and existing.id != user.id:
            raise ConflictError("이미 가입된 이메일입니다.")
    password_hash = hash_password(new_password) if new_password else None
    return user_crud.update_account(
        db,
        user=user,
        email=email,
        password_hash=password_hash,
        nickname=nickname,
    )


def withdraw_account(db: Session, *, user: User, current_password: str) -> None:
    """Soft-delete an account after final password confirmation."""

    verify_current_password(user, current_password)
    user_crud.soft_delete_user(db, user)
