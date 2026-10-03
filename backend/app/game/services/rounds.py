from __future__ import annotations

import random
from collections import Counter
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.game.config import (
    NOTE_RANGE,
    TASKS_PER_ROUND,
    TIME_EASY_S,
    TIME_HARD_S,
    TIME_MEDIUM_S,
)
from app.game.models import Player, Round, TaskAttempt, TrophyAwarded
from app.services.auth import ServiceError
from app.settings import Settings


def time_limit_s(difficulty: str) -> int:
    return {"easy": TIME_EASY_S, "medium": TIME_MEDIUM_S, "hard": TIME_HARD_S}[
        difficulty
    ]


def score_task(
    expected: list[dict[str, object]], given: list[dict[str, object]] | None
) -> int:
    if given is None:
        return -1
    if len(given) != len(expected):
        return -1
    for e, g in zip(expected, given, strict=True):
        if e["name"] != g["name"] or e["octave"] != g["octave"]:
            return -1
    return 1


def check_timeout(
    issued_at: datetime, submitted_at: datetime, difficulty: str, grace_ms: int
) -> bool:
    limit = timedelta(seconds=time_limit_s(difficulty)) + timedelta(
        milliseconds=grace_ms
    )
    return submitted_at - issued_at > limit


def generate_tasks(
    difficulty: str, note_count: int, note_naming: str
) -> list[dict[str, object]]:
    tasks: list[dict[str, object]] = []
    last: tuple[str, tuple[tuple[str, int], ...]] | None = None
    for _ in range(TASKS_PER_ROUND):
        clef = random.choice(["treble", "bass"])
        pool = NOTE_RANGE[clef]
        notes: list[tuple[str, int]] = random.sample(pool, note_count)
        for _ in range(49):
            candidate: tuple[str, tuple[tuple[str, int], ...]] = (
                clef,
                tuple(notes),
            )
            if candidate != last:
                last = candidate
                break
            notes = random.sample(pool, note_count)
        tasks.append(
            {
                "clef": clef,
                "notes": [{"name": n, "octave": o} for n, o in notes],
            }
        )
    return tasks


def create_round(
    session: Session,
    player_id: int,
    season_id: int,
    difficulty: str,
    note_count: int,
    note_naming: str,
    settings: Settings,
) -> tuple[Round, list[dict[str, object]]]:
    now = datetime.now(UTC)
    tasks = generate_tasks(difficulty, note_count, note_naming)
    rnd = Round(
        player_id=player_id,
        season_id=season_id,
        difficulty=difficulty,
        note_count=note_count,
        note_naming=note_naming,
        status="active",
        created_at=now,
        expires_at=now + timedelta(seconds=settings.avatar_round_expire_s),
    )
    session.add(rnd)
    session.flush()
    for i, task in enumerate(tasks):
        attempt = TaskAttempt(
            round_id=rnd.id,
            season_id=season_id,
            task_index=i,
            clef=task["clef"],
            expected_notes=task["notes"],
            given_notes=None,
            is_correct=False,
            timed_out=False,
            score=0,
        )
        session.add(attempt)
    session.flush()
    return rnd, tasks


def submit_task(
    session: Session,
    round_id: int,
    task_index: int,
    answers: list[dict[str, object]] | None,
    timed_out: bool,
    submitted_at: datetime,
    settings: Settings,
) -> dict[str, object]:
    rnd = session.get(Round, round_id)
    if rnd is None or rnd.status != "active":
        raise ServiceError("ROUND_NOT_ACTIVE", 400)
    if submitted_at > rnd.expires_at:
        raise ServiceError("ROUND_EXPIRED", 400)

    attempt = session.scalar(
        select(TaskAttempt)
        .where(TaskAttempt.round_id == round_id, TaskAttempt.task_index == task_index)
        .with_for_update()
    )
    if attempt is None:
        raise ServiceError("TASK_NOT_FOUND", 404)
    if attempt.submitted_at is not None:
        return _build_submit_response(session, rnd, attempt, task_index)

    if attempt.issued_at is None:
        attempt.issued_at = submitted_at - timedelta(milliseconds=1)

    if not timed_out and attempt.issued_at is not None:
        timed_out = check_timeout(
            attempt.issued_at,
            submitted_at,
            rnd.difficulty,
            settings.avatar_gen_grace_ms,
        )

    if timed_out:
        attempt.timed_out = True
        attempt.given_notes = None
        attempt.is_correct = False
        attempt.score = -1
    else:
        attempt.given_notes = answers  # type: ignore[assignment]
        attempt.is_correct = (
            score_task(
                attempt.expected_notes,  # type: ignore[arg-type]
                answers,
            )
            == 1
        )
        attempt.score = 1 if attempt.is_correct else -1

    attempt.submitted_at = submitted_at
    if attempt.issued_at is not None:
        attempt.response_ms = int(
            (submitted_at - attempt.issued_at).total_seconds() * 1000
        )
    session.flush()
    return _build_submit_response(session, rnd, attempt, task_index)


