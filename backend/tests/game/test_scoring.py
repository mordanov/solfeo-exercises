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


def test_note_only_rules_ignore_octaves_but_preserve_names_and_order() -> None:
    expected = [{"name": "E", "octave": 2}, {"name": "C", "octave": 4}]
    given = [{"name": "E", "octave": 4}, {"name": "C", "octave": 3}]
    assert score_task(expected, given, note_only=True) == 1
    assert score_task(expected, given[::-1], note_only=True) == -1
    assert score_task(expected, given[:1], note_only=True) == -1


def test_legacy_rules_still_require_the_written_octave() -> None:
    assert score_task([{"name": "E", "octave": 4}], [{"name": "E", "octave": 5}]) == -1
