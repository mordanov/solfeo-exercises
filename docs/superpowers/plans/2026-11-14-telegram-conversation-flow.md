# Telegram Conversation Flow Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace "send audio → visit website" with an in-bot guided flow: audio downloads → bot asks chapter → bot asks exercise → bot auto-applies the import.

**Architecture:** Approach B (conversation after download). Audio queues and downloads normally (pending → ready). After download, `process_one` writes a chapter-selection message into `row.reply_text` and marks `link.conv_step="awaiting_chapter"`. Subsequent text replies in `receive()` walk the chapter → exercise selection; `_auto_apply()` applies the import. Web apply remains fully functional on any "ready" import.

**Tech Stack:** Python/FastAPI, SQLAlchemy ORM, PostgreSQL, Alembic, Telegram Bot API long-polling.

**Spec:** `docs/superpowers/specs/2026-11-14-telegram-conversation-flow-design.md`

## Global Constraints

- Ponytail: minimum code, no speculative abstractions, no new dependencies.
- Approach B: download proceeds unchanged; conversation starts after status="ready".
- No new status values on `TelegramUpdate` (existing check constraint kept).
- `chapters.create_chapter()` commits mid-transaction — must NOT be called; inline chapter creation: `SELECT nextval('chapter_number_seq')` + `Chapter(number=number)` + `session.flush()`.
- `exercises.lock()` must be called before any exercise create/update.
- Existing web `apply_import` must continue working on any "ready" import; it clears conv state on completion.
- `reply_text` overrides TEXTS lookup in worker; all existing TEXTS keys must remain.

## Review Focus

- **Stale conversation** (`conv_update_id` points to non-"ready" update): `receive()` must detect and clear conv state, replying `"stale_conversation"`. Tested in Task 3 Step 6.
- **New audio while conversation in progress**: `process_one` overwrites `link.conv_update_id` with the newer update; the older "ready" update remains claimable via web. No special code needed; covered implicitly in Task 3 Step 6.
- **Chapter with no exercises** (`awaiting_exercise` but chapter is empty): exercise list shows only "new"; a digit input is invalid. Tested in Task 3 Step 6.
- **Web apply clears bot conversation**: `apply_import()` must null out `link.conv_step/conv_chapter_id/conv_update_id`. Tested in Task 3 Step 12.
- **Invalid input during conversation** (non-digit, non-"new" text): must not crash; reply with "help". Tested in Task 3 Step 6.

---

### Task 1: DB Model Changes

**Files:**
- Modify: `backend/app/models/__init__.py`

**Interfaces:**
- Produces: `TelegramLink.conv_step: str | None`, `TelegramLink.conv_chapter_id: int | None`, `TelegramLink.conv_update_id: int | None`; `TelegramUpdate.chapter_id: int | None`, `TelegramUpdate.reply_text: str | None`

- [ ] **Step 1: Add three columns to `TelegramLink`**

After `sender_id` in `TelegramLink`:

```python
conv_step: Mapped[str | None] = mapped_column(String(20))
conv_chapter_id: Mapped[int | None] = mapped_column(ForeignKey("chapters.id"))
conv_update_id: Mapped[int | None] = mapped_column(BigInteger)
```

- [ ] **Step 2: Add two columns to `TelegramUpdate`**

After `notified` in `TelegramUpdate`:

```python
chapter_id: Mapped[int | None] = mapped_column(ForeignKey("chapters.id"))
reply_text: Mapped[str | None] = mapped_column(Text)
```

- [ ] **Step 3: Verify no import errors**

```bash
cd backend && python -c "from app.models import TelegramLink, TelegramUpdate; print('ok')"
```
Expected: `ok`

- [ ] **Step 4: Commit**

```bash
git add backend/app/models/__init__.py
git commit -m "feat(telegram): add conversation state columns to TelegramLink and TelegramUpdate

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

### Task 2: Migration

**Files:**
- Create: `backend/migrations/versions/0014_telegram_conversation.py`

**Interfaces:**
- Consumes: column definitions from Task 1

- [ ] **Step 1: Confirm `down_revision`**

The revision ID of `0013_exercise_chapters_and_listening_runs.py` is `"0013_exercise_chapters"`. Use that as `down_revision`.

- [ ] **Step 2: Create migration file**

```python
"""telegram conversation state

Revision ID: 0014
Revises: 0013_exercise_chapters
Create Date: 2026-11-14
"""
from alembic import op
import sqlalchemy as sa