def _build_submit_response(
    session: Session, rnd: Round, attempt: TaskAttempt, task_index: int
) -> dict[str, object]:
    next_index = task_index + 1
    next_task: dict[str, object] | None = None
    if next_index < TASKS_PER_ROUND:
        next_attempt = session.scalar(
            select(TaskAttempt).where(
                TaskAttempt.round_id == rnd.id,
                TaskAttempt.task_index == next_index,
            )
        )
        if next_attempt is not None:
            next_attempt.issued_at = datetime.now(UTC)
            session.flush()
            next_task = {
                "index": next_index,
                "clef": next_attempt.clef,
                "notes": next_attempt.expected_notes,
            }

    result: dict[str, object] | None = None
    if next_index >= TASKS_PER_ROUND:
        result = _finalize_round(session, rnd)

    return {
        "is_correct": attempt.is_correct,
        "correct_answers": attempt.expected_notes,
        "score_delta": attempt.score,
        "next_task": next_task,
        "result": result,
    }


def _finalize_round(session: Session, rnd: Round) -> dict[str, object] | None:
    from app.game.config import (
        LEVEL_THRESHOLDS,
        TROPHY_THRESHOLDS,
        WIN_THRESHOLD,
        XP_CORRECT_TASK,
        XP_WIN_BONUS,
    )

    if rnd.status == "completed":
        return None
    attempts = list(
        session.scalars(select(TaskAttempt).where(TaskAttempt.round_id == rnd.id))
    )
    if len(attempts) < TASKS_PER_ROUND or any(a.submitted_at is None for a in attempts):
        return None

    score = sum(a.score for a in attempts)
    correct_count = sum(1 for a in attempts if a.is_correct)
    is_win = correct_count >= WIN_THRESHOLD

    rnd.score = score
    rnd.correct_count = correct_count
    rnd.status = "completed"
    rnd.completed_at = datetime.now(UTC)

    xp_gained = correct_count * XP_CORRECT_TASK + (XP_WIN_BONUS if is_win else 0)

    player = session.get(Player, rnd.player_id)
    if player is None:
        return None
    old_xp = player.xp
    player.xp += xp_gained
    session.flush()

    level_up = _compute_level(player.xp, LEVEL_THRESHOLDS) > _compute_level(
        old_xp, LEVEL_THRESHOLDS
    )
    new_trophy = _check_trophy(session, player, rnd.season_id, TROPHY_THRESHOLDS)

    return {
        "score": score,
        "correct_count": correct_count,
        "is_win": is_win,
        "xp_gained": xp_gained,
        "level_up": level_up,
        "new_trophy": new_trophy,
        "practice_hint": _practice_hint(attempts),
    }


def _compute_level(xp: int, thresholds: list[int]) -> int:
    level = 0
    for i, threshold in enumerate(thresholds):
        if xp >= threshold:
            level = i
    return level


def _check_trophy(
    session: Session,
    player: Player,
    season_id: int,
    trophy_thresholds: list[int],
) -> int | None:

    completed = session.scalar(
        select(func.count())
        .select_from(Round)
        .where(Round.player_id == player.id, Round.status == "completed")
    )
    for threshold in sorted(trophy_thresholds):
        if completed is not None and completed >= threshold:
            already = session.scalar(
                select(TrophyAwarded).where(
                    TrophyAwarded.player_id == player.id,
                    TrophyAwarded.threshold == threshold,
                )
            )
            if already is None:
                session.add(TrophyAwarded(player_id=player.id, threshold=threshold))
                session.flush()
                return threshold
    return None


def _practice_hint(attempts: list[TaskAttempt]) -> str:
    confusions: Counter[tuple[str, str]] = Counter()
    for a in attempts:
        if not a.is_correct and not a.timed_out and a.given_notes is not None:
            expected_list: list[dict[str, object]] = a.expected_notes  # type: ignore[assignment]
            given_list: list[dict[str, object]] = a.given_notes  # type: ignore[assignment]
            for e, g in zip(expected_list, given_list, strict=False):
                if e["name"] != g["name"]:
                    confusions[(str(e["name"]), str(g["name"]))] += 1
    if confusions:
        (expected_name, given_name), _ = confusions.most_common(1)[0]
        return f"Потренируем {expected_name} и {given_name}?"
    return "Молодец! Продолжай в том же духе!"
