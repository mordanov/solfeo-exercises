from datetime import UTC, datetime, timedelta

from app.game.config import NOTE_RANGE, TASKS_PER_ROUND
from app.game.services.rounds import check_timeout, generate_tasks, time_limit_s


def test_generate_tasks_count() -> None:
    tasks = generate_tasks("easy", 2, "solfege")
    assert len(tasks) == TASKS_PER_ROUND


def test_each_clef_has_exactly_thirteen_pitches_matching_the_reference_staff() -> None:
    assert (
        NOTE_RANGE["treble"]
        == [(name, octave) for octave in (4, 5) for name in "CDEFGAB"][:-1]
    )
    assert (
        NOTE_RANGE["bass"]
        == [(name, octave) for octave in (2, 3, 4) for name in "CDEFGAB"][2:15]
    )


def test_generate_tasks_clef_is_treble_or_bass() -> None:
    tasks = generate_tasks("easy", 1, "letters")
    assert all(t["clef"] in ("treble", "bass") for t in tasks)


def test_generate_tasks_notes_in_range() -> None:
    tasks = generate_tasks("hard", 4, "letters")
    for task in tasks:
        clef = str(task["clef"])
        valid = {(n, o) for n, o in NOTE_RANGE[clef]}
        for note in task["notes"]:  # type: ignore[attr-defined]
            assert (note["name"], note["octave"]) in valid, (
                f"{note} not in {clef} range"
            )


def test_generate_tasks_no_immediate_repeat() -> None:
    for _ in range(10):
        tasks = generate_tasks("medium", 2, "letters")
        for i in range(1, len(tasks)):
            assert (
                tasks[i]["notes"] != tasks[i - 1]["notes"]
                or tasks[i]["clef"] != tasks[i - 1]["clef"]
            )


def test_time_limit_s() -> None:
    assert time_limit_s("easy") == 13
    assert time_limit_s("medium") == 10
    assert time_limit_s("hard") == 7


def test_check_timeout_within_grace() -> None:
    issued = datetime.now(UTC)
    submitted = issued + timedelta(seconds=13.4)  # 400ms over 13s limit, grace=500ms
    assert check_timeout(issued, submitted, "easy", grace_ms=500) is False


def test_check_timeout_over_grace() -> None:
    issued = datetime.now(UTC)
    submitted = issued + timedelta(seconds=14.0)  # 1000ms over, grace=500ms
    assert check_timeout(issued, submitted, "easy", grace_ms=500) is True
