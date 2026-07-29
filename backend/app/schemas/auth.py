"""Authentication and sensitive account schemas."""

from pydantic import BaseModel, ConfigDict, EmailStr, Field, model_validator

from app.schemas.user import ConsentCreate, UserResponse


class TokenResponse(BaseModel):
    """Bearer token returned after signup or login."""

    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class PasswordVerificationRequest(BaseModel):
    """Current password confirmation."""

    current_password: str = Field(min_length=8, max_length=128)


class AccountUpdateRequest(PasswordVerificationRequest):
    """Credential and display-name changes."""

    email: EmailStr | None = None
    new_password: str | None = Field(default=None, min_length=8, max_length=128)
    new_password_confirm: str | None = Field(
        default=None,
        min_length=8,
        max_length=128,
    )
    nickname: str | None = Field(default=None, max_length=50)

    @model_validator(mode="after")
    def passwords_match(self) -> "AccountUpdateRequest":
        """Require password confirmation when changing the password."""

        if self.new_password != self.new_password_confirm:
            raise ValueError("새 비밀번호 확인 값이 일치하지 않습니다.")
        return self


class AccountWithdrawRequest(PasswordVerificationRequest):
    """Final confirmation required for withdrawal."""

    confirm_withdrawal: bool


class MessageResponse(BaseModel):
    """Simple successful operation response."""

    message: str


class ConsentBatchUpdate(BaseModel):
    """Versioned privacy choices updated from Settings."""

    consents: list[ConsentCreate] = Field(min_length=1)


class ErrorResponse(BaseModel):
    """Stable expected-error envelope."""

    code: str
    detail: str

    model_config = ConfigDict(extra="forbid")
