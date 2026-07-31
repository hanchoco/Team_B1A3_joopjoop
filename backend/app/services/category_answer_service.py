"""Category-answer management orchestration."""

from sqlalchemy.orm import Session

from app.crud import categories as category_crud
from app.services.errors import NotFoundError


def reset_category_answers(db: Session, *, user_id: int, category_id: int) -> int:
    """Delete all answers for one valid category owned by the user."""

    if category_crud.get_category(db, category_id) is None:
        raise NotFoundError("카테고리를 찾을 수 없습니다.")
    return category_crud.delete_user_category_answers(
        db,
        user_id=user_id,
        category_id=category_id,
    )
