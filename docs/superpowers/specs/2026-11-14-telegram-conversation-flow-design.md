# Telegram Conversation Flow — Design

**Intent:** Replace "send audio → go to website" with an in-bot guided flow: audio arrives → bot asks chapter → bot asks exercise → bot applies automatically.

**Why:** Manager workflow is cumbersome; going to the website after every upload breaks flow. Bot-guided apply completes the import without leaving Telegram.

**Goals:** Complete chapter + exercise selection inside Telegram; auto-apply the import on conversation completion; keep web apply as a fallback for any "ready" import.

**Non-goals:** Remove or break existing web apply endpoint; change exercise fields beyond chapter_id.

**Anti-goals:** Re-asking if user sends another audio before completing the first conversation (just reset state to latest).

**Constraints:** `create_chapter()` commits mid-transaction; must inline chapter creation instead. `process_one` is single-threaded with receive; no concurrent locking needed for conv state.

---

## Approaches

**A. Conversation before download** (status="collecting"): audio queued without download, bot asks chapter/exercise first, download starts only when conversation completes. Clean UX, longer wait between audio and "done". Breaks all existing tests (receive → process_one → apply pattern).

**B. Conversation after download** (chosen): audio queued immediately (status="pending"), download proceeds as before to status="ready". Bot then sends chapter list. User picks chapter → exercise → auto-apply. Web apply still works on "ready" imports. Test impact: minimal (minor comment update only).

Chose B: keeps existing download pipeline intact, existing tests mostly pass, web UI still fully functional as fallback.

---

## Design

### New DB columns

`telegram_links`: `conv_step VARCHAR(20)`, `conv_chapter_id FK→chapters`, `conv_update_id BIGINT FK→telegram_updates`

`telegram_updates`: `chapter_id FK→chapters`, `reply_text TEXT`

Migration: `0014_telegram_conversation.py`

### receive() changes

- **Audio message:** set `row.notified = True` (suppress "received" notification — chapter list comes later from process_one).
- **Text with `conv_step="awaiting_chapter"`:** parse digit or "new". If "new", inline-create chapter (nextval + flush, no commit). Set `link.conv_chapter_id`, `link.conv_step="awaiting_exercise"`. Create text row with `reply_text=exercise_list`.
- **Text with `conv_step="awaiting_exercise"`:** parse digit or "new". Look up `link.conv_update_id` → find "ready" TelegramUpdate. Set `ready.chapter_id`, `ready.exercise_id`. Call `_auto_apply()`. Clear `link.conv_step / conv_chapter_id / conv_update_id`. Row gets `reply_code="applied_bot"`.
- **Stale conversation** (conv_update_id missing or update not "ready"): clear link state, `reply_code="stale_conversation"`.

### process_one() changes

After successful download (currently sets `reply_code="ready", notified=False`), instead:
- Query all chapters ordered by number
- Build `reply_text = _chapter_list_text(chapters, row.language)`
- Set `row.reply_code = "received"` (valid fallback key), `row.notified = False`
- Set `link.conv_step = "awaiting_chapter"`, `link.conv_chapter_id = None`, `link.conv_update_id = row.id`
- `row.status = "ready"` (unchanged)

### _auto_apply() helper (new)

Acquires exercise advisory lock. If `row.exercise_id` set → `get_exercise`, update `audio_id` only. Else → `new_exercise`, set `chapter_id`, `title`, `description`, `audio_id`. Flush. Set `row.exercise_id`, `row.status="applied"`, `row.reply_code="applied_bot"`, `row.notified=False`.

### apply_import() changes (web fallback)

After applying, clear `link.conv_step / conv_chapter_id / conv_update_id` on the TelegramLink to cancel any in-flight bot conversation.

### worker/telegram.py changes

- Add TEXTS entries: `"applied_bot"`, `"stale_conversation"`
- Update reply loop: `content = row.reply_text or TEXTS[row.language][row.reply_code]`
- Remove obsolete "ready" message text (builder call: keep "ready" key to avoid KeyError on old rows, just update its text to something neutral or leave it)

### Tests

`test_worker_restart_duplicate_update_and_real_api_transport`: update comment from "ready notification" to "chapter list"; assert `len(replies) == 2` still holds since "received" notification is now suppressed (notified=True on audio receive).

All other tests pass without changes.