revision = "0014"
down_revision = "0013_exercise_chapters"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("telegram_links", sa.Column("conv_step", sa.String(20), nullable=True))
    op.add_column("telegram_links", sa.Column("conv_chapter_id", sa.Integer(), nullable=True))
    op.add_column("telegram_links", sa.Column("conv_update_id", sa.BigInteger(), nullable=True))
    op.add_column("telegram_updates", sa.Column("chapter_id", sa.Integer(), nullable=True))
    op.add_column("telegram_updates", sa.Column("reply_text", sa.Text(), nullable=True))
    op.create_foreign_key(
        "fk_telegram_links_conv_chapter_id_chapters",
        "telegram_links", "chapters", ["conv_chapter_id"], ["id"],
    )
    op.create_foreign_key(
        "fk_telegram_updates_chapter_id_chapters",
        "telegram_updates", "chapters", ["chapter_id"], ["id"],
    )


def downgrade() -> None:
    op.drop_constraint("fk_telegram_updates_chapter_id_chapters", "telegram_updates", type_="foreignkey")
    op.drop_constraint("fk_telegram_links_conv_chapter_id_chapters", "telegram_links", type_="foreignkey")
    op.drop_column("telegram_updates", "reply_text")
    op.drop_column("telegram_updates", "chapter_id")
    op.drop_column("telegram_links", "conv_update_id")
    op.drop_column("telegram_links", "conv_chapter_id")
    op.drop_column("telegram_links", "conv_step")
```

- [ ] **Step 3: Run migration**

```bash
cd backend && alembic upgrade head
```
Expected: completes without errors.

- [ ] **Step 4: Test downgrade/upgrade round-trip**

```bash
cd backend && alembic downgrade -1 && alembic upgrade head
```
Expected: no errors.

- [ ] **Step 5: Commit**

```bash
git add backend/migrations/versions/0014_telegram_conversation.py
git commit -m "feat(telegram): migration 0014 — conversation state columns

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

### Task 3: Service Refactor

**Files:**
- Modify: `backend/app/services/telegram.py`
- Modify: `backend/tests/test_telegram.py`

**Interfaces:**
- Consumes: Task 1 columns
- Produces: `_auto_apply(session, target, chapter_id, exercise_id)` — acquires exercise lock, creates/updates exercise, sets `target.status="applied"` and `target.exercise_id`

- [ ] **Step 1: Write failing test — `process_one` sets chapter list**

Add to `backend/tests/test_telegram.py`:

```python
def test_process_one_sets_chapter_list_and_conv_step(session, settings, tmp_path):
    # arrange: linked user, one chapter, one pending update with a file_id
    ...
    process_one(session, settings, fake_download)
    session.expire_all()
    row = session.get(TelegramUpdate, update_id)
    link = session.get(TelegramLink, user_id)
    assert row.status == "ready"
    assert row.reply_text is not None
    assert "new" in row.reply_text.lower()
    assert row.notified is False
    assert link.conv_step == "awaiting_chapter"
    assert link.conv_update_id == update_id
    assert link.conv_chapter_id is None
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd backend && python -m pytest tests/test_telegram.py::test_process_one_sets_chapter_list_and_conv_step -v
```
Expected: FAIL (reply_text None, conv_step None)

- [ ] **Step 3: Add `_chapter_list_text` helper**

Add to `backend/app/services/telegram.py`:

```python
def _chapter_list_text(chapters: list, language: str) -> str:
```

Signature: takes a list of `Chapter` objects ordered by number and a language code; returns a formatted string. English example:

```
Select a chapter:
2 – Chapter 2
3 – Chapter 3
new – Create new chapter

Reply with a number or "new".
```

Use a small per-language dict of 4 static phrases (header, row format, new-option, footer). ru/es translations at implementer's discretion — keep them short and clear.

- [ ] **Step 4: Update `process_one` success path**

