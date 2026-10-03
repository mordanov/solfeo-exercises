# Community 21

> 26 nodes · cohesion 0.12

## Key Concepts

- **test_database.py** (19 connections) — `backend/tests/test_database.py`
- **Database** (8 connections) — `backend/app/database.py`
- **Probe** (8 connections) — `backend/tests/test_database.py`
- **count_rows()** (6 connections) — `backend/tests/test_database.py`
- **ProbeBase** (5 connections) — `backend/tests/test_database.py`
- **test_explicit_transaction_commits()** (3 connections) — `backend/tests/test_database.py`
- **test_closing_session_does_not_commit()** (3 connections) — `backend/tests/test_database.py`
- **test_exception_rolls_back_and_does_not_poison_next_session()** (3 connections) — `backend/tests/test_database.py`
- **test_database_error_rolls_back()** (3 connections) — `backend/tests/test_database.py`
- **database.py** (2 connections) — `backend/app/database.py`
- **DeclarativeBase** (2 connections)
- **database()** (2 connections) — `backend/tests/test_database.py`
- **migration_config()** (2 connections) — `backend/tests/test_database.py`
- **test_migration_upgrade_repeat_downgrade_and_upgrade()** (2 connections) — `backend/tests/test_database.py`
- **test_failed_connection_is_not_hidden()** (2 connections) — `backend/tests/test_database.py`
- **test_dependency_rolls_back_a_failed_request()** (2 connections) — `backend/tests/test_database.py`
- **.__init__()** (1 connections) — `backend/app/database.py`
- **session()** (1 connections) — `backend/app/database.py`
- **.close()** (1 connections) — `backend/app/database.py`
- **anyio_backend()** (1 connections) — `backend/tests/test_database.py`
- **database_settings()** (1 connections) — `backend/tests/test_database.py`
- **test_application_owns_database_and_dependency_closes_sessions()** (1 connections) — `backend/tests/test_database.py`
- **test_startup_fails_if_emergency_sync_cannot_reach_database()** (1 connections) — `backend/tests/test_database.py`
- **test_password_with_url_characters_is_not_interpolated()** (1 connections) — `backend/tests/test_database.py`
- **test_invalid_database_configuration_is_rejected()** (1 connections) — `backend/tests/test_database.py`
- *... and 1 more nodes in this community*

## Relationships

- [[Community 40]] (4 shared connections)
- [[Community 24]] (1 shared connections)
- [[Community 41]] (1 shared connections)

## Source Files

- `backend/app/database.py`
- `backend/tests/test_database.py`

## Audit Trail

- EXTRACTED: 73 (89%)
- INFERRED: 9 (11%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [[index]] to navigate.*