"""Category and category-answer database access."""

from collections.abc import Mapping, Sequence
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.user_category_profile import (
    Category,
    CategoryQuestion,
    UserCategoryAnswer,
)

DEFAULT_CATEGORIES = (
    ("HOUSING", "주거", "주거비와 주거 안정 정책", 1),
    ("TRANSPORT", "교통", "교통비와 이동 지원 정책", 2),
    ("FINANCE", "금융", "대출, 저축, 자산 형성 정책", 3),
    ("TAX", "세금", "세액 감면과 공제 정책", 4),
    ("EMPLOYMENT", "고용", "취업과 재직 지원 정책", 5),
    ("WELFARE", "복지", "생활 안정과 복지 정책", 6),
    ("PARTICIPATION", "참여", "청년 활동과 참여 정책", 7),
    ("ETC", "기타", "그 밖의 청년 지원 정책", 8),
)


def ensure_default_categories(db: Session) -> list[Category]:
    """Create the stable category registry once and return it."""

    existing = {str(category.code.value): category for category in list_categories(db)}
    changed = False
    for code, name, description, order in DEFAULT_CATEGORIES:
        if code in existing:
            continue
        db.add(
            Category(
                code=code,
                name=name,
                description=description,
                display_order=order,
                is_active=True,
            )
        )
        changed = True
    if changed:
        db.commit()
    return list_categories(db)


def list_categories(db: Session, *, active_only: bool = True) -> list[Category]:
    """Return categories in their configured display order."""

    statement = select(Category)
    if active_only:
        statement = statement.where(Category.is_active.is_(True))
    statement = statement.order_by(Category.display_order.asc(), Category.id.asc())
    return list(db.scalars(statement).all())


def get_category(db: Session, category_id: int) -> Category | None:
    """Return a category by primary key."""

    return db.get(Category, category_id)


def get_category_by_code(db: Session, code: str) -> Category | None:
    """Return a category by its stable code."""

    statement = select(Category).where(Category.code == code.upper())
    return db.scalar(statement)


def list_category_questions(
    db: Session,
    category_id: int,
    *,
    active_only: bool = True,
) -> list[CategoryQuestion]:
    """Return the questions configured for one category."""

    statement = select(CategoryQuestion).where(CategoryQuestion.category_id == category_id)
    if active_only:
        statement = statement.where(CategoryQuestion.is_active.is_(True))
    statement = statement.order_by(
        CategoryQuestion.display_order.asc(),
        CategoryQuestion.id.asc(),
    )
    return list(db.scalars(statement).all())


def list_user_category_answers(
    db: Session,
    user_id: int,
    *,
    category_id: int | None = None,
) -> list[UserCategoryAnswer]:
    """Return answers for a user, optionally restricted to one category."""

    statement = select(UserCategoryAnswer).where(UserCategoryAnswer.user_id == user_id)
    if category_id is not None:
        statement = statement.join(
            CategoryQuestion,
            UserCategoryAnswer.question_id == CategoryQuestion.id,
        ).where(CategoryQuestion.category_id == category_id)
    return list(db.scalars(statement).all())


def get_user_answer_values(db: Session, user_id: int) -> dict[str, object]:
    """Return answers keyed by the Policy Engine ``question_key``."""

    statement = (
        select(CategoryQuestion.question_key, UserCategoryAnswer.answer_json)
        .join(
            UserCategoryAnswer,
            UserCategoryAnswer.question_id == CategoryQuestion.id,
        )
        .where(UserCategoryAnswer.user_id == user_id)
    )
    values: dict[str, object] = {}
    for question_key, answer_json in db.execute(statement):
        if isinstance(answer_json, Mapping) and "value" in answer_json:
            values[question_key] = answer_json["value"]
        else:
            values[question_key] = answer_json
    return values


def upsert_user_category_answers(
    db: Session,
    *,
    user_id: int,
    category_id: int,
    answers: Sequence[Mapping[str, object]],
) -> list[UserCategoryAnswer]:
    """Validate and save one answer per question for a category."""

    questions = list_category_questions(db, category_id, active_only=True)
    questions_by_id = {question.id: question for question in questions}
    now = datetime.now(UTC).replace(tzinfo=None)
    saved: list[UserCategoryAnswer] = []

    for payload in answers:
        question_id_raw = payload.get("question_id")
        if not isinstance(question_id_raw, int) or question_id_raw not in questions_by_id:
            raise ValueError(f"Unknown question_id for category {category_id}")

        answer_json = payload.get("answer_json")
        if not isinstance(answer_json, Mapping) or "value" not in answer_json:
            raise ValueError("answer_json must be an object containing 'value'")

        statement = select(UserCategoryAnswer).where(
            UserCategoryAnswer.user_id == user_id,
            UserCategoryAnswer.question_id == question_id_raw,
        )
        answer = db.scalar(statement)
        if answer is None:
            answer = UserCategoryAnswer(
                user_id=user_id,
                question_id=question_id_raw,
                answer_json=dict(answer_json),
                answered_at=now,
                updated_at=now,
            )
            db.add(answer)
        else:
            answer.answer_json = dict(answer_json)
            answer.updated_at = now
        saved.append(answer)

    db.commit()
    for answer in saved:
        db.refresh(answer)
    return saved
