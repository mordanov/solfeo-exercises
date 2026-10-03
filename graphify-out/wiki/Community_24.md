# Community 24

> 24 nodes · cohesion 0.19

## Key Concepts

- **auth.py** (20 connections) — `backend/app/services/auth.py`
- **delete()** (9 connections) — `backend/app/api/exercises.py`
- **sync_emergency()** (8 connections) — `backend/app/services/auth.py`
- **require_password()** (7 connections) — `backend/app/services/auth.py`
- **login()** (7 connections) — `backend/app/services/auth.py`
- **change_password()** (7 connections) — `backend/app/services/auth.py`
- **hash_password()** (6 connections) — `backend/app/services/auth.py`
- **revoke_sessions()** (6 connections) — `backend/app/services/auth.py`
- **new_session()** (6 connections) — `backend/app/services/auth.py`
- **verify_password()** (5 connections) — `backend/app/services/auth.py`
- **Identity** (5 connections) — `backend/app/services/auth.py`
- **create_user()** (5 connections) — `backend/app/services/auth.py`
- **editable_user()** (5 connections) — `backend/app/services/auth.py`
- **reset_password()** (5 connections) — `backend/app/services/auth.py`
- **token_hash()** (4 connections) — `backend/app/services/auth.py`
- **administration_lock()** (4 connections) — `backend/app/services/auth.py`
- **authenticate()** (4 connections) — `backend/app/services/auth.py`
- **update_user()** (3 connections) — `backend/app/services/auth.py`
- **test_passwords_use_salted_scrypt()** (3 connections) — `backend/tests/test_auth.py`
- **test_emergency_create_reset_disable_and_reactivate()** (3 connections) — `backend/tests/test_auth.py`
- **logout()** (2 connections) — `backend/app/services/auth.py`
- **database()** (2 connections) — `backend/tests/test_auth.py`
- **update_settings()** (1 connections) — `backend/app/services/auth.py`
- **list_users()** (1 connections) — `backend/app/services/auth.py`

## Relationships

- [[Community 40]] (10 shared connections)
- [[Community 3]] (8 shared connections)
- [[Community 41]] (3 shared connections)
- [[Community 52]] (1 shared connections)
- [[Community 96]] (1 shared connections)
- [[Community 21]] (1 shared connections)

## Source Files

- `backend/app/api/exercises.py`
- `backend/app/services/auth.py`
- `backend/tests/test_auth.py`

## Audit Trail

- EXTRACTED: 99 (77%)
- INFERRED: 29 (23%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [[index]] to navigate.*