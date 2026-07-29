"""Policy-scoped AI Q&A schemas."""

from pydantic import BaseModel, Field


class PolicyQuestionRequest(BaseModel):
    """A single stateless question about the current policy."""

    question: str = Field(min_length=1, max_length=1000)


class PolicyQuestionResponse(BaseModel):
    """Solar answer plus reusable suggested questions."""

    answer: str
    suggested_questions: list[str]
