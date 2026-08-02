"""Category and category-answer database access."""

from collections.abc import Mapping, Sequence
from datetime import UTC, datetime

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models.user_category_profile import (
    AnswerType,
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

DEFAULT_CATEGORY_QUESTIONS: dict[
    str, tuple[tuple[str, str, AnswerType, list[dict[str, str]] | None, str | None], ...]
] = {
    "EMPLOYMENT": (
        (
            "employment.company_size_code",
            "현재 근무 중인 회사의 규모를 알려주세요",
            AnswerType.SINGLE_SELECT,
            [
                {"label": "5인 미만", "value": "MICRO"},
                {"label": "5~49인", "value": "SMALL"},
                {"label": "50~299인", "value": "MEDIUM"},
                {"label": "300인 이상", "value": "LARGE"},
                {"label": "공공기관/공기업", "value": "PUBLIC"},
                {"label": "해당 없음", "value": "UNKNOWN"},
            ],
            None,
        ),
        (
            "employment.contract_type_code",
            "현재 근로계약 형태를 알려주세요",
            AnswerType.SINGLE_SELECT,
            [
                {"label": "정규직 (계약기간을 정하지 않음)", "value": "PERMANENT"},
                {"label": "계약직·기간제·인턴 (계약 종료일이 있음)", "value": "FIXED_TERM"},
                {"label": "파견직·용역직 (소속 회사와 근무지가 다름)", "value": "DISPATCHED"},
                {"label": "프리랜서·특수고용", "value": "FREELANCER"},
                {"label": "일용직·단기 아르바이트", "value": "DAILY"},
                {"label": "현재 근무 중이 아님", "value": "UNKNOWN"},
            ],
            None,
        ),
        (
            "employment.tenure_months",
            "현재 직장에서 근속한 개월 수를 알려주세요",
            AnswerType.NUMBER,
            None,
            "개월",
        ),
        (
            "employment.insurance_enrolled",
            "고용보험에 가입되어 있나요?",
            AnswerType.BOOLEAN,
            None,
            None,
        ),
        (
            "employment.job_field_code",
            "현재(또는 희망) 직무 분야를 모두 선택해주세요",
            AnswerType.MULTI_SELECT,
            [
                {"label": "IT/개발", "value": "IT"},
                {"label": "마케팅", "value": "MARKETING"},
                {"label": "디자인", "value": "DESIGN"},
                {"label": "영업", "value": "SALES"},
                {"label": "생산/제조", "value": "MANUFACTURING"},
                {"label": "서비스/고객응대", "value": "SERVICE"},
                {"label": "교육", "value": "EDUCATION"},
                {"label": "의료/보건", "value": "MEDICAL"},
                {"label": "사무/행정", "value": "ADMIN"},
                {"label": "기타", "value": "OTHER"},
            ],
            None,
        ),
    ),
    "HOUSING": (
        ("housing.deposit_amount", "임차 보증금을 알려주세요", AnswerType.NUMBER, None, "원"),
        ("housing.monthly_rent_amount", "월세액을 알려주세요", AnswerType.NUMBER, None, "원"),
        ("housing.is_household_head", "본인이 세대주인가요?", AnswerType.BOOLEAN, None, None),
        (
            "housing.has_lease_contract",
            "임대차 계약서를 제출할 수 있나요?",
            AnswerType.BOOLEAN,
            None,
            None,
        ),
        (
            "housing.residence_months",
            "현재 거주지에 거주한 개월 수를 알려주세요",
            AnswerType.NUMBER,
            None,
            "개월",
        ),
        (
            "housing.home_ownership_status_code",
            "현재 주택 소유 상태를 알려주세요",
            AnswerType.SINGLE_SELECT,
            [
                {"label": "무주택", "value": "NONE"},
                {"label": "본인 소유", "value": "SELF"},
                {"label": "세대원 소유", "value": "HOUSEHOLD_MEMBER"},
                {"label": "해당 없음/모름", "value": "UNKNOWN"},
            ],
            None,
        ),
    ),
    "FINANCE": (
        (
            "finance.monthly_income_amount",
            "월 평균 소득을 알려주세요",
            AnswerType.NUMBER,
            None,
            "원",
        ),
        ("finance.annual_income_amount", "연 소득을 알려주세요", AnswerType.NUMBER, None, "원"),
        ("finance.total_asset_amount", "총 자산가액을 알려주세요", AnswerType.NUMBER, None, "원"),
        ("finance.total_debt_amount", "총 부채액을 알려주세요", AnswerType.NUMBER, None, "원"),
        (
            "finance.fixed_monthly_expense_amount",
            "월 고정 지출(월세, 대출상환 등)을 알려주세요",
            AnswerType.NUMBER,
            None,
            "원",
        ),
    ),
    "WELFARE": (
        (
            "welfare.is_basic_livelihood_recipient",
            "기초생활수급자이신가요?",
            AnswerType.BOOLEAN,
            None,
            None,
        ),
        (
            "welfare.is_near_poverty_household",
            "차상위계층에 해당하시나요?",
            AnswerType.BOOLEAN,
            None,
            None,
        ),
    ),
}


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


def ensure_default_category_questions(db: Session) -> list[CategoryQuestion]:
    """Create the stable onboarding-question registry once and return it."""

    categories_by_code = {str(category.code.value): category for category in list_categories(db)}
    existing_keys = {
        (question.category_id, question.question_key)
        for question in db.scalars(select(CategoryQuestion)).all()
    }
    changed = False
    for code, questions in DEFAULT_CATEGORY_QUESTIONS.items():
        category = categories_by_code.get(code)
        if category is None:
            continue
        for order, (question_key, label, answer_type, options_json, unit) in enumerate(
            questions, start=1
        ):
            if (category.id, question_key) in existing_keys:
                continue
            db.add(
                CategoryQuestion(
                    category_id=category.id,
                    question_key=question_key,
                    label=label,
                    answer_type=answer_type,
                    options_json=options_json,
                    unit=unit,
                    is_required=False,
                    is_used_for_matching=True,
                    display_order=order,
                    is_active=True,
                )
            )
            changed = True
    if changed:
        db.commit()
    return list(db.scalars(select(CategoryQuestion)).all())


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


def delete_user_category_answers(
    db: Session,
    *,
    user_id: int,
    category_id: int,
) -> int:
    """Delete every saved answer owned by a user for one category."""

    question_ids = select(CategoryQuestion.id).where(CategoryQuestion.category_id == category_id)
    result = db.execute(
        delete(UserCategoryAnswer).where(
            UserCategoryAnswer.user_id == user_id,
            UserCategoryAnswer.question_id.in_(question_ids),
        )
    )
    db.commit()
    return int(result.rowcount or 0)
