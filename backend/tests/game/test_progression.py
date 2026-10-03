from app.game.config import LEVEL_THRESHOLDS, TROPHY_THRESHOLDS
from app.game.services.rounds import _compute_level


def test_level_zero_at_zero_xp() -> None:
    assert _compute_level(0, LEVEL_THRESHOLDS) == 0


def test_level_advances_at_threshold() -> None:
    for i, threshold in enumerate(LEVEL_THRESHOLDS):
        assert _compute_level(threshold, LEVEL_THRESHOLDS) == i


def test_level_does_not_exceed_max() -> None:
    assert _compute_level(99999, LEVEL_THRESHOLDS) == len(LEVEL_THRESHOLDS) - 1


def test_level_between_thresholds() -> None:
    # XP between level 1 (30) and level 2 (80) stays at level 1
    assert _compute_level(50, LEVEL_THRESHOLDS) == 1


def test_trophy_thresholds_sorted() -> None:
    assert TROPHY_THRESHOLDS == sorted(TROPHY_THRESHOLDS)
