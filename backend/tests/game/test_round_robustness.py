from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from threading import Barrier
from typing import cast
from uuid import uuid4

import pytest
from pydantic import ValidationError
from sqlalchemy import create_engine, select, text

from app.database import Database
from app.game.api.rounds import SubmitTaskBody
from app.game.models import Player, Round, Season, TaskAttempt
from app.game.services.rounds import create_round, submit_task, task_payload
from app.models import Base
from app.services.auth import ServiceError, create_user
from app.settings import Settings


@pytest.fixture(scope="module")
def robustness_settings() -> Settings:
    return Settings(
        database_name=f"solfeo_round_test_{uuid4().hex}",
        auth_allowed_origins=["https://test"],
        session_cookie_secure=True,
        game_feedback_ms=900,
    )


@pytest.fixture(scope="module")
def robustness_database(robustness_settings: Settings) -> Iterator[Database]:
    if robustness_settings.database_host not in ("localhost", "127.0.0.1"):
        raise pytest.UsageError("Round robustness tests require local PostgreSQL")
    admin = create_engine(
        robustness_settings.database_url.set(database="postgres"),
        isolation_level="AUTOCOMMIT",
    )
    name = robustness_settings.database_name
    with admin.connect() as connection:
        connection.execute(text(f'CREATE DATABASE "{name}"'))
    database = Database(robustness_settings)
    try:
        Base.metadata.create_all(database.engine)
        yield database
    finally:
        database.close()
        with admin.connect() as connection:
            connection.execute(text(f'DROP DATABASE "{name}"'))
        admin.dispose()


def new_round(database: Database, settings: Settings, *, note_count: int = 1) -> int:
    with database.session() as session:
        user = create_user(
            session,
            settings,
            username=f"round-{uuid4().hex[:12]}",
            password="Synthetic-test-password1!",
            first_name="Round",
            last_name="Test",
            role="student",
            must_change_password=False,
        )
        with session.begin():
            player = Player(account_id=user.id, name="Round test", xp=145)
            session.add(player)
            session.flush()
            season = Season(player_id=player.id, number=1)
            session.add(season)
            session.flush()
            rnd, _ = create_round(
                session, player.id, season.id, "easy", note_count, "letters", settings
            )
            return rnd.id


def submit(
    database: Database,
    settings: Settings,
    round_id: int,
    index: int,
    *,
    correct: bool = True,
) -> dict[str, object]:
    with database.session() as session, session.begin():
        attempt = session.scalar(
            select(TaskAttempt).where(
                TaskAttempt.round_id == round_id, TaskAttempt.task_index == index
            )
        )
        assert attempt is not None
        now = max(datetime.now(UTC), attempt.issued_at or datetime.now(UTC))
        answers = attempt.expected_notes if correct else [{"name": "C", "octave": 4}]
        return submit_task(
            session,
            round_id,
            index,
            answers if isinstance(answers, list) else None,
            not correct,
            now,
            settings,
        )


