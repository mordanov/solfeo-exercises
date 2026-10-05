from __future__ import annotations

import random
from collections import Counter
from datetime import UTC, datetime, timedelta
from typing import cast

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
    expected: list[dict[str, object]],
    given: list[dict[str, object]] | None,
    *,
    note_only: bool = False,
) -> int:
    if given is None:
        return -1
    _validate_notes(given)
    _validate_notes(expected)
    if len(given) != len(expected):
        return -1
    for e, g in zip(expected, given, strict=True):
        if e["name"] != g["name"] or (not note_only and e["octave"] != g["octave"]):
            return -1
    return 1


def _validate_notes(notes: object) -> list[dict[str, object]]:
    if not isinstance(notes, list) or not 1 <= len(notes) <= 4:
        raise ServiceError("INVALID_ANSWERS", 422)
    for note in notes:
        if (
            not isinstance(note, dict)
            or set(note) != {"name", "octave"}
            or note.get("name") not in ("C", "D", "E", "F", "G", "A", "B")
            or type(note.get("octave")) is not int
            or note["octave"] not in (2, 3, 4, 5)
        ):
            raise ServiceError("INVALID_ANSWERS", 422)
    return cast(list[dict[str, object]], notes)


def task_payload(
    attempt: TaskAttempt, difficulty: str, server_now: datetime
) -> dict[str, object]:
    if attempt.issued_at is None:
        raise ServiceError("TASK_NOT_ISSUED", 400)
    limit_ms = time_limit_s(difficulty) * 1000
    return {
        "index": attempt.task_index,
        "clef": attempt.clef,
        "notes": attempt.expected_notes,
        "issued_at": attempt.issued_at.isoformat(),
        "deadline_at": (
            attempt.issued_at + timedelta(milliseconds=limit_ms)
        ).isoformat(),
        "time_limit_ms": limit_ms,
        "server_time": server_now.isoformat(),
    }


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
    *,
    show_sound_hint: bool = True,
    show_correct_answer: bool = False,
) -> tuple[Round, list[dict[str, object]]]:
    if difficulty not in ("easy", "medium", "hard"):
        raise ServiceError("INVALID_DIFFICULTY", 422)
    if type(note_count) is not int or note_count not in (1, 2, 3, 4):
        raise ServiceError("INVALID_NOTE_COUNT", 422)
    now = datetime.now(UTC)
    tasks = generate_tasks(difficulty, note_count, note_naming)
    rnd = Round(
        player_id=player_id,
        season_id=season_id,
        difficulty=difficulty,
        note_count=note_count,
        note_naming=note_naming,
        show_sound_hint=show_sound_hint,
        show_correct_answer=show_correct_answer,
        rules_version=2,
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
            issued_at=now if i == 0 else None,
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
    if type(task_index) is not int or not 0 <= task_index < TASKS_PER_ROUND:
        raise ServiceError("INVALID_TASK_INDEX", 422)
    rnd = session.scalar(
        select(Round)
        .where(Round.id == round_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if rnd is None:
        raise ServiceError("ROUND_NOT_ACTIVE", 400)

    attempt = session.scalar(
        select(TaskAttempt)
        .where(TaskAttempt.round_id == round_id, TaskAttempt.task_index == task_index)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if attempt is None:
        raise ServiceError("TASK_NOT_FOUND", 404)
    if attempt.submitted_at is not None:
        if attempt.submit_response is not None:
            return attempt.submit_response
        response = _build_submit_response(
            session, rnd, attempt, task_index, submitted_at, settings
        )
        attempt.submit_response = response
        session.flush()
        return response

    if rnd.status != "active":
        raise ServiceError("ROUND_NOT_ACTIVE", 400)
    if submitted_at > rnd.expires_at:
        raise ServiceError("ROUND_EXPIRED", 400)

    previous_pending = session.scalar(
        select(TaskAttempt.id)
        .where(
            TaskAttempt.round_id == round_id,
            TaskAttempt.task_index < task_index,
            TaskAttempt.submitted_at.is_(None),
        )
        .limit(1)
    )
    if attempt.issued_at is None or previous_pending is not None:
        raise ServiceError("TASK_NOT_ISSUED", 400)
    if submitted_at < attempt.issued_at:
        raise ServiceError("TASK_NOT_STARTED", 400)

    if answers is not None:
        _validate_notes(answers)
    if not timed_out:
        if answers is None or len(answers) != rnd.note_count:
            raise ServiceError("INVALID_ANSWERS", 422)
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
        # Historical JSON columns are annotated as objects but hold note arrays.
        attempt.given_notes = cast(dict[str, object], answers)
        attempt.is_correct = (
            score_task(
                _validate_notes(attempt.expected_notes),
                answers,
                note_only=rnd.rules_version >= 2,
            )
            == 1
        )
        attempt.score = 1 if attempt.is_correct else -1

    attempt.submitted_at = submitted_at
    attempt.response_ms = int((submitted_at - attempt.issued_at).total_seconds() * 1000)
    session.flush()
    response = _build_submit_response(
        session, rnd, attempt, task_index, submitted_at, settings
    )
    attempt.submit_response = response
    session.flush()
    return response


def _build_submit_response(
    session: Session,
    rnd: Round,
    attempt: TaskAttempt,
    task_index: int,
    submitted_at: datetime,
    settings: Settings,
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
            if next_attempt.issued_at is None:
                next_attempt.issued_at = submitted_at + timedelta(
                    milliseconds=settings.game_feedback_ms
                )
            session.flush()
            next_task = task_payload(next_attempt, rnd.difficulty, submitted_at)

    result: dict[str, object] | None = None
    if next_index >= TASKS_PER_ROUND:
        result = _finalize_round(session, rnd, submitted_at, settings)

    return {
        "is_correct": attempt.is_correct,
        "timed_out": attempt.timed_out,
        "correct_answers": attempt.expected_notes,
        "score_delta": attempt.score,
        "next_task": next_task,
        "result": result,
    }


def _finalize_round(
    session: Session, rnd: Round, submitted_at: datetime, settings: Settings
) -> dict[str, object] | None:
    from app.game.config import (
        LEVEL_THRESHOLDS,
        TROPHY_THRESHOLDS,
        WIN_THRESHOLD,
        XP_CORRECT_TASK,
        XP_WIN_BONUS,
    )
    from app.game.services.achievements import evaluate_achievements

    if rnd.status == "completed":
        return None
    attempts = list(
        session.scalars(select(TaskAttempt).where(TaskAttempt.round_id == rnd.id))
    )
    if len(attempts) < TASKS_PER_ROUND or any(a.submitted_at is None for a in attempts):
        return None

    score_bonus = (
        int(not rnd.show_sound_hint) + int(not rnd.show_correct_answer)
        if rnd.rules_version >= 2
        else 0
    )
    score = max(0, sum(a.score for a in attempts) + score_bonus)
    correct_count = sum(1 for a in attempts if a.is_correct)
    is_win = correct_count >= WIN_THRESHOLD

    # Refresh after locking: another round may have changed an identity-map player.
    player = session.scalar(
        select(Player)
        .where(Player.id == rnd.player_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if player is None:
        raise ServiceError("PLAYER_NOT_FOUND", 404)

    historical_average = session.scalar(
        select(func.avg(func.greatest(Round.score, 0))).where(
            Round.player_id == rnd.player_id,
            Round.id != rnd.id,
            Round.status == "completed",
            Round.difficulty == rnd.difficulty,
            Round.note_count == rnd.note_count,
            Round.score.is_not(None),
        )
    )
    average_score = (
        float(historical_average) if historical_average is not None else None
    )

    rnd.score = score
    rnd.correct_count = correct_count
    rnd.status = "completed"
    rnd.completed_at = submitted_at

    xp_gained = correct_count * XP_CORRECT_TASK + (XP_WIN_BONUS if is_win else 0)

    old_xp = player.xp
    player.xp += xp_gained
    session.flush()

    level_up = _compute_level(player.xp, LEVEL_THRESHOLDS) > _compute_level(
        old_xp, LEVEL_THRESHOLDS
    )
    new_trophy = _check_trophy(session, player, rnd.season_id, TROPHY_THRESHOLDS)
    new_achievements = evaluate_achievements(session, player, rnd, settings)

    return {
        "score": score,
        "score_bonus": score_bonus,
        "correct_count": correct_count,
        "is_win": is_win,
        "xp_gained": xp_gained,
        "level_up": level_up,
        "new_trophy": new_trophy,
        "new_achievements": new_achievements,
        "average_score": average_score,
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


def _practice_hint(attempts: list[TaskAttempt]) -> dict[str, str] | None:
    confusions: Counter[tuple[str, str]] = Counter()
    for a in attempts:
        if not a.is_correct and not a.timed_out and a.given_notes is not None:
            expected_list = _validate_notes(a.expected_notes)
            given_list = _validate_notes(a.given_notes)
            for e, g in zip(expected_list, given_list, strict=False):
                if e["name"] != g["name"]:
                    confusions[(str(e["name"]), str(g["name"]))] += 1
    if confusions:
        (expected_name, given_name), _ = confusions.most_common(1)[0]
        return {"expected": expected_name, "given": given_name}
    return None
