from pydantic import BaseModel


class ChapterOutput(BaseModel):
    id: int
    number: int
    active_exercise_count: int
    assigned_exercise_count: int


class ChapterListOutput(BaseModel):
    chapters: list[ChapterOutput]