In `backend/app/services/telegram.py`, after `row.media_id, row.status, row.last_error = media.id, "ready", None`, replace:

```python
row.reply_code, row.notified = "ready", False
```

with:

```python
chapters = list(session.scalars(select(Chapter).order_by(Chapter.number)))
row.reply_text = _chapter_list_text(chapters, row.language)
row.reply_code = "received"
row.notified = False
binding.conv_step = "awaiting_chapter"
binding.conv_chapter_id = None
binding.conv_update_id = row.id
```

Add `Chapter` to the `from app.models import ...` line. `binding` is already in scope (fetched earlier in `process_one` for the access check).

- [ ] **Step 5: Run test to verify it passes**

```bash
cd backend && python -m pytest tests/test_telegram.py::test_process_one_sets_chapter_list_and_conv_step -v
```
Expected: PASS

- [ ] **Step 6: Write failing tests — `receive()` conv step handling**

Add these tests to `backend/tests/test_telegram.py`. Each needs a helper that builds a valid text-message payload for a linked user:

```python
def test_receive_awaiting_chapter_digit_selects_chapter(session, ...):
    # arrange: link.conv_step="awaiting_chapter", chapter with number=3 exists
    row = receive(session, text_payload(user_id=..., text="3"))
    link = session.get(TelegramLink, user_id)
    assert link.conv_step == "awaiting_exercise"
    assert link.conv_chapter_id == chapter.id
    assert row.reply_text is not None  # exercise list

def test_receive_awaiting_chapter_new_creates_chapter(session, ...):
    # arrange: link.conv_step="awaiting_chapter", no chapters
    before = session.scalar(select(func.count()).select_from(Chapter))
    receive(session, text_payload(user_id=..., text="new"))
    after = session.scalar(select(func.count()).select_from(Chapter))
    link = session.get(TelegramLink, user_id)
    assert after == before + 1
    assert link.conv_step == "awaiting_exercise"
    assert link.conv_chapter_id is not None

def test_receive_awaiting_chapter_invalid_input_replies_help(session, ...):
    # arrange: link.conv_step="awaiting_chapter"
    row = receive(session, text_payload(user_id=..., text="banana"))
    assert row.reply_code == "help"
    link = session.get(TelegramLink, user_id)
    assert link.conv_step == "awaiting_chapter"  # state unchanged

def test_receive_awaiting_exercise_new_auto_applies(session, ...):
    # arrange: link with conv_step="awaiting_exercise", conv_chapter_id set,
    #          conv_update_id pointing to a "ready" TelegramUpdate with media_id set
    row = receive(session, text_payload(user_id=..., text="new"))
    link = session.get(TelegramLink, user_id)
    assert link.conv_step is None
    assert link.conv_chapter_id is None
    assert link.conv_update_id is None
    assert row.reply_code == "applied_bot"
    ready = session.get(TelegramUpdate, ready_update_id)
    assert ready.status == "applied"
    assert ready.exercise_id is not None

def test_receive_awaiting_exercise_digit_applies_to_existing(session, ...):
    # arrange: chapter has 2 exercises; link conv_step="awaiting_exercise"
    row = receive(session, text_payload(user_id=..., text="1"))
    ready = session.get(TelegramUpdate, ready_update_id)
    assert ready.status == "applied"
    assert ready.exercise_id == exercise1.id

def test_receive_awaiting_exercise_digit_out_of_range(session, ...):
    # arrange: chapter has 1 exercise; text="9"
    row = receive(session, text_payload(user_id=..., text="9"))
    assert row.reply_code == "help"

def test_receive_stale_conv_clears_state(session, ...):
    # arrange: link.conv_step="awaiting_exercise", conv_update_id points to a "failed" update
    row = receive(session, text_payload(user_id=..., text="new"))
    link = session.get(TelegramLink, user_id)
    assert link.conv_step is None
    assert row.reply_code == "stale_conversation"
```

- [ ] **Step 7: Run tests to verify they fail**

```bash
cd backend && python -m pytest tests/test_telegram.py -k "awaiting_chapter or awaiting_exercise or stale_conv" -v
```
Expected: All FAIL

