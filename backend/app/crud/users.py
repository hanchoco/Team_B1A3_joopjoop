"""User account and profile database access."""

from collections.abc import Mapping, Sequence
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.user import User, UserConsent, UserProfile

PROFILE_FIELDS = frozenset(
    {
        "birth_year",
        "region_code",
        "region_sido",
        "region_sigungu",
        "income_band_code",
        "employment_status_code",
        "household_type_code",
        "household_size",
        "housing_type_code",
        "onboarding_completed",
    }
)


def get_user_by_id(db: Session, user_id: int) -> User | None:
    """Return a user by primary key."""

    return db.get(User, user_id)


def get_user_by_email(db: Session, email: str) -> User | None:
    """Return a user by normalized email address."""

    statement = select(User).where(User.email == email.strip().lower())
    return db.scalar(statement)


def create_user(
    db: Session,
    *,
    email: str,
    password_hash: str,
    nickname: str | None,
) -> User:
    """Create an account and its one-to-one profile in one transaction."""

    user = User(
        email=email.strip().lower(),
        password_hash=password_hash,
        nickname=nickname,
        account_status="ACTIVE",
    )
    db.add(user)
    db.flush()
    db.add(UserProfile(user_id=user.id, onboarding_completed=False))
    db.commit()
    db.refresh(user)
    return user


def record_login(db: Session, user: User) -> User:
    """Persist the user's latest successful login time."""

    user.last_login_at = datetime.now(UTC).replace(tzinfo=None)
    db.commit()
    db.refresh(user)
    return user


def get_user_profile(db: Session, user_id: int) -> UserProfile | None:
    """Return a user's basic recommendation profile."""

    return db.get(UserProfile, user_id)


def update_user_profile(
    db: Session,
    *,
    user_id: int,
    values: Mapping[str, object],
) -> UserProfile:
    """Patch whitelisted profile fields and persist the result."""

    profile = get_user_profile(db, user_id)
    if profile is None:
        profile = UserProfile(user_id=user_id, onboarding_completed=False)
        db.add(profile)

    for field, value in values.items():
        if field not in PROFILE_FIELDS:
            raise ValueError(f"Unsupported profile field: {field}")
        setattr(profile, field, value)

    profile.updated_at = datetime.now(UTC).replace(tzinfo=None)
    db.commit()
    db.refresh(profile)
    return profile


def update_account(
    db: Session,
    *,
    user: User,
    email: str | None = None,
    password_hash: str | None = None,
    nickname: str | None = None,
) -> User:
    """Update mutable account credentials after service-level verification."""

    if email is not None:
        user.email = email.strip().lower()
    if password_hash is not None:
        user.password_hash = password_hash
    if nickname is not None:
        user.nickname = nickname
    user.updated_at = datetime.now(UTC).replace(tzinfo=None)
    db.commit()
    db.refresh(user)
    return user


def delete_user(db: Session, user: User) -> None:
    """Permanently remove an account and its cascaded records."""

    db.delete(user)
    db.commit()


def list_user_consents(db: Session, user_id: int) -> list[UserConsent]:
    """Return the user's consent history, newest first."""

    statement = (
        select(UserConsent)
        .where(UserConsent.user_id == user_id)
        .order_by(UserConsent.agreed_at.desc(), UserConsent.id.desc())
    )
    return list(db.scalars(statement).all())


def replace_user_consents(
    db: Session,
    *,
    user_id: int,
    consents: Sequence[Mapping[str, object]],
) -> list[UserConsent]:
    """Create or update one decision per consent type/version."""

    now = datetime.now(UTC).replace(tzinfo=None)
    created: list[UserConsent] = []
    for consent in consents:
        consent_type = consent.get("consent_type")
        consent_version = consent.get("consent_version")
        is_agreed = consent.get("is_agreed")
        if not isinstance(consent_type, str) or not isinstance(consent_version, str):
            raise ValueError("consent_type and consent_version are required")
        if not isinstance(is_agreed, bool):
            raise ValueError("is_agreed must be boolean")
        statement = select(UserConsent).where(
            UserConsent.user_id == user_id,
            UserConsent.consent_type == consent_type,
            UserConsent.consent_version == consent_version,
        )
        record = db.scalar(statement)
        if record is None:
            record = UserConsent(
                user_id=user_id,
                consent_type=consent_type,
                consent_version=consent_version,
            )
            db.add(record)
        record.is_agreed = is_agreed
        record.agreed_at = now
        record.withdrawn_at = None if is_agreed else now
        created.append(record)

    db.commit()
    for record in created:
        db.refresh(record)
    return created