@pytest.mark.parametrize(
    "payload",
    [
        {"task_index": -1, "timed_out": True},
        {"task_index": 7, "timed_out": True},
        {"task_index": 0, "answers": [{"name": "X", "octave": 4}]},
        {"task_index": 0, "answers": [{"name": "C", "octave": 1}]},
        {"task_index": 0, "answers": [{"name": "C", "octave": 6}]},
        {"task_index": 0, "answers": [{"name": "C", "octave": "4"}]},
        {"task_index": 0, "answers": [{"name": "C"}]},
        {"task_index": 0, "answers": []},
        {"task_index": 0, "answers": [{"name": "C", "octave": 4}] * 5},
        {"task_index": 0},
    ],
)
def test_input_validation(payload: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        SubmitTaskBody.model_validate(payload)


def test_first_task_is_issued(
    robustness_database: Database, robustness_settings: Settings
) -> None:
    round_id = new_round(robustness_database, robustness_settings)
    with robustness_database.session() as session:
        attempts = list(
            session.scalars(
                select(TaskAttempt)
                .where(TaskAttempt.round_id == round_id)
                .order_by(TaskAttempt.task_index)
            )
        )
        assert attempts[0].issued_at is not None
        assert all(attempt.issued_at is None for attempt in attempts[1:])
        task = task_payload(attempts[0], "easy", attempts[0].issued_at)
        assert task["time_limit_ms"] == 13000
        assert task["server_time"] == attempts[0].issued_at.isoformat()
        assert datetime.fromisoformat(str(task["deadline_at"])) == (
            attempts[0].issued_at + timedelta(seconds=13)
        )


def test_unissued_task_rejected(
    robustness_database: Database, robustness_settings: Settings
) -> None:
    round_id = new_round(robustness_database, robustness_settings)
    with pytest.raises(ServiceError):
        submit(robustness_database, robustness_settings, round_id, 2)


def test_server_late_answer_reports_cached_timeout(
    robustness_database: Database, robustness_settings: Settings
) -> None:
    round_id = new_round(robustness_database, robustness_settings)
    with robustness_database.session() as session, session.begin():
        attempt = session.scalar(
            select(TaskAttempt).where(
                TaskAttempt.round_id == round_id, TaskAttempt.task_index == 0
            )
        )
        assert attempt is not None and attempt.issued_at is not None
        notes = attempt.expected_notes
        assert isinstance(notes, list)
        late = attempt.issued_at + timedelta(
            seconds=13, milliseconds=robustness_settings.avatar_gen_grace_ms + 1
        )
        response = submit_task(
            session, round_id, 0, notes, False, late, robustness_settings
        )
        assert response["timed_out"] is True
        assert response["is_correct"] is False
        assert response["score_delta"] == -1
    with robustness_database.session() as session, session.begin():
        replay = submit_task(
            session,
            round_id,
            0,
            None,
            True,
            late + timedelta(days=1),
            robustness_settings,
        )
        assert replay == response
        assert replay["timed_out"] is True


def test_deadlines_and_replay(
    robustness_database: Database, robustness_settings: Settings
) -> None:
    round_id = new_round(robustness_database, robustness_settings)
    response = submit(robustness_database, robustness_settings, round_id, 0)
    next_task = response["next_task"]
    assert isinstance(next_task, dict)
    issued = datetime.fromisoformat(next_task["issued_at"])
    assert "server_time" in next_task
    deadline = datetime.fromisoformat(next_task["deadline_at"])
    assert deadline - issued == timedelta(milliseconds=next_task["time_limit_ms"])
    with robustness_database.session() as session:
        attempt = session.scalar(
            select(TaskAttempt).where(
                TaskAttempt.round_id == round_id, TaskAttempt.task_index == 0
            )
        )
        assert attempt is not None and attempt.submitted_at is not None
        assert issued - attempt.submitted_at == timedelta(
            milliseconds=robustness_settings.game_feedback_ms
        )
    with robustness_database.session() as session, session.begin():
        replay = submit_task(
            session,
            round_id,
            0,
            None,
            True,
            deadline + timedelta(days=1),
            robustness_settings,
        )
        assert replay == response
    with robustness_database.session() as session, session.begin():
        with pytest.raises(ServiceError):
            submit_task(
                session,
                round_id,
                1,
                None,
                True,
                issued - timedelta(milliseconds=1),
                robustness_settings,
            )
    assert submit(robustness_database, robustness_settings, round_id, 0) == response


@pytest.mark.parametrize("answers", [None, [], [{}], [{"name": "X", "octave": 4}]])
def test_service_invalid_answers_are_errors(
    robustness_database: Database,
    robustness_settings: Settings,
    answers: list[dict[str, object]] | None,
) -> None:
    round_id = new_round(robustness_database, robustness_settings, note_count=2)
    with robustness_database.session() as session, session.begin():
        with pytest.raises(ServiceError):
            submit_task(
                session,
                round_id,
                0,
                answers,
                False,
                datetime.now(UTC),
                robustness_settings,
            )


def test_floor_and_final_replay(
    robustness_database: Database, robustness_settings: Settings
) -> None:
    round_id = new_round(robustness_database, robustness_settings)
    for index in range(7):
        response = submit(
            robustness_database, robustness_settings, round_id, index, correct=False
        )
        if index == 0:
            first_response = response
    result = response["result"]
    assert isinstance(result, dict)
    assert result["score"] == 0
    assert result["score_bonus"] == 1
    assert result["average_score"] is None
    assert result["practice_hint"] is None
    assert "first_round" in result["new_achievements"]
    assert submit(robustness_database, robustness_settings, round_id, 6) == response
    assert (
        submit(robustness_database, robustness_settings, round_id, 0) == first_response
    )
    with robustness_database.session() as session:
        rnd = session.get(Round, round_id)
        last = session.scalar(
            select(TaskAttempt).where(
                TaskAttempt.round_id == round_id, TaskAttempt.task_index == 6
            )
        )
        assert rnd is not None and last is not None
        assert rnd.completed_at == last.submitted_at
        assert last.submit_response == response


@pytest.mark.parametrize("rules_version,correct", [(1, False), (2, True)])
def test_legacy_octave_scoring(
    robustness_database: Database,
    robustness_settings: Settings,
    rules_version: int,
    correct: bool,
) -> None:
    round_id = new_round(robustness_database, robustness_settings)
    with robustness_database.session() as session, session.begin():
        rnd = session.get(Round, round_id)
        assert rnd is not None
        rnd.rules_version = rules_version
        attempt = session.scalar(
            select(TaskAttempt).where(
                TaskAttempt.round_id == round_id, TaskAttempt.task_index == 0
            )
        )
        assert attempt is not None
        attempt.expected_notes = cast(dict[str, object], [{"name": "C", "octave": 4}])
        response = submit_task(
            session,
            round_id,
            0,
            [{"name": "C", "octave": 3}],
            False,
            datetime.now(UTC),
            robustness_settings,
        )
        assert response["is_correct"] is correct


def test_assistance_bonus_is_applied_before_floor_and_hint_is_structured(
    robustness_database: Database, robustness_settings: Settings
) -> None:
    round_id = new_round(robustness_database, robustness_settings)
    with robustness_database.session() as session, session.begin():
        rnd = session.get(Round, round_id)
        assert rnd is not None
        rnd.show_sound_hint = False
        rnd.show_correct_answer = False
        for seeded_attempt in session.scalars(
            select(TaskAttempt).where(TaskAttempt.round_id == round_id)
        ):
            seeded_attempt.expected_notes = cast(
                dict[str, object], [{"name": "C", "octave": 4}]
            )
    for index in range(3):
        submit(robustness_database, robustness_settings, round_id, index)
    for index in range(3, 7):
        with robustness_database.session() as session, session.begin():
            attempt = session.scalar(
                select(TaskAttempt).where(
                    TaskAttempt.round_id == round_id, TaskAttempt.task_index == index
                )
            )
            assert attempt is not None and attempt.issued_at is not None
            response = submit_task(
                session,
                round_id,
                index,
                [{"name": "D", "octave": 4}],
                False,
                max(datetime.now(UTC), attempt.issued_at),
                robustness_settings,
            )
    result = response["result"]
    assert isinstance(result, dict)
    assert result["score"] == 1
    assert result["score_bonus"] == 2
    assert result["xp_gained"] == 3
    assert result["is_win"] is False
    assert result["practice_hint"] == {"expected": "C", "given": "D"}


@pytest.mark.parametrize("second_correct", [1, 7])
def test_concurrent_rounds_preserve_xp(
    robustness_database: Database,
    robustness_settings: Settings,
    second_correct: int,
) -> None:
    round_id = new_round(robustness_database, robustness_settings)
    with robustness_database.session() as session, session.begin():
        first = session.get(Round, round_id)
        assert first is not None
        second, _ = create_round(
            session,
            first.player_id,
            first.season_id,
            "easy",
            1,
            "letters",
            robustness_settings,
        )
        second_id = second.id
        player_id = first.player_id
    for index in range(6):
        submit(robustness_database, robustness_settings, round_id, index)
        submit(
            robustness_database,
            robustness_settings,
            second_id,
            index,
            correct=index < second_correct,
        )
    ready = Barrier(2)

    def finish(identifier: int) -> dict[str, object]:
        with robustness_database.session() as session, session.begin():
            stale_player = session.get(Player, player_id)
            assert stale_player is not None and stale_player.xp == 145
            attempt = session.scalar(
                select(TaskAttempt).where(
                    TaskAttempt.round_id == identifier, TaskAttempt.task_index == 6
                )
            )
            assert attempt is not None and attempt.issued_at is not None
            ready.wait(timeout=10)
            notes = attempt.expected_notes
            assert isinstance(notes, list)
            timed_out = identifier == second_id and second_correct < 7
            return submit_task(
                session,
                identifier,
                6,
                None if timed_out else notes,
                timed_out,
                max(datetime.now(UTC), attempt.issued_at),
                robustness_settings,
            )

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [
            pool.submit(finish, identifier) for identifier in (round_id, second_id)
        ]
        results = [future.result(timeout=20) for future in futures]
    assert all(isinstance(response["result"], dict) for response in results)
    second_xp = 12 if second_correct == 7 else 1
    for response, expected_xp in zip(results, (12, second_xp), strict=True):
        result = response["result"]
        assert isinstance(result, dict)
        assert result["xp_gained"] == expected_xp
    with robustness_database.session() as session:
        player = session.get(Player, player_id)
        assert player is not None and player.xp == 145 + 12 + second_xp


def test_average_score_excludes_current_and_other_round_options(
    robustness_database: Database, robustness_settings: Settings
) -> None:
    round_id = new_round(robustness_database, robustness_settings)
    with robustness_database.session() as session, session.begin():
        current = session.get(Round, round_id)
        assert current is not None
        for score, difficulty, count in (
            (-3, "easy", 1),
            (5, "easy", 1),
            (7, "hard", 1),
            (7, "easy", 2),
        ):
            session.add(
                Round(
                    player_id=current.player_id,
                    season_id=current.season_id,
                    difficulty=difficulty,
                    note_count=count,
                    note_naming="letters",
                    status="completed",
                    score=score,
                    correct_count=3,
                    completed_at=datetime.now(UTC),
                    expires_at=current.expires_at,
                )
            )
    for index in range(7):
        response = submit(
            robustness_database, robustness_settings, round_id, index, correct=False
        )
    result = response["result"]
    assert isinstance(result, dict)
    assert result["average_score"] == 2.5
    assert submit(robustness_database, robustness_settings, round_id, 6) == response
