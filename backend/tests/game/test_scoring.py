from app.game.services.rounds import score_task


def test_all_correct() -> None:
    expected = [{"name": "C", "octave": 4}, {"name": "E", "octave": 4}]
    given = [{"name": "C", "octave": 4}, {"name": "E", "octave": 4}]
    assert score_task(expected, given) == 1


def test_wrong_answer() -> None:
    expected = [{"name": "C", "octave": 4}]
    given = [{"name": "D", "octave": 4}]
    assert score_task(expected, given) == -1


def test_timeout() -> None:
    assert score_task([{"name": "C", "octave": 4}], None) == -1


def test_wrong_order() -> None:
    expected = [{"name": "C", "octave": 4}, {"name": "E", "octave": 4}]
    given = [{"name": "E", "octave": 4}, {"name": "C", "octave": 4}]
    assert score_task(expected, given) == -1
