"""Signup, login, profile, credentials, consent, and withdrawal routes."""

from fastapi import APIRouter, status

from app.api.deps import CurrentUser, DbSession
from app.crud import users as user_crud
from app.schemas.auth import (
    AccountUpdateRequest,
    AccountWithdrawRequest,
    ConsentBatchUpdate,
    MessageResponse,
    PasswordVerificationRequest,
    TokenResponse,
)
from app.schemas.user import (
    ConsentResponse,
    UserCreate,
    UserLogin,
    UserProfileResponse,
    UserProfileUpdate,
    UserResponse,
)
from app.services import auth_service

auth_router = APIRouter(prefix="/auth", tags=["auth"])
router = APIRouter(prefix="/users", tags=["users"])


@auth_router.post(
    "/signup",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
)
def signup(payload: UserCreate, db: DbSession) -> TokenResponse:
    """Create an account, profile, and versioned consent records."""

    result = auth_service.register_user(db, payload)
    return TokenResponse(
        access_token=result.access_token,
        token_type=result.token_type,
        user=UserResponse.model_validate(result.user),
    )


@auth_router.post("/login", response_model=TokenResponse)
def login(payload: UserLogin, db: DbSession) -> TokenResponse:
    """Authenticate an active account."""

    result = auth_service.authenticate_user(db, payload)
    return TokenResponse(
        access_token=result.access_token,
        token_type=result.token_type,
        user=UserResponse.model_validate(result.user),
    )


@router.get("/me", response_model=UserResponse)
def get_my_account(current_user: CurrentUser) -> UserResponse:
    """Return the authenticated account."""

    return UserResponse.model_validate(current_user)


@router.get("/me/profile", response_model=UserProfileResponse)
def get_my_profile(
    db: DbSession,
    current_user: CurrentUser,
) -> UserProfileResponse:
    """Return stable matching profile fields."""

    profile = user_crud.get_user_profile(db, current_user.id)
    if profile is None:
        from app.services.errors import NotFoundError

        raise NotFoundError("사용자 기본 정보를 찾을 수 없습니다.")
    return UserProfileResponse.model_validate(profile)


@router.patch("/me/profile", response_model=UserProfileResponse)
def patch_my_profile(
    payload: UserProfileUpdate,
    db: DbSession,
    current_user: CurrentUser,
) -> UserProfileResponse:
    """Update onboarding/profile values used by future policy matches."""

    profile = user_crud.update_user_profile(
        db,
        user_id=current_user.id,
        values=payload.model_dump(exclude_unset=True),
    )
    return UserProfileResponse.model_validate(profile)


@router.post("/me/verify-password", response_model=MessageResponse)
def verify_my_password(
    payload: PasswordVerificationRequest,
    current_user: CurrentUser,
) -> MessageResponse:
    """Verify the current password before showing credential controls."""

    auth_service.verify_current_password(current_user, payload.current_password)
    return MessageResponse(message="비밀번호가 확인되었습니다.")


@router.patch("/me/account", response_model=UserResponse)
def patch_my_account(
    payload: AccountUpdateRequest,
    db: DbSession,
    current_user: CurrentUser,
) -> UserResponse:
    """Change login email, password, or nickname after verification."""

    user = auth_service.change_account(
        db,
        user=current_user,
        current_password=payload.current_password,
        email=str(payload.email) if payload.email is not None else None,
        new_password=payload.new_password,
        nickname=payload.nickname,
    )
    return UserResponse.model_validate(user)


@router.get("/me/consents", response_model=list[ConsentResponse])
def list_my_consents(
    db: DbSession,
    current_user: CurrentUser,
) -> list[ConsentResponse]:
    """Return versioned terms/privacy consent decisions."""

    return [
        ConsentResponse.model_validate(record)
        for record in user_crud.list_user_consents(db, current_user.id)
    ]


@router.put("/me/consents", response_model=list[ConsentResponse])
def update_my_consents(
    payload: ConsentBatchUpdate,
    db: DbSession,
    current_user: CurrentUser,
) -> list[ConsentResponse]:
    """Record new consent versions or withdrawals."""

    records = user_crud.replace_user_consents(
        db,
        user_id=current_user.id,
        consents=[consent.model_dump() for consent in payload.consents],
    )
    return [ConsentResponse.model_validate(record) for record in records]


@router.delete("/me", response_model=MessageResponse)
def withdraw_my_account(
    payload: AccountWithdrawRequest,
    db: DbSession,
    current_user: CurrentUser,
) -> MessageResponse:
    """Withdraw after password and explicit final confirmation."""

    if not payload.confirm_withdrawal:
        from app.services.errors import ConflictError

        raise ConflictError("회원 탈퇴 최종 동의가 필요합니다.")
    auth_service.withdraw_account(
        db,
        user=current_user,
        current_password=payload.current_password,
    )
    return MessageResponse(message="회원 탈퇴가 완료되었습니다.")
