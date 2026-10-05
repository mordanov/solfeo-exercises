from datetime import timedelta

from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from app.game.config import LEVEL_THRESHOLDS, WIN_THRESHOLD
from app.game.models import AchievementAwarded, Player, Round, TaskAttempt
from app.settings import Settings

ACHIEVEMENT_CODES = (
    "first_round",
    "first_win",
    "perfect_round",
    "correct_streak_10",
    "notes_100",
    "note_rainbow",
    "treble_25",
    "bass_25",
    "both_clefs",
    "duet",
    "trio",
    "quartet",
    "all_difficulties",
    "independent_win",
    "days_streak_3",
    "days_7",
    "level_2",
    "level_5",
    "wins_10",
    "welcome_back",
)


def evaluate_achievements(
    session: Session, player: Player, current_round: Round, settings: Settings
) -> list[str]:
    session.flush()
    completed = [Round.player_id == player.id, Round.status == "completed"]
    total = (
        session.scalar(select(func.count()).select_from(Round).where(*completed)) or 0
    )
    wins = (
        session.scalar(
            select(func.count())
            .select_from(Round)
            .where(*completed, Round.correct_count >= WIN_THRESHOLD)
        )
        or 0
    )
    perfect_counts = set(
        session.scalars(
            select(Round.note_count)
            .where(*completed, Round.correct_count == 7)
            .distinct()
        )
    )
    difficulties = set(
        session.scalars(
            select(Round.difficulty)
            .where(*completed, Round.correct_count >= WIN_THRESHOLD)
            .distinct()
        )
    )
    independent = session.scalar(
        select(Round.id)
        .where(
            *completed,
            Round.correct_count >= WIN_THRESHOLD,
            Round.show_sound_hint.is_(False),
            Round.show_correct_answer.is_(False),
        )
        .limit(1)
    )
    clefs: dict[str, int] = {
        clef: count
        for clef, count in session.execute(
            select(TaskAttempt.clef, func.count())
            .join(Round, Round.id == TaskAttempt.round_id)
            .where(*completed, TaskAttempt.is_correct.is_(True))
            .group_by(TaskAttempt.clef)
        ).all()
    }
    both = (
        len(
            set(
                session.scalars(
                    select(TaskAttempt.clef).where(
                        TaskAttempt.round_id == current_round.id,
                        TaskAttempt.is_correct.is_(True),
                    )
                )
            )
        )
        == 2
        and (current_round.correct_count or 0) >= WIN_THRESHOLD
    )
    notes: dict[str, int] = {
        str(name): int(count)
        for name, count in session.execute(
            text("""
        SELECT expected.note->>'name', count(*)
        FROM task_attempts AS attempt
        JOIN rounds AS round ON round.id = attempt.round_id
        CROSS JOIN LATERAL jsonb_array_elements(attempt.expected_notes)
            WITH ORDINALITY AS expected(note, position)
        JOIN LATERAL jsonb_array_elements(NULLIF(attempt.given_notes, 'null'::jsonb))
            WITH ORDINALITY AS given(note, position)
            ON expected.position = given.position
        WHERE round.player_id = :player_id AND round.status = 'completed'
          AND NOT attempt.timed_out
          AND expected.note->>'name' = given.note->>'name'
          AND (round.rules_version >= 2
               OR expected.note->>'octave' = given.note->>'octave')
        GROUP BY expected.note->>'name'
    """),
            {"player_id": player.id},
        ).all()
    }
    streak = (
        session.scalar(
            text("""
        WITH ordered AS (
            SELECT attempt.is_correct,
              count(*) FILTER (WHERE NOT attempt.is_correct) OVER (
                ORDER BY round.completed_at, round.id, attempt.task_index
              ) AS group_id
            FROM task_attempts AS attempt
            JOIN rounds AS round ON round.id = attempt.round_id
            WHERE round.player_id = :player_id AND round.status = 'completed'
        )
        SELECT coalesce(max(correct_count), 0) FROM (
            SELECT count(*) AS correct_count FROM ordered
            WHERE is_correct GROUP BY group_id
        ) AS runs
    """),
            {"player_id": player.id},
        )
        or 0
    )
    local_day = func.date(
        func.timezone(settings.game_timezone, Round.completed_at)
    ).label("day")
    days = list(
        session.scalars(
            select(local_day)
            .where(*completed, Round.completed_at.is_not(None))
            .distinct()
            .order_by(local_day)
        )
    )
    three_days = any(
        days[index] + timedelta(days=2) == days[index + 2]
        for index in range(max(0, len(days) - 2))
    )
    welcome_back = any(
        following - previous >= timedelta(days=7)
        for previous, following in zip(days, days[1:], strict=False)
    )
    conditions = {
        "first_round": total >= 1,
        "first_win": wins >= 1,
        "perfect_round": bool(perfect_counts),
        "correct_streak_10": streak >= 10,
        "notes_100": sum(notes.values()) >= 100,
        "note_rainbow": all(notes.get(name, 0) >= 10 for name in "CDEFGAB"),
        "treble_25": clefs.get("treble", 0) >= 25,
        "bass_25": clefs.get("bass", 0) >= 25,
        "both_clefs": both,
        "duet": 2 in perfect_counts,
        "trio": 3 in perfect_counts,
        "quartet": 4 in perfect_counts,
        "all_difficulties": len(difficulties) == 3,
        "independent_win": independent is not None,
        "days_streak_3": three_days,
        "days_7": len(days) >= 7,
        "level_2": player.xp >= LEVEL_THRESHOLDS[1],
        "level_5": player.xp >= LEVEL_THRESHOLDS[4],
        "wins_10": wins >= 10,
        "welcome_back": welcome_back,
    }
    earned = set(
        session.scalars(
            select(AchievementAwarded.code).where(
                AchievementAwarded.player_id == player.id
            )
        )
    )
    added = [
        code for code in ACHIEVEMENT_CODES if conditions[code] and code not in earned
    ]
    session.add_all(
        AchievementAwarded(player_id=player.id, code=code) for code in added
    )
    session.flush()
    return added