- [ ] **Step 8: Add `_exercise_list_text` helper**

```python
def _exercise_list_text(chapter_exercises: list, chapter_number: int, language: str) -> str:
```

Takes a list of `Exercise` objects and the chapter's number; returns formatted exercise selection message. English example:

```
Chapter 3 exercises:
1 – Exercise Title
2 – Another Exercise
new – Create new exercise

Reply with a number or "new".
```

Same per-language phrase dict pattern as `_chapter_list_text`.

- [ ] **Step 9: Add `_auto_apply` helper**

```python
def _auto_apply(
    session: Session, target: TelegramUpdate, chapter_id: int, exercise_id: int | None
) -> None:
    exercises.lock(session)
    exercise = exercises.get_exercise(session, exercise_id) if exercise_id else exercises.new_exercise(session)
    exercise.chapter_id = chapter_id
    exercise.title = target.title
    exercise.description = target.description
    exercise.audio_id = target.media_id
    session.add(exercise)
    session.flush()
    target.exercise_id = exercise.id
    target.status = "applied"
```

- [ ] **Step 10: Update `receive()` — suppress "received" notification on audio**

In the audio/voice/document branch, add `row.notified = True` so the worker does not send a "received" message (the chapter list from `process_one` arrives later):

```python
row.status = "pending"
row.notified = True   # chapter list sent by process_one after download
```

- [ ] **Step 11: Update `receive()` — add conv step handling**

In the `else` branch (after obtaining valid `binding` and `user`), before the existing `attachment = ...` check, insert:

```python
if binding.conv_step in ("awaiting_chapter", "awaiting_exercise") and not (message.audio or message.voice or message.document):
    _handle_chapter_reply(session, message.text.strip(), binding, row)  # if awaiting_chapter
    # or
    _handle_exercise_reply(session, message.text.strip(), binding, row, user)  # if awaiting_exercise
    session.add(row)
    session.commit()
    return row
```

Implement two private helpers (or inline — whichever is shorter):

**`_handle_chapter_reply(session, text, binding, row)`:**
1. If `text == "new"`: `number = session.execute(text_("SELECT nextval('chapter_number_seq')")).scalar_one(); chapter = Chapter(number=number); session.add(chapter); session.flush()`. Set `binding.conv_chapter_id = chapter.id`.
2. Elif `text.isdigit()`: query chapter with `Chapter.number == int(text)`. If not found: `row.reply_code = "help"; return`.
3. Else: `row.reply_code = "help"; return`.
4. Fetch exercises for `binding.conv_chapter_id` ordered by `(Exercise.position, Exercise.id)` where `deleted_at IS NULL`.
5. Fetch chapter for its `.number` (needed by `_exercise_list_text`).
6. `row.reply_text = _exercise_list_text(exs, chapter.number, row.language)`.
7. `binding.conv_step = "awaiting_exercise"`.

Note: the `text` built-in is shadowed by the SQLAlchemy import; use `text` from sqlalchemy as `text_` or keep the existing import name consistent with the file.

**`_handle_exercise_reply(session, text, binding, row, user)`:**
1. `target = session.scalar(select(TelegramUpdate).where(TelegramUpdate.id == binding.conv_update_id, TelegramUpdate.status == "ready", TelegramUpdate.user_id == user.id).with_for_update().execution_options(populate_existing=True))`.
2. If `target is None`: clear `binding.conv_step/conv_chapter_id/conv_update_id`; `row.reply_code = "stale_conversation"; return`.
3. `chapter_id = binding.conv_chapter_id`.
4. If `text == "new"`: `exercise_id = None`.
5. Elif `text.isdigit()`: `exs = list(session.scalars(select(Exercise).where(Exercise.chapter_id == chapter_id, Exercise.deleted_at.is_(None)).order_by(Exercise.position, Exercise.id)))`; `idx = int(text) - 1`; if `idx < 0 or idx >= len(exs)`: `row.reply_code = "help"; return`; `exercise_id = exs[idx].id`.
6. Else: `row.reply_code = "help"; return`.
7. `_auto_apply(session, target, chapter_id, exercise_id)`.
8. Clear `binding.conv_step/conv_chapter_id/conv_update_id`.
9. `row.reply_code = "applied_bot"`.

