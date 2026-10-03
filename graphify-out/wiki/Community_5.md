# Community 5

> 63 nodes · cohesion 0.06

## Key Concepts

- **generate()** (16 connections) — `worker/generate_spoken.py`
- **test_exercises.py** (14 connections) — `backend/tests/test_exercises.py`
- **create_exercise()** (14 connections) — `backend/tests/test_exercises.py`
- **prepare_media()** (12 connections) — `backend/app/services/media.py`
- **test_listening.py** (12 connections) — `backend/tests/test_listening.py`
- **audio_exercise()** (11 connections) — `backend/tests/test_listening.py`
- **event()** (11 connections) — `backend/tests/test_listening.py`
- **generate_spoken.py** (11 connections) — `worker/generate_spoken.py`
- **test_spoken_generation.py** (10 connections) — `backend/tests/test_spoken_generation.py`
- **test_omr.py** (8 connections) — `backend/tests/test_omr.py`
- **run_media()** (7 connections) — `backend/app/services/media.py`
- **GenerationError** (7 connections) — `worker/generate_spoken.py`
- **write_timings()** (7 connections) — `worker/generate_spoken.py`
- **verify()** (7 connections) — `worker/generate_spoken.py`
- **test_navigation_persistence_random_and_deleted_pointer()** (5 connections) — `backend/tests/test_listening.py`
- **validate_audio()** (5 connections) — `worker/generate_spoken.py`
- **duration()** (4 connections) — `backend/app/services/media.py`
- **wav()** (4 connections) — `backend/tests/test_spoken_generation.py`
- **test_partial_generation_resumes_without_rebuying_completed_clips()** (4 connections) — `backend/tests/test_spoken_generation.py`
- **test_session_ownership_conflicts_and_image_only()** (4 connections) — `backend/tests/test_listening.py`
- **main()** (4 connections) — `worker/generate_spoken.py`
- **media.py** (3 connections) — `backend/app/services/media.py`
- **test_retry_budget_and_text_edit_preserve_job()** (3 connections) — `backend/tests/test_omr.py`
- **test_timings_cover_existing_aac_frames_without_rewriting_clips()** (3 connections) — `backend/tests/test_spoken_generation.py`
- **test_real_aac_conversion_resumes_and_verifies_all_clips()** (3 connections) — `backend/tests/test_spoken_generation.py`
- *... and 38 more nodes in this community*

## Relationships

- [[Community 7]] (8 shared connections)
- [[Community 40]] (5 shared connections)
- [[Community 3]] (3 shared connections)
- [[Community 4]] (1 shared connections)
- [[Community 68]] (1 shared connections)
- [[Community 41]] (1 shared connections)
- [[Community 35]] (1 shared connections)

## Source Files

- `backend/app/services/media.py`
- `backend/tests/test_exercises.py`
- `backend/tests/test_listening.py`
- `backend/tests/test_omr.py`
- `backend/tests/test_spoken_generation.py`
- `worker/generate_spoken.py`

## Audit Trail

- EXTRACTED: 206 (77%)
- INFERRED: 60 (23%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [[index]] to navigate.*