from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from app.api.auth import Input
from app.api.exercises import ExerciseOutput
from app.services.listening import Event

RunStatus = Literal["active", "completed", "cancelled"]


class RunStartInput(Input):
    chapter_ids: list[int] = Field(min_length=1)

    @field_validator("chapter_ids")
    @classmethod
    def unique_positive_chapters(cls, value: list[int]) -> list[int]:
        if any(chapter_id <= 0 for chapter_id in value):
            raise ValueError("INVALID_CHAPTER_ID")
        if len(set(value)) != len(value):
            raise ValueError("DUPLICATE_CHAPTER_ID")
        return value


class RunNavigationInput(Input):
    direction: Literal["next", "previous"]


class RunItemOutput(BaseModel):
    position: int
    chapter_number: int
    exercise: ExerciseOutput


class ListeningRunOutput(BaseModel):
    id: int
    status: RunStatus
    chapter_numbers: list[int]
    current_index: int
    items: list[RunItemOutput]


class JournalChapterOption(BaseModel):
    chapter_number: int


class RunEventInput(Input):
    run_id: int = Field(gt=0)
    session_id: UUID
    exercise_id: int = Field(gt=0)
    audio_id: UUID | None = None
    event: Event
    position_seconds: float = Field(ge=0, allow_inf_nan=False)
    csrf_token: str = Field(min_length=1, max_length=128, repr=False)
