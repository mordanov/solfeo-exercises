# Decisions

Format: date, decision, reason. Do not reverse a decision without asking the owner.

- <date>: Job queue is in Postgres (SKIP LOCKED), no Redis. Reason: fewer services.
- <date>: Audio is stored as AAC in .m4a. Reason: Chrome and Safari both play it.
- <date>: Passwords use bcrypt or scrypt. Reason: the owner wants simple auth, plaintext is not allowed.
- <date>: The original image is always kept. Reason: needed for OMR review and as a fallback.
- <date>: Sync or async SQLAlchemy: <decide in PHASE 0>.
- <date>: CSRF method: <decide in PHASE 1>.