Add `Exercise` to `from app.models import ...` if not already there.

- [ ] **Step 12: Run conv step tests to verify they pass**

```bash
cd backend && python -m pytest tests/test_telegram.py -k "awaiting_chapter or awaiting_exercise or stale_conv" -v
```
Expected: All PASS

- [ ] **Step 13: Write failing test — `apply_import` clears conv state**

```python
def test_apply_import_via_web_clears_conv_state(session, ...):
    # arrange: link.conv_step="awaiting_chapter", conv_update_id set to a "ready" update
    apply_import(session, user_id, update_id, None, "title", "")
    session.expire_all()
    link = session.get(TelegramLink, user_id)
    assert link.conv_step is None
    assert link.conv_chapter_id is None
    assert link.conv_update_id is None
```

- [ ] **Step 14: Run test to verify it fails**

```bash
cd backend && python -m pytest tests/test_telegram.py::test_apply_import_via_web_clears_conv_state -v
```
Expected: FAIL (conv_step still set)

- [ ] **Step 15: Update `apply_import` to clear conv state**

In `apply_import`, before the final `session.commit()`:

```python
binding = session.get(TelegramLink, user_id)
if binding is not None:
    binding.conv_step = None
    binding.conv_chapter_id = None
    binding.conv_update_id = None
```

- [ ] **Step 16: Run test to verify it passes**

```bash
cd backend && python -m pytest tests/test_telegram.py::test_apply_import_via_web_clears_conv_state -v
```
Expected: PASS

- [ ] **Step 17: Run full Telegram test suite**

```bash
cd backend && python -m pytest tests/test_telegram.py -v
```
Expected: All PASS

- [ ] **Step 18: Commit**

```bash
git add backend/app/services/telegram.py backend/tests/test_telegram.py
git commit -m "feat(telegram): guided chapter/exercise selection in bot

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

### Task 4: Worker Update

**Files:**
- Modify: `worker/telegram.py`

**Interfaces:**
- Consumes: `TelegramUpdate.reply_text` (Task 1), `reply_code="applied_bot"` and `"stale_conversation"` (Task 3)

- [ ] **Step 1: Add new TEXTS entries to all three languages**

In `worker/telegram.py` TEXTS dict, add to `"en"`:
```python
"applied_bot": "Done! Exercise saved.",
"stale_conversation": "Session expired. Please send the audio again.",
```

Add to `"ru"`:
```python
"applied_bot": "Готово! Упражнение сохранено.",
"stale_conversation": "Сессия устарела. Пожалуйста, отправьте аудио снова.",
```

Add to `"es"`:
```python
"applied_bot": "¡Listo! Ejercicio guardado.",
"stale_conversation": "Sesión expirada. Por favor, envía el audio de nuevo.",
```

- [ ] **Step 2: Use `reply_text` in the reply loop**

In `cycle()`, replace:
```python
api.reply(row.chat_id, TEXTS[row.language][row.reply_code])
```
with:
```python
content = row.reply_text or TEXTS[row.language][row.reply_code]
api.reply(row.chat_id, content)
```

- [ ] **Step 3: Run integration tests**

```bash
cd backend && python -m pytest tests/test_telegram.py -v
```
Expected: All PASS

- [ ] **Step 4: Commit**

```bash
git add worker/telegram.py
git commit -m "feat(telegram): use reply_text in cycle, add applied_bot/stale_conversation texts

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

### Task 5: Test Comment Update

**Files:**
- Modify: `backend/tests/test_telegram.py`

- [ ] **Step 1: Update comment in duplicate-update test**

In `test_worker_restart_duplicate_update_and_real_api_transport`, find a comment referring to "ready notification" (or similar) and update it to describe the chapter list reply.

- [ ] **Step 2: Verify test still passes**

```bash
cd backend && python -m pytest tests/test_telegram.py::test_worker_restart_duplicate_update_and_real_api_transport -v
```
Expected: PASS

- [ ] **Step 3: Commit**

```bash
git add backend/tests/test_telegram.py
git commit -m "test(telegram): update comment for chapter list flow

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```
