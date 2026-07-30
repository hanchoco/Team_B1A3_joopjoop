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


# EMPLOYMENT, HOUSING, FINANCE, and WELFARE have category-specific structured
# questions; every `question_key` below is registered as a matching condition
# key in ``services/policy_engine/rules.py``'s ``CONDITION_KEY_REGISTRY``, so
# answers here actually feed into policy matching (not just displayed UI).
# TRANSPORT/TAX/PARTICIPATION/ETC have no registered condition keys yet, so
# they intentionally have no extra questions (inventing ones with no matching
# condition_key would just be unusable UI).
DEFAULT_CATEGORY_QUESTIONS: dict[str, tuple[dict[str, object], ...]] = {
    "HOUSING": (
        {
            "question_key": "housing.deposit_amount",
            "label": "임차 보증금을 알려주세요",
            "description": None,
            "answer_type": "NUMBER",
            "unit": "원",
            "is_required": False,
            "is_used_for_matching": True,
            "display_order": 1,
        },
        {
            "question_key": "housing.monthly_rent_amount",
            "label": "월세액을 알려주세요",
            "description": None,
            "answer_type": "NUMBER",
            "unit": "원",
            "is_required": False,
            "is_used_for_matching": True,
            "display_order": 2,
        },
        {
            "question_key": "housing.is_household_head",
            "label": "본인이 세대주인가요?",
            "description": None,
            "answer_type": "BOOLEAN",
            "is_required": False,
            "is_used_for_matching": True,
            "display_order": 3,
        },
        {
            "question_key": "housing.has_lease_contract",
            "label": "임대차 계약서를 제출할 수 있나요?",
            "description": None,
            "answer_type": "BOOLEAN",
            "is_required": False,
            "is_used_for_matching": True,
            "display_order": 4,
        },
        {
            "question_key": "housing.residence_months",
            "label": "현재 거주지에 거주한 개월 수를 알려주세요",
            "description": None,
            "answer_type": "NUMBER",
            "unit": "개월",
            "is_required": False,
            "is_used_for_matching": True,
            "display_order": 5,
        },
    ),
    "FINANCE": (
        {
            "question_key": "finance.monthly_income_amount",
            "label": "월 평균 소득을 알려주세요",
            "description": None,
            "answer_type": "NUMBER",
            "unit": "원",
            "is_required": False,
            "is_used_for_matching": True,
            "display_order": 1,
        },
        {
            "question_key": "finance.annual_income_amount",
            "label": "연 소득을 알려주세요",
            "description": None,
            "answer_type": "NUMBER",
            "unit": "원",
            "is_required": False,
            "is_used_for_matching": True,
            "display_order": 2,
        },
        {
            "question_key": "finance.total_asset_amount",
            "label": "총 자산가액을 알려주세요",
            "description": None,
            "answer_type": "NUMBER",
            "unit": "원",
            "is_required": False,
            "is_used_for_matching": True,
            "display_order": 3,
        },
        {
            "question_key": "finance.total_debt_amount",
            "label": "총 부채액을 알려주세요",
            "description": None,
            "answer_type": "NUMBER",
            "unit": "원",
            "is_required": False,
            "is_used_for_matching": True,
            "display_order": 4,
        },
        {
            "question_key": "finance.fixed_monthly_expense_amount",
            "label": "월 고정 지출(월세, 대출상환 등)을 알려주세요",
            "description": None,
            "answer_type": "NUMBER",
            "unit": "원",
            "is_required": False,
            "is_used_for_matching": True,
            "display_order": 5,
        },
    ),
    "WELFARE": (
        {
            "question_key": "welfare.is_basic_livelihood_recipient",
            "label": "기초생활수급자이신가요?",
            "description": None,
            "answer_type": "BOOLEAN",
            "is_required": False,
            "is_used_for_matching": True,
            "display_order": 1,
        },
        {
            "question_key": "welfare.is_near_poverty_household",
            "label": "차상위계층에 해당하시나요?",
            "description": None,
            "answer_type": "BOOLEAN",
            "is_required": False,
            "is_used_for_matching": True,
            "display_order": 2,
        },
    ),
    "EMPLOYMENT": (
        {
            "question_key": "employment.company_size_code",
            "label": "다니시는 회사 규모가 어떻게 되나요?",
            "description": "회사 규모에 따라 지원 가능한 정책이 달라져요.",
            "answer_type": "SINGLE_SELECT",
            "options_json": ["소기업", "중소기업", "중견기업", "대기업", "공공기관", "비영리/기타"],
            "is_required": False,
            "is_used_for_matching": True,
            "display_order": 1,
        },
        {
            "question_key": "employment.contract_type_code",
            "label": "고용 형태가 어떻게 되나요?",
            "description": None,
            "answer_type": "SINGLE_SELECT",
            "options_json": ["정규직", "계약직", "일용직", "프리랜서", "기타"],
            "is_required": False,
            "is_used_for_matching": True,
            "display_order": 2,
        },
        {
            "question_key": "employment.tenure_months",
            "label": "근속 기간이 얼마나 되셨나요?",
            "description": "개월 수로 입력해주세요.",
            "answer_type": "NUMBER",
            "unit": "개월",
            "is_required": False,
            "is_used_for_matching": True,
            "display_order": 3,
        },
        {
            "question_key": "employment.insurance_enrolled",
            "label": "고용보험에 가입되어 있나요?",
            "description": None,
            "answer_type": "BOOLEAN",
            "is_required": False,
            "is_used_for_matching": True,
            "display_order": 4,
        },
        {
            "question_key": "employment.job_field_code",
            "label": "직무 분야가 어떻게 되나요?",
            "description": None,
            "answer_type": "SINGLE_SELECT",
            "options_json": [
                "IT/개발",
                "경영/사무",
                "영업/마케팅",
                "생산/제조",
                "서비스",
                "교육",
                "의료/복지",
                "기타",
            ],
            "is_required": False,
            "is_used_for_matching": True,
            "display_order": 5,
        },
    ),
}


def ensure_default_category_questions(db: Session) -> list[CategoryQuestion]:
    """Create the stable question registry once and return it (idempotent)."""

    categories_by_code = {
        str(category.code.value): category for category in list_categories(db, active_only=False)
    }
    changed = False
    for code, questions in DEFAULT_CATEGORY_QUESTIONS.items():
        category = categories_by_code.get(code)
        if category is None:
            continue
        existing_keys = {
            question.question_key
            for question in list_category_questions(db, category.id, active_only=False)
        }
        for spec in questions:
            if spec["question_key"] in existing_keys:
                continue
            db.add(
                CategoryQuestion(
                    category_id=category.id,
                    question_key=spec["question_key"],
                    label=spec["label"],
                    description=spec.get("description"),
                    answer_type=spec["answer_type"],
                    options_json=spec.get("options_json"),
                    unit=spec.get("unit"),
                    is_required=spec["is_required"],
                    is_used_for_matching=spec["is_used_for_matching"],
                    display_order=spec["display_order"],
                    is_active=True,
                )
            )
            changed = True
    if changed:
        db.commit()
    return [
        question
        for category in categories_by_code.values()
        for question in list_category_questions(db, category.id, active_only=False)
    ]


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
