from typing import cast

from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from app.game.config import WIN_THRESHOLD
from app.game.models import Round

NOTE_NAMES = ["C", "D", "E", "F", "G", "A", "B"]


def get_stats(session: Session, player_id: int, season_id: int) -> dict[str, object]:
    rows = session.execute(
        select(
            Round.difficulty,
            Round.note_count,
            func.count(Round.id).label("rounds"),
            func.sum(Round.correct_count).label("total_correct"),
            func.avg(Round.score).label("avg_score"),
            func.sum(Round.score).label("total_score"),
            func.count(Round.id)
            .filter(Round.correct_count >= WIN_THRESHOLD)
            .label("wins"),
        )
        .where(
            Round.player_id == player_id,
            Round.season_id == season_id,
            Round.status == "completed",
        )
        .group_by(Round.difficulty, Round.note_count)
    ).fetchall()

    matrix: dict[str, object] = {}
    for diff, nc, rounds, correct, avg_score, total_score, wins in rows:
        d = cast(dict[str, object], matrix.setdefault(diff, {}))
        d[str(nc)] = {
            "rounds": rounds,
            "total_correct": correct or 0,
            "avg_score": round(float(avg_score), 2) if avg_score else 0.0,
            "total_score": total_score or 0,
            "wins": wins,
            "win_rate": round(wins * 100 / rounds, 2),
        }
    return matrix


def get_confusion(
    session: Session, player_id: int, season_id: int, clef: str | None = None
) -> dict[str, object]:
    latest_round = session.scalar(
        select(Round.id)
        .where(
            Round.player_id == player_id,
            Round.season_id == season_id,
            Round.status == "completed",
        )
        .order_by(Round.completed_at.desc().nulls_last(), Round.id.desc())
        .limit(1)
    )
    rows = session.execute(
        text("""
            SELECT expected.note->>'name' AS expected_name,
                   given.note->>'name' AS given_name,
                   attempt.timed_out, count(*) AS occurrences,
                   count(*) FILTER (WHERE round.id = :latest_round) AS latest_count
            FROM task_attempts AS attempt
            JOIN rounds AS round ON round.id = attempt.round_id
            CROSS JOIN LATERAL jsonb_array_elements(attempt.expected_notes)
                WITH ORDINALITY AS expected(note, position)
            LEFT JOIN LATERAL jsonb_array_elements(
                NULLIF(attempt.given_notes, 'null'::jsonb)
            )
                WITH ORDINALITY AS given(note, position)
                ON expected.position = given.position
            WHERE round.player_id = :player_id
              AND round.status = 'completed'
              AND round.season_id = :season_id
              AND attempt.season_id = :season_id
              AND (CAST(:clef AS text) IS NULL OR attempt.clef = :clef)
              AND (attempt.timed_out OR (
                  NOT attempt.is_correct
                  AND expected.note->>'name' <> given.note->>'name'
              ))
            GROUP BY expected_name, given_name, attempt.timed_out
        """),
        {
            "player_id": player_id,
            "season_id": season_id,
            "clef": clef,
            "latest_round": latest_round,
        },
    )
    heatmap: dict[str, dict[str, int]] = {
        n: {m: 0 for m in NOTE_NAMES} for n in NOTE_NAMES
    }
    top: dict[tuple[str, str], int] = {}
    missed: dict[str, int] = {}
    round_top: dict[tuple[str, str], int] = {}
    for expected, given, timed_out, count, latest_count in rows:
        if timed_out and expected in NOTE_NAMES:
            missed[expected] = missed.get(expected, 0) + count
        elif expected in heatmap and given in NOTE_NAMES:
            heatmap[expected][given] += count
            key = (expected, given)
            top[key] = top.get(key, 0) + count
            if latest_count:
                round_top[key] = round_top.get(key, 0) + latest_count

    top3 = sorted(top.items(), key=lambda x: (-x[1], x[0]))[:3]
    return {
        "heatmap": heatmap,
        "top_confusions": [
            {"expected": k[0], "given": k[1], "count": v} for k, v in top3
        ],
        "round_top_confusions": [
            {"expected": pair[0], "given": pair[1], "count": count}
            for pair, count in sorted(
                round_top.items(), key=lambda item: (-item[1], item[0])
            )[:3]
        ],
        "missed_notes": [
            {"name": name, "count": count}
            for name, count in sorted(
                missed.items(), key=lambda item: (-item[1], item[0])
            )
        ],
    }
