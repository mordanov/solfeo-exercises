# Community 46

> 18 nodes · cohesion 0.17

## Key Concepts

- **AudiverisEngine** (8 connections) — `backend/app/services/omr_engine.py`
- **read_export()** (7 connections) — `backend/app/services/omr_engine.py`
- **test_omr_engine.py** (7 connections) — `backend/tests/test_omr_engine.py`
- **main()** (6 connections) — `worker/omr.py`
- **OmrEngine** (5 connections) — `backend/app/services/omr_engine.py`
- **.recognize()** (4 connections) — `backend/app/services/omr_engine.py`
- **omr.py** (3 connections) — `worker/omr.py`
- **test_plain_and_compressed_exports()** (2 connections) — `backend/tests/test_omr_engine.py`
- **test_archive_traversal_and_size_limit()** (2 connections) — `backend/tests/test_omr_engine.py`
- **test_no_score_and_ambiguous_export()** (2 connections) — `backend/tests/test_omr_engine.py`
- **test_authored_score_fixtures_are_supported()** (2 connections) — `backend/tests/test_omr_engine.py`
- **test_system_indentation_does_not_split_one_exercise()** (2 connections) — `backend/tests/test_omr_engine.py`
- **test_faint_staff_retry_is_bounded_and_uses_fresh_output()** (2 connections) — `backend/tests/test_omr_engine.py`
- **test_unrelated_failures_do_not_trigger_faint_staff_retry()** (2 connections) — `backend/tests/test_omr_engine.py`
- **cycle()** (2 connections) — `worker/omr.py`
- **healthy()** (2 connections) — `worker/omr.py`
- **Protocol** (1 connections)
- **.__init__()** (1 connections) — `backend/app/services/omr_engine.py`

## Relationships

- [[Community 40]] (5 shared connections)
- [[Community 95]] (2 shared connections)
- [[Community 19]] (1 shared connections)

## Source Files

- `backend/app/services/omr_engine.py`
- `backend/tests/test_omr_engine.py`
- `worker/omr.py`

## Audit Trail

- EXTRACTED: 38 (63%)
- INFERRED: 22 (37%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [[index]] to navigate.*