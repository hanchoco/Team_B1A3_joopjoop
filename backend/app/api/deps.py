"""Shared FastAPI dependencies."""

from typing import Annotated

import jwt
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.security import decode_access_token
from app.crud import users as user_crud
from app.db.session import get_db
from app.models.user import User
from app.services.errors import AuthenticationError

bearer_scheme = HTTPBearer(auto_error=False)
DbSession = Annotated[Session, Depends(get_db)]


def get_current_user(
    db: DbSession,
    credentials: Annotated[
        HTTPAuthorizationCredentials | None,
        Depends(bearer_scheme),
    ],
) -> User:
    """Resolve the active account represented by a bearer token."""

    if credentials is None or credentials.scheme.lower() != "bearer":
        raise AuthenticationError("로그인이 필요합니다.")
    try:
        payload = decode_access_token(credentials.credentials)
        subject = payload.get("sub")
        user_id = int(subject)
    except (jwt.PyJWTError, TypeError, ValueError) as exc:
        raise AuthenticationError("유효하지 않은 인증 토큰입니다.") from exc
    user = user_crud.get_user_by_id(db, user_id)
    if user is None or str(user.account_status).split(".")[-1] != "ACTIVE":
        raise AuthenticationError("사용할 수 없는 계정입니다.")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]
