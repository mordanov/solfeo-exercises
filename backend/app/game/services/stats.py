from typing import cast

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.game.models import Round, TaskAttempt

NOTE_NAMES = ["C", "D", "E", "F", "G", "A", "B"]


def get_stats(session: Session, player_id: int, season_id: int) -> dict[str, object]:
    rows = session.execute(
        select(
            Round.difficulty,
            Round.note_count,
            func.count(Round.id).label("rounds"),
            func.sum(Round.correct_count).label("total_correct"),
            func.avg(Round.score).label("avg_score"),
        )
        .where(
            Round.player_id == player_id,
            Round.season_id == season_id,
            Round.status == "completed",
        )
        .group_by(Round.difficulty, Round.note_count)
    ).fetchall()

    matrix: dict[str, object] = {}
    for diff, nc, rounds, correct, avg_score in rows:
        d = cast(dict[str, object], matrix.setdefault(diff, {}))
        d[str(nc)] = {
            "rounds": rounds,
            "total_correct": correct or 0,
            "avg_score": round(float(avg_score), 2) if avg_score else 0.0,
        }
    return matrix


def get_confusion(
    session: Session, player_id: int, season_id: int
) -> dict[str, object]:
    attempts = list(
        session.scalars(
            select(TaskAttempt)
            .join(Round, Round.id == TaskAttempt.round_id)
            .where(Round.player_id == player_id, TaskAttempt.season_id == season_id)
        )
    )
    heatmap: dict[str, dict[str, int]] = {
        n: {m: 0 for m in NOTE_NAMES} for n in NOTE_NAMES
    }
    top: dict[tuple[str, str], int] = {}
    for a in attempts:
        if a.is_correct or a.timed_out or not a.given_notes:
            continue
        expected = cast(list[dict[str, object]], a.expected_notes)
        given = cast(list[dict[str, object]], a.given_notes)
        for e, g in zip(expected, given, strict=False):
            en, gn = str(e["name"]), str(g["name"])
            if en != gn and en in heatmap and gn in NOTE_NAMES:
                heatmap[en][gn] += 1
                key = (en, gn)
                top[key] = top.get(key, 0) + 1

    top3 = sorted(top.items(), key=lambda x: -x[1])[:3]
    return {
        "heatmap": heatmap,
        "top_confusions": [
            {"expected": k[0], "given": k[1], "count": v} for k, v in top3
        ],
    }
