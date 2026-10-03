# Community 29

> 22 nodes · cohesion 0.23

## Key Concepts

- **test_bot.py** (20 connections) — `prototypes/telegram/tests/test_bot.py`
- **config()** (19 connections) — `prototypes/telegram/tests/test_bot.py`
- **Bot** (17 connections) — `prototypes/telegram/bot.py`
- **update()** (8 connections) — `prototypes/telegram/tests/test_bot.py`
- **test_downloads_authorized_attachments_and_replies_after_save()** (4 connections) — `prototypes/telegram/tests/test_bot.py`
- **test_denies_unauthorized_sources_without_api_calls()** (4 connections) — `prototypes/telegram/tests/test_bot.py`
- **test_rejects_known_oversized_file_without_downloading()** (4 connections) — `prototypes/telegram/tests/test_bot.py`
- **test_limits_actual_download_and_removes_partial_file()** (4 connections) — `prototypes/telegram/tests/test_bot.py`
- **test_storage_capacity_rejects_without_downloading()** (4 connections) — `prototypes/telegram/tests/test_bot.py`
- **test_invalid_media_does_not_leave_files_or_claim_success()** (4 connections) — `prototypes/telegram/tests/test_bot.py`
- **test_does_not_advance_offset_when_reply_fails_and_does_not_resave()** (3 connections) — `prototypes/telegram/tests/test_bot.py`
- **test_persists_offset_only_after_processing()** (3 connections) — `prototypes/telegram/tests/test_bot.py`
- **test_text_and_links_are_not_downloaded()** (3 connections) — `prototypes/telegram/tests/test_bot.py`
- **test_refuses_corrupt_offset_instead_of_replaying_messages()** (3 connections) — `prototypes/telegram/tests/test_bot.py`
- **test_requires_token_and_nonempty_numeric_allowlist()** (2 connections) — `prototypes/telegram/tests/test_bot.py`
- **test_config_errors_do_not_reveal_token()** (2 connections) — `prototypes/telegram/tests/test_bot.py`
- **test_rejects_unsafe_telegram_file_paths()** (2 connections) — `prototypes/telegram/tests/test_bot.py`
- **test_startup_checks_identity_and_refuses_existing_webhook()** (2 connections) — `prototypes/telegram/tests/test_bot.py`
- **test_rate_limit_preserves_retry_after_without_exposing_api_body()** (2 connections) — `prototypes/telegram/tests/test_bot.py`
- **test_does_not_follow_file_redirects()** (2 connections) — `prototypes/telegram/tests/test_bot.py`
- **test_rejects_incomplete_download()** (2 connections) — `prototypes/telegram/tests/test_bot.py`
- **test_bot_texts_have_identical_nonempty_translation_keys()** (1 connections) — `prototypes/telegram/tests/test_bot.py`

## Relationships

- [[Community 27]] (5 shared connections)
- [[Community 49]] (1 shared connections)
- [[Community 117]] (1 shared connections)

## Source Files

- `prototypes/telegram/bot.py`
- `prototypes/telegram/tests/test_bot.py`

## Audit Trail

- EXTRACTED: 95 (83%)
- INFERRED: 20 (17%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [[index]] to navigate.*