# Project status

This document records progress and remaining checks for the current phase.

Prerequisites:
- Read `docs/PHASES.md` and `docs/DECISIONS.md`.

Last updated: 2026-10-10 by Copilot, session `296626a2-8b63-40eb-9331-72dd123a0523`.

## Current phase
Game fixes, lifetime prizes, and manager approval for custom avatars follow the merged game features.
The owner approves autonomous implementation after reviewing 20 proposals.
The merged game improvements remain on `main`.
The current branch is `feat/game-only-player-role`.
Accepted PHASE 7 remains closed.
Earlier game, appearance, and listening entries below remain historical session records.

### Avatar generation incident investigation

VPS logs record `AVATAR_JOB_FAILED` for job 1 at `2026-10-10T08:35:31Z`.
The running avatar worker reaches `_frames` and raises `AvatarError` at line 346.
That branch rejects an empty cell or visible alpha pixels within the required cell margin.
The resulting code is `AVATAR_SHEET_INVALID`, not a provider authentication failure.
The log omits the cell coordinates and error code.
The available MCP diagnostics do not permit source-image inspection.
The precise image defect remains unverified.

A local synthetic sheet produces 30 frames successfully.
Adding one edge pixel with alpha 1 makes the same sheet fail.
This demonstrates sensitivity to nearly transparent noise, not the actual production image defect.
Inspect the saved `avatars/custom/1/sheet.png` under `MEDIA_ROOT` before selecting a segmentation correction.
Retain image validation and add safe error codes and cell geometry to diagnostics.
Reprocess the saved sheet after correction instead of automatically requesting another paid generation.

Custom generation writes only 30 full-body frames.
Built-in selection portraits exist, but custom avatars have no separate face portrait.
The saved-custom selector currently shows the level-1 neutral frame.
A complete correction must add a circular face portrait, protected retrieval, selector wiring, and moderation for that image.
This session changes no runtime code, production configuration, or job state.

### Game-only player role

The owner adds the `player` role for Guess the Note without exercise access.
Managers can create accounts and change existing accounts to this role.
Role labels support Russian, English, and Spanish.
Players open the game after login and retain settings, password changes, and appearance.
They use owned game profiles, rounds, statistics, prizes, and existing avatar actions.
Managers still create game profiles explicitly.
The server rejects exercise metadata, audio, images, scores, listening actions, and manager functions.
Rejection also covers protected `HEAD` and range requests without file redirects.
Direct student and manager URLs show a permission error without requesting protected data.
Role changes revoke existing login sessions.
Migration `0012_player_role` preserves accounts, profiles, and progress.
It refuses downgrade while player accounts exist instead of granting exercise access.
Validation passes 339 backend tests and 365 frontend tests.
Backend coverage includes a complete 7-question player round, ownership, settings, session revocation, and migration compatibility.
The production build and all 6 quality hooks pass.

After publication, create a Player account and assign its game profile.
Check game entry, a completed round, settings, themes, and forbidden direct exercise links.
Repeat the check in Safari and on a physical phone.
Check an existing student and manager for unchanged access.

### Post-round prize collection

The owner removes the prize shelf from round preparation.
Preparation no longer requests the achievement catalog.
Every round result shows the complete collection below replay controls.
New awards retain their separate announcements.
Player statistics retain the optional collection.
Prize images, conditions, stored awards, XP, and levels remain unchanged.
Validation passes 349 frontend tests and 4 documentation tests.
The production build and all 6 quality hooks pass.
Regression tests cover preparation without prize requests and result collections without new awards in all 3 languages.
After publication, check preparation, results, and replay on a phone and in Safari.

### Packaged prize artwork

The owner supplies `trophies.png` with all 20 prize illustrations.
The source remains unchanged and supplies a reproducible extraction command.
The extractor detects each complete badge instead of cutting imperfect grid positions.
All 20 public PNGs use transparent 256 × 256 px canvases and consistent padding.
Setup and profile shelves now use pictures instead of prize emoji.
New-prize announcements use the same images.
Locked prizes use grayscale; earned prizes retain full color.
Names and descriptions remain localized in all 3 languages.
Prizes, XP, levels, and award conditions remain unchanged.
No runtime generation, migration, new dependency, or provider call occurs.
Validation passes 345 frontend tests and 7 artwork/documentation tests.
The production build and all 6 quality hooks pass.
Native Chrome passes 37 checks across 3 languages, 2 themes, and widths of 320, 390, and 1280 px.
Both shelves load all 20 PNGs; a completed round shows all 20 new-prize pictures.
The checks confirm transparent images, uniform size, localized labels, gray locked prizes, and no horizontal page overflow.
Remaining manual checks cover prize appearance in Safari and on physical phones and tablets.

### Prize extraction CI repair

Run `37234852133` fails only the prize reproduction test; the other 332 backend tests pass.
The comparison differs inside PNG compression data, not the file header or dimensions.
The reproduction test now compares exact decoded RGBA pixels, format, and dimensions.
It retains byte-for-byte verification of the original source.
Regression tests accept different lossless encodings and reject a changed color pixel with unchanged alpha.
The test remains enabled without skips, pixel tolerances, or an extraction change.

### Game fixes, prizes, and avatar approval

Implementation is complete on `feat/game-rewards-moderation`.

Round totals cannot fall below 0; individual incorrect answers retain their raw score of -1.
Migration `0011_game_rewards_review` floors historical negative totals without changing XP.
Player locks serialize XP awards, and stored JSON replies make repeated submissions stable.
Server timestamps govern the first question, subsequent questions, and feedback.
The interface accounts for its clock difference from the server.
Structured practice hints use localized note names instead of backend prose.

The game adds 20 lifetime prizes, separate from the existing completed-round trophies.
Each profile earns each prize once, without extra XP.
Season resets retain prizes, trophies, XP, and avatars.
Completed rounds supply prize progress across seasons.
Existing expected and entered arrays supply individual-note counts without another position column.
`GAME_TIMEZONE` defaults to `UTC` for calendar-day prizes and generation quotas.
`GAME_FEEDBACK_MS` defaults to `900`.
All new interface messages use Russian, English, and Spanish.
The copy welcomes breaks without warnings about losing a streak.

Custom creation requires automatic checks of the description and generated image, then manager approval.
Pending selection shows the new wordless hourglass artwork.
Approval activates the waiting selection; rejection shows the question-mark choice.
Approval preserves a later explicit built-in choice when the waiting reference no longer identifies that job.
Explicit saved-avatar selection also clears the waiting reference.
Selection locks refresh cached players after concurrent approval.
Students cannot retrieve unapproved generated images.
Managers can inspect all 30 frames and approve or reject each queued result.
Migration preserves existing ready avatars as approved without paid regeneration.
The packaged hourglass does not replace the owner's original PNG.

The full backend suite passes 329 tests.
An additional ownership regression passes with the 3 existing achievement tests.
All 337 frontend tests pass.
The production build and all 6 quality hooks pass.
Native Chrome checks cover 18 student cases and 6 manager decisions at 320 px.
These checks use synthetic responses in all 3 languages and both naming settings.
Each manager preview retrieves 30 unique frames before approval or rejection.
The badge generator passes separate type and formatting checks and reproduces the packaged image exactly.
Real provider image quality and Safari remain manual checks.
The knowledge graph receives an AST-only update.
No paid provider call, push, deployment, or production change occurs.

Local tests use a disposable PostgreSQL database in memory because the shared Docker disk is full.
The session removes only its own database fixture and browser processes.

Remaining manual checks:
1. Deploy the backend, frontend, and worker together with migration `0011_game_rewards_review`.
2. Check nonnegative results, stable retries, and first-question timing in Chrome and Safari.
3. Check prizes across seasons, both naming settings, and all 3 interface languages.
4. Generate only an explicitly authorized avatar through the configured provider.
5. Inspect all 30 images as a manager before approval.
6. Check student image denial before approval and automatic activation after approval.
7. Reject a disposable result and check the question-mark fallback.
8. Check existing ready avatars after migration without another provider request.

### Failed release 37204983176

The owner requests diagnosis and repair through `vps-docker`.
Publication succeeds, but the deploy step fails.
Container logs identify an HTTPS origin with insecure session cookies.
Backend configuration validation correctly refuses startup.
The observed backend is stopped; the frontend remains created but not running.
PostgreSQL and unrelated VPS services remain running.
The Actions log tools return no output; container logs establish the startup failure.

The rollout now validates candidate backend settings before changing active services or applying migrations.
It uses a disposable backend container without dependency startup or database access.
Invalid settings preserve the existing services and release state.
The Secure-cookie requirement remains unchanged.
No private credentials are read, replaced, or logged.

Production recovers independently during this investigation.
The repeated run `37204983176` completes successfully for source `6455bf3`.
The backend, frontend, OMR, and Telegram services report healthy.
The avatar worker runs, and PostgreSQL remains healthy.
The public health endpoint returns exactly `{"status":"ok"}`.
The public frontend returns HTTP 200.
This session does not change production configuration or repeat the deployment.
Main includes the preflight change through PR 13.
No speculative restart, unrelated Compose update, or push occurs.

Verification includes 61 deployment tests and 4 documentation tests.
A real disposable deployment rejects insecure HTTPS cookies without replacing healthy containers or changing the active release.
All 6 configured quality checks pass.
The AST graph is current.
The disposable deployment fixtures remove their own containers, networks, and volumes.

Manual verification: sign in through HTTPS, then open and start Guess the Note.
The statistics branch preserves the preflight change during main integration.

### Game statistics and season reset

The owner reports missing statistics and progress-reset controls.
Existing profile and manager screens have no visible entry from the player selector.
The profile route is not parsed, and the old manager screen hides reset errors.
The previous bulk action sends separate reset requests.
The initial APIs omit wins, historical filters, missed notes, and actual trophies.

The player selector now shows compact rounds and win rate, with a **Statistics** button.
Managers also see **Player management**.
Profiles show actual XP, level, trophies, and season history.
Summary tables separate difficulty and note count and retain the combined matrix.
Manager detail adds localized note analysis, a clef filter, latest-round confusions, and an accessible heatmap.
Timeouts appear as missed notes.

The API excludes unfinished and expired rounds.
Ownership checks apply to statistics, history, and selected seasons.

The reset retains the original season-based rule.
It opens a new statistics season without removing history, XP, levels, trophies, or saved avatars.
The owner does not confirm full progress deletion.
Both single and bulk actions require explicit `RESET` confirmation.
The dialog stays open on failure and cannot close during a pending request.
Bulk reset uses the existing atomic endpoint.

Player locks serialize resets, and season numbers remain monotonic.
Successful resets refresh history, statistics, and mistake analysis.
Completed rounds refresh profiles and statistics.
Direct profile routes and browser navigation work.
All new interface strings have Russian, English, and Spanish translations.
No dependency, migration, paid generation, production reset, or deployment occurs.

Verification includes 82 game tests, 4 documentation tests, and 324 frontend tests.
The production frontend build and all 6 quality hooks pass.
Real PostgreSQL checks cover ownership, preserved history and trophies, rejected resets, and concurrent resets with one active season.
Chrome checks 36 cases across 3 languages, both naming settings, both roles, and widths of 320, 390, and 1280 px.
Browser checks use synthetic API data; they do not reset production players.
Checks verify exact weighted averages, bounded page width, visible counts, pending-dialog protection, error retry, and one bulk request.

The knowledge graph receives an AST-only update.
Disposable PostgreSQL and browser fixtures are removed after validation.
The feature branch receives main through a merge before publication.
The merge preserves the deployment preflight and both feature records.
The generated graph is rebuilt from the combined source.

Remaining manual checks:
1. Publish the backend and frontend together through the verified release flow.
2. Use disposable local profiles to check single and bulk resets, retained XP, and history.
3. Open statistics in Chrome and Safari on a phone or iPad.
4. Check both naming settings and all 3 interface languages.

### Main integration

Main includes the persistent-avatar feature from PR 11.
The merge preserves both avatar generation and the note-only game rules.
The migration chain now runs `0008_game` → `0009_avatar_sheets` → `0010_round_rules`.
The already merged avatar migration remains unchanged.
Round-rule migration tests cover both previous revisions and preserve active avatar jobs from revision `0009_avatar_sheets`.
All 154 affected backend and deployment tests and 4 documentation tests pass.
All 315 frontend tests, the production build, and 6 quality hooks pass.
Checks cover clean upgrades, both previous revisions, downgrade/repeat, model parity, and active avatar job preservation.
The regenerated knowledge graph contains both features without conflict markers.
No push, production change, private configuration inspection, or paid generation occurs.

### Seven-note rounds and assistance bonuses

The owner confirms E2–C4 for bass and a one-time bonus per round.
Treble questions use C4–A5; both clefs have 13 natural pitches.
The 7 answer buttons select names C through B without octave labels.
Buttons, selected answers, and revealed answers follow account naming and interface language.
Button audio uses the current question note's octave, including wrong choices, repeated names, and backspace.

The sampled piano expands to natural C2–B5 so every answer button works in octaves 2–5.
One local asset contains 112 AAC samples across 4 real velocity layers and occupies 2464963 bytes.
The builder retains upstream tuning, attribution, the license, and 68 source hashes.
Independent decoding verifies all 112 samples within 11.45 cents of their intended frequencies.
The previous C4–B5 asset remains unchanged for cached application code.
The new application requests only the new piano asset and adds no dependency.

Setup shows only the selected 13, 10, or 7 s limit.
The renamed correct-answer switch and sound-hint switch each show +1 point when disabled or 0 points when enabled.
Each disabled option adds 1 point once per completed round, including losing rounds.
The result states the total assistance bonus.
XP, victory, stars, emotions, and existing completed results remain unchanged.
The backend stores immutable options and rules version 2.
Migration `0010_round_rules` preserves version 1 for previous rows, with strict octave grading and no assistance bonus.
Submitted fake bonuses or option changes cannot change the result.
A round lock prevents simultaneous final submissions from awarding XP or bonuses twice.

The staff uses one 234 × 140 frame for all clefs and 1–4 notes.
Shorter note groups remain centered.
Correct answers appear only to the right of the centered playback control, including when the control is hidden.
Reserved feedback space preserves the staff size and playback control coordinates.
All 3 interface languages receive the revised labels and explanations.

The complete backend and deployment suite passes 298 tests.
The additional legacy-asset test and final targeted rerun also pass.
All 311 frontend tests, the production build, and all 6 quality hooks pass.
Chrome verifies 53 native audio and layout cases without mocking AAC decoding or scheduling.
Coverage includes 320, 390, and 1280 px, both themes and clefs, all note counts, languages, and naming settings.
Checks compare actual staff dimensions and button coordinates before and after feedback.
They also verify all assistance combinations, wrong bass choices, repeated C4/C5 answers, and one asset request.
Upgrade, repeat, downgrade, previous-release rows, and model parity pass on disposable PostgreSQL.
The knowledge graph receives an AST-only refresh.
No production change, push, deployment, private configuration inspection, or paid generation occurs.

The main integration now includes the avatar-generation repair.
Migration `0010_round_rules` follows `0009_avatar_sheets` as the single head.

Remaining manual checks:
1. Publish the backend and frontend together and apply `0010_round_rules`.
2. Compare bass E2–C4 and treble C4–A5 hint and answer sounds in Chrome and Safari on a real phone or iPad.
3. Confirm 7 labels under both naming settings and switch between Russian, English, and Spanish.
4. Check both switches and verify a round bonus of 0, 1, or 2 exactly once, without extra XP.
5. Confirm fixed staff dimensions and centered playback during correct, incorrect, and timeout feedback.
### Persistent custom avatar generation

The owner requests 30 saved appearances, honest progress, reuse, and economical generation on a separate branch.
The previous worker generates only 3 emotion images.
The existing API returns status `503` when `OPENAI_API_KEY` is empty.
Read-only VPS inspection confirms that the production avatar worker runs.
This session does not inspect private environment values or confirm production key presence.
The interface now reports missing configuration before permitting creation.
Saved and built-in avatars remain available without provider credentials.

One image request now creates a sprite sheet with 5 columns and 6 rows.
The default uses `gpt-image-1-mini`, low quality, and a transparent `1024x1536` PNG.
The worker extracts 10 levels with neutral, happy, and sad emotions.
Explicit legacy DALL-E settings retain white-background extraction without erasing magenta or enclosed white artwork.
Each job permanently saves its original sheet, 30 transparent PNG frames, and a hash manifest in shared private media storage.
Authenticated level-specific routes retain ownership checks, nginx delivery, and no-store responses.
Both selection endpoints reject incomplete version 2 sets.

The chooser shows phases, actual saved-image counts, and explicitly approximate remaining time.
The count stays at 0 during the single provider image request.
The interface explains this limitation rather than inventing intermediate AI progress.
An overdue estimate becomes unknown.
The progress area becomes visible automatically, including after reopening a cached job on a phone.
Ready previews show every level and all 3 emotions.
The paginated saved gallery preserves previous choices after switching to built-in characters.
Selection requires no new image request.

Account and player locks serialize quota checks and creation.
Identical pending requests reuse one job and one quota record.
Durable worker claims prevent duplicate processing.
Recovery reuses a saved sheet and valid frames, including when the key becomes unavailable.
A late provider reply cannot replace a new worker's sheet.
Interrupted requests without a saved image fail explicitly without automatic paid retries.
Moderation refunds only the linked quota record.
Migration `0009_avatar_sheets` preserves older ready avatars and closes untracked legacy pending jobs without regeneration.

All 293 Python tests, including deployment checks, and 312 frontend tests pass.
Empty and previous-release migrations, repeated upgrades, downgrades, and model comparison pass.
The production frontend build passes.
All 6 repository quality hooks and documentation checks pass.
Chrome verifies 100 cases using synthetic APIs and existing local artwork.
These cover all 3 languages, both themes, 4 viewport widths, visible progress, polling, reopening, reuse, pagination, and legacy previews.
Synthetic geometry checks do not establish real-provider artistic quality.
No new dependency, paid generation, push, deployment, or private configuration change occurs.
The code knowledge graph receives an AST-only refresh.

Remaining manual checks:
1. Publish the backend, frontend, migration, and avatar worker together.
2. Configure a private `OPENAI_API_KEY` with model access in both the backend and avatar worker.
3. Select the intended model and quality explicitly if the existing environment retains a legacy override.
4. Generate one real avatar and inspect all 10 levels and 3 emotions for consistent identity and correct expressions.
5. Close and reopen generation in Chrome and Safari; confirm understandable progress and approximate time.
6. Restart the application, switch to a built-in character, and reuse the saved avatar without another generation request.

### Sampled piano and game setup

The owner confirms 14 natural pitches from C4 through B5.
Both clefs now share this range.
The 14 answer buttons identify the selected name and scientific octave.
Submission uses that actual octave instead of copying the question's octave.
Button labels and revealed answers follow account note naming and interface language.
The bass staff expands its viewport for high notes without moving clef anchors.

Answer buttons and the sound hint now use the same sampled piano and velocity 64.
The requested `soundfont-player` dependency loads one local Salamander Grand Piano V3 asset.
Its 56 AAC samples retain 4 original velocity layers and occupy 1233535 bytes.
The asset retains attribution, the complete CC BY 3.0 license, source hashes, and an export procedure.
Offline export uses the upstream tuning corrections.
Independent decoding verifies all 56 pitches within 6.29 cents of their expected frequencies.
The browser does not load a full SF2 or an external soundfont.

Setup offers independent sound-hint and correct-answer switches.
Defaults retain the hint and hide the answer.
The optional answer appears to the staff's right during feedback and uses the server's authoritative notes.
Choices remain between rounds within the current game-area session.
Difficulty explanations state the existing 13, 10, and 7 s limits.
Piano loading completes before round creation; failed loading permits retry without consuming a round.
Setup controls remain disabled during loading and round creation.

Managers see only active, non-emergency accounts without an existing profile in the creation selector.
A filtered, paginated endpoint returns these candidates and their total.
An empty list shows the requested all-assigned popup instead of a creation form.
The backend locks the owner account row and rejects concurrent duplicate creation or emergency ownership.
Existing profiles, progress, manager-only creation, scoring, and XP rules remain unchanged.
No migration, private configuration, push, deployment, or paid generation occurs.

All 308 frontend tests, 221 backend tests, the production build, and 6 quality hooks pass.
The runtime dependency audit reports no vulnerabilities.
Chrome verifies 46 native piano cases and 8 lifecycle or error cases.
Browser API fixtures remain synthetic; audio loading, AAC decoding, scheduling, and input events are real.
Coverage includes 320, 390, 768, and 1280 px, both themes, both clefs, both naming settings, and all 3 languages.
Every pitch in the 14-note range uses the same decoded buffer for its hint and answer.
Additional checks confirm localized authoritative answers, one asset request, loading retry, keyboard input, cancellation, and a real timeout.
A narrow-screen regression keeps partial-answer labels readable without wrapping or clipping their octave.
The knowledge graph and its HTML viewer receive an AST-only refresh.

Remaining manual checks:
1. Publish the backend and frontend together.
2. Compare hints and matching answer buttons for C4, C5, and B5 in Chrome and Safari on a real phone or iPad.
3. Test both switches, incorrect answers, timeouts, and return after backgrounding the browser.
4. Change account note naming and language; confirm matching button and revealed-answer labels.
5. Confirm both clefs remain visible and create a profile using the filtered account selector.

### Game note playback
The white round button below the staff plays all notes from the current game question.
It preserves their written pitches, octaves, and order.
The existing synthesizer produces tones without spoken names, downloads, or new dependencies.
The button changes to a stop control during playback.
Repeating after a partial answer still plays the complete question.
Labels and errors use Russian, English, and Spanish translations.

The user gesture creates or resumes the audio context, including Safari's interrupted state.
Cancellation stops and disconnects active and scheduled sources.
Answer selection, submission, timeout, page exit, and leaving the round cancel playback.
Natural completion also releases the sources.
Audio failures remain visible and permit another attempt.
Listening does not enter answers, pause the timer, change scoring, or create journal rows.
Staff engraving and existing answer-button tones remain unchanged.

All 290 frontend tests, the production frontend build, documentation checks, and 6 quality hooks pass.
Chrome verifies 32 cases using actual Web Audio nodes and trusted pointer events.
The cases cover 320, 390, 768, and 1280 px, both themes, both clefs, and 1 or 4 notes.
They include all 3 languages and confirm exact pitches, timing, source cleanup, button placement, and no horizontal overflow.
Additional browser checks cover stop, replay, partial answers, page exit, keyboard activation, mute errors, and retry.
A real timer expiration cancels active playback; the next question plays its own notes.
The knowledge graph and its HTML viewer receive an AST-only refresh.
No backend, migration, configuration, dependency, push, or production changes occur.

Remaining manual checks:
1. Publish the frontend change.
2. Hear 1 and 4 notes in both clefs on a real phone or iPad in Chrome and Safari.
3. Stop and repeat playback before selecting answers.
4. Confirm unchanged timing and scoring, with no sound continuing after exit or timeout.

### Standard game clefs
The owner reports distorted treble and bass clefs with 2 example screenshots.
The old renderer uses simplified hand-drawn curves and the same incorrect offset for both clefs.
It now uses the original filled glyph contours from Bravura 1.482.
The pinned source, copyright notice, and SIL Open Font License accompany the derived data.

The treble origin sits on the G4 line; the bass origin sits on the F3 line.
The bass dots correctly surround F3.
The font's original staff-space scale preserves the symbols' proportions.
Inline SVG avoids runtime font requests, fallback characters, and font-loading delays during the timer.
Notes, stems, ledger lines, paper, and layout remain unchanged.
Accessible clef descriptions now use Russian, English, and Spanish translations.

All 270 frontend tests, the production frontend build, documentation checks, and 6 quality hooks pass.
Chrome verifies 64 actual game cases with both clefs and 1 or 4 notes.
The cases cover 320, 390, 430, and 1280 px, both themes, and standard or large account fonts.
They confirm the original glyph bounds, exact G/F anchors, bass-dot placement, unchanged notes, and no clipping or horizontal overflow.
The application makes no runtime music-font request.
The knowledge graph receives an AST-only update.
No application dependency, backend, migration, private configuration, push, or production changes occur.

Remaining manual checks:
1. Publish the frontend change.
2. Inspect both clefs in real rounds on a phone or iPad in Chrome and Safari.
3. Confirm unchanged note positions and correct answers in both clefs.

### Circular game shortcut
The owner approves moving only the header branding to accommodate an upper-left badge.
The supplied Unicorn artwork becomes a transparent 128 × 128 px public PNG.
The original source remains unchanged.
The circular 44 × 44 px link opens `/game` with a localized tooltip and accessible name in all 3 languages.
The existing authentication gates and menu link remain unchanged.

Absolute positioning keeps the new control outside the document flow.
An inaccessible sizing copy preserves the original header dimensions.
Below 900 px, compact branding text fits beside the badge without moving other controls.
Desktop branding retains its previous text size.

Chrome compares 24 before-and-after cases at 320, 390, 430, and 1280 px.
The cases cover all 3 languages, standard Roboto, and large Serif text.
Navigation, forms, panels, and the theme control retain their exact original coordinates.
The cases show no measured horizontal overflow.
Dark mode retains the same coordinates for navigation, forms, and panels.
Actual keyboard Tab navigation shows the focus outline, and activating the badge opens `/game`.
Real keyboard, mouse, and emulated mobile touch activation each reach the player-selection page.
All 263 frontend tests, the production frontend build, documentation checks, and 6 quality hooks pass.
The knowledge graph receives an AST-only update.
No dependency, backend, migration, private configuration, push, or production changes occur.

Remaining manual checks:
1. Publish the frontend change.
2. Tap the badge on a real phone or iPad and confirm the player-selection page.
3. Check the localized tooltip and keyboard focus in Chrome and Safari.

### Game first-entry repair
The owner reports that `/game` shows only the player-selection heading.
Profiles remain separate from accounts, but the interface previously offered no way to create the first profile.
The previous avatar browser fixture supplied profiles in advance and did not cover this entry condition.

The account menu now links to Guess the Note for both roles after any required password change.
Managers create profiles and select an active owner account through the existing 50-account pagination.
Creation starts an active season and uses Unicorn as the initial avatar.
The existing chooser changes the avatar without resetting progress.
Students see only assigned profiles; an empty list directs them to a manager.
The repair retains manager-only creation and introduces no automatic profiles.

Player loading, empty results, and request errors now have separate translated states.
Account lookup and duplicate-name errors remain visible in the creation form.
Missing or inactive owners create neither a player nor a season.
Logout, session expiry, and account changes cancel and remove cached game data.

Chrome verification starts with 2 accounts and no player profiles in a separate disposable database.
The manager creates a profile for the student through the interface.
The student then selects it through the menu and starts a real round.
All 11 browser cases pass, including 320, 390, 430, and 1280 px layouts without measured overflow.
New controls retain touch targets of at least 44 px.
Regression tests cover ownership, CSRF, active accounts, empty states, errors, pagination, and logout cache removal.
All 218 backend tests, 260 frontend tests, the production frontend build, and 6 quality hooks pass.
The knowledge graph receives an AST-only update.
No dependencies, migrations, private configuration, paid generation, push, or production changes occur.

Remaining manual checks:
1. Publish the paired backend and frontend changes.
2. Create a profile for an existing student through the manager's Guess the Note page.
3. Sign in as that student, select the profile, and click **Let's go!**.
4. Check the creation dialog and navigation in Safari on a real phone or iPad.

### Game avatar artwork
The owner supplies the original sheets and authorizes repeated artwork on 2026-10-03.
The catalog includes 11 characters, with the requested Lion, Panda, and Rhino additions.
Extraction produces 330 level/emotion files and 12 selection choices.
Both original-folder outputs and public copies use transparent PNGs.
The 384 × 384 px canvases contain full character crops without circular clipping.
The source sheets remain unchanged.

The chooser saves a built-in character through a narrowly authorized, CSRF-protected endpoint.
Students change only owned players; manager-only player editing retains its authorization boundary.
All player views use the backend's derived level from existing XP thresholds.
Completed rounds refresh player caches.
Results show happy for 5–7 correct answers, neutral for 3–4, and sad for 0–2.
The winning threshold and XP bonus do not change.

The question-mark card opens explicit custom creation with quota, polling, preview, acceptance, discard, and errors.
Recent jobs remain available when the chooser reopens.
Selecting built-in artwork clears a generated selection.
Private generated images require authentication and use nginx's internal media route.
The existing generation worker now participates in development, production deployment, and rollback.
An empty private credential keeps it idle and makes generation explicitly unavailable.
No paid generation occurs during this work.

The selection source lacks a unicorn portrait; its first neutral appearance supplies the extra choice.
Five sheets repeat their final group across levels 9 and 10.
Three 11-group sheets retain their final forms through the documented correspondence.
Mermaid extraction follows the owner's left-to-right emotion pattern despite inconsistent original expressions.
Some original figures overlap; extraction cannot recover hidden artwork.
See `docs/developer/game-avatars.md` and `avatars/crops.json` for reproducibility and exact correspondence.

Browser checks cover 42 combinations of width, language, theme, screen, and result.
They use Chrome at 320, 390, 430, and 1280 px with synthetic authenticated profiles.
Actual UI rounds produce 7, 4, and 2 correct answers and the corresponding avatar emotions.
These checks confirm saved Lion/Panda/Rhino choices, XP-level refresh, loaded public images, and no measured overflow.
Game controls use 44 px minimum heights; narrow setup buttons and result actions remain inside the viewport.
The chooser reports an unconfigured generation service instead of claiming success.

Docker verification compares all 342 published PNGs with their source copies.
An actual nginx check confirms authenticated GET/HEAD, private PNG delivery, uncached responses, and anonymous rejection.
Game page routes now return successful document responses instead of the old SPA fallback's status `404`.
The knowledge graph receives an AST-only update.
No dependency, migration, private environment file, push, or production service changes occur.
All 217 backend tests, 251 frontend tests, 58 deployment checks, and 6 quality hooks pass.
The final paired Docker images build successfully.

Remaining manual checks:
1. Inspect every character, level, and emotion against the original artwork.
2. Check the chooser and result actions on real phones and an iPad in Chrome and Safari.
3. Complete rounds near an XP threshold and confirm the saved avatar and increased level after reload.
4. Configure the private generation service only if needed, then confirm a real preview, acceptance, and all 3 emotions.
5. Publish the paired release before production acceptance.

### Appearance settings
The owner accepts this separate proposal and requests `feat/appearance-settings` on 2026-10-02.
That branch starts from source `c4ee4f1`.
Settings includes independent light and dark schemes: Classic, Forest, Warm, and Plum.
Each scheme coordinates buttons, their text, the page background, panels, ordinary text, and control outlines.
Account preferences also select Roboto, System, or Serif and a base size of 16, 18, or 20 px.
The example panel previews either mode without changing the page or saving automatically.
Save applies the authenticated profile without a reload.
Restore selects the standard appearance; Save commits it without resetting language or note naming.

Light/dark mode remains browser-local; account preferences follow the user across devices.

Migration `0007_appearance` adds constrained profile columns and preserves existing accounts with the original appearance.
Partial settings updates retain omitted fields and reject nulls, empty updates, unsupported values, and unknown fields.
New accounts use 4 documented environment defaults.
Emergency-manager startup preserves previously saved appearance.
Anonymous pages return to Classic, Roboto, and 16 px after logout.

All 182 backend tests, 194 frontend tests, 46 focused release checks, and 6 quality hooks pass.
The backend suite includes all 4 documentation checks, migration backfills, empty-database upgrades, downgrade, and schema-drift checks.
Palette tests cover readable normal and hover states; Forest uses explicit dark hover shades to retain contrast.

Chrome passes 134 cases with synthetic APIs across all schemes, modes, languages, fonts, sizes, and representative routes.
The checks cover 320, 390, 430, and 1280 px with long account and exercise content.
They confirm no page or mobile container overflow, independent draft saving, restoration, errors, and stable form values.
An actual border click confirms the 44 px field target, including its smaller native input.
Browser measurements confirm unchanged score dimensions and engraving fonts between standard and large serif interfaces.

Component regressions confirm unchanged audio nodes, spoken players, and tempo during theme updates.

The production frontend build and full frontend Docker image build pass.
The final image serves 213 byte-identical assets and 5 application routes with the existing security headers.
No dependencies, private configuration, original voice files, deployed services, push, or pull request changes occur.
The owner's untracked `material_design.md` remains untouched.

Remaining manual checks:
1. Check all schemes and large fonts in Chrome and Safari on real phones and an iPad.
2. Save different light and dark schemes, then reload and sign in on another device.
3. Confirm local light/dark mode, profile preferences, and unchanged language and note naming after restoration.
4. Check real recordings and spoken notes for unchanged position, tempo, cursor, and audible playback.
5. Publish the paired backend and frontend release with migration `0007_appearance` before production acceptance.

### CI follow-up: run 37008189410
The owner requests investigation and repair through `vps-docker` on 2026-10-02.
The failed run belongs to appearance pull request #4.
Its production permission test expects `0006_omr`, although the built image correctly applies `0007_appearance`.
Its frontend job also exceeds the default 5 s limit during the 50-row user-editing test.
Backend, quality, and dependency jobs pass in that run.

The production test now derives the expected head from the built backend's Alembic scripts.
All role, port, schema-isolation, and permission assertions remain.
Vitest now uses 2 workers for ordinary `npm test`, matching the previously successful bounded local runs.
The fix does not increase timeouts, remove rows, skip tests, or change application behavior.

Fresh local backend and frontend images reproduce the original production assertion failure.
After the fix, the complete `deploy/tests` suite passes all 56 tests.
Ordinary `npm test` passes all 194 tests in 2 consecutive local runs.
It also passes twice inside Linux with 2 CPUs, 2 GiB memory, and the same default timeout.
The production build, all 6 quality hooks, and 4 documentation checks pass.

The old failed run remains historical; a new remote run requires publication of the fix commit.
No VPS services or private environment files change.

### Student original image and score
The owner requires both available media blocks on 2026-10-02.
The student area now always shows the available original image, followed by an available approved score.
An approved score no longer replaces the image or depends on its presence.
Score errors retain the original image without rendering a duplicate fallback.
Image errors remain explicit, including when the score succeeds.
Unapproved results and approved results without a score version remain hidden.

The original regression fails before the fix and passes afterward.
All 200 frontend tests, the production build, 6 quality hooks, and 4 documentation checks pass.
New cases cover simultaneous media, an independent score, missing approval/version, image failures, and score failures.
Existing recorded-audio, speech, navigation, and journal regressions remain green.
No backend API, file authorization, dependencies, private configuration, or deployed services change.

Remaining manual check:
1. Open a student exercise with an original image and approved recognition.
2. Confirm that both appear, including in Chrome and Safari on a phone.
3. Confirm that a pending or rejected score leaves only the available original image.

### Material Design baseline
Material Design: separate visual migration after accepted PHASE 7.
The owner starts the feature on 2026-10-01.
Steps 1 through 6 are implemented and validated locally.
The separate branch `feat/material-design` starts from merged main source `5108a9a`.
The owner authorizes all remaining steps without intermediate confirmations.
Implementation keeps separate screen commits and validates each screen before continuing.
Safari automation remains unavailable because its remote automation setting is disabled.
Final owner visual acceptance and production publication remain separate.

### Responsive layout follow-up
The owner requests mobile responsiveness on 2026-10-02 without replacing the existing architecture.
Measured problems include wide table content, retained desktop score dimensions, repeated nested padding, and undersized navigation targets.
Below 600 px, user and journal cards retain every field, permitted action, filter, and pagination handler.
Mobile navigation uses 2 columns; buttons, links, and checkboxes provide targets of at least 44 px.
Forms shrink correctly and selected values stay within their controls.

Nested panels preserve more width for images, audio, scores, and spoken controls.
Score width changes recalculate line breaks and restore the current cursor without reloading MusicXML or restarting playback.
Desktop presentation remains unchanged in all 9 baseline screenshots at 1280 px.

The complete frontend suite passes 155 tests.
Chrome passes 72 initial viewport checks, including 320, 360, 375, 390, 414, 430, 768, and 1280 px.

Another 378 Chrome cases cover all languages, both themes, long unbroken text, selected options, and inline editing.
These cases include 50-row pages, large original images, 24-measure scores, note labels, OMR review, and long filenames.
These checks find no mobile page, table, or score horizontal scrolling.
The Safari driver responds, but refuses sessions because Allow remote automation remains disabled.
The task does not change browser preferences, private configuration, APIs, dependencies, or deployed services.

Remaining manual checks:
1. Check Chrome and Safari on real phones at 320-430 px.
2. Check all languages and both themes with long real exercise content.
3. Select files and dates on an iPhone.
4. Check every measure and note label in a real approved score.
5. Turn the device during recorded audio and spoken playback.
6. Confirm stable playback position, tempo, note cursor, and account form values.

### Installation and usability follow-up
The owner requests 5 focused improvements on 2026-10-02.
Original favicon, phone, and dedicated iPad icons accompany 3 localized application manifests.
Mobile installation uses a native prompt after a click, or browser-specific instructions when unavailable.
Installed applications suppress the offer; no service worker, offline caching, or Android share target returns.
Browser preferences select the anonymous language, with English fallback; saved account language takes priority after login.

Activate and Deactivate use equal widths in every language.
Only Settings shows and requests Service status.
Recognition review omits the original image; exercise previews and student fallbacks retain it.
Conservative AAC timings choose a safe tempo before playback; decoded lengths confirm it before scheduling.
Browser storage remembers tempo per account, exercise, score version, language, and naming choice.
Short notes can extend the slider below 40 BPM without relaxing speech-rate or complete-duration limits.

All 181 frontend tests, 10 speech-generation tests, 4 documentation checks, production build, and 6 quality hooks pass.
A 1470-case regression covers every committed language, naming choice, pitch, accidental, and short-note duration.
Chrome passes 66 follow-up cases, including 320, 360, 390, 430, and 1280 px.
Cases cover long content, matching button widths, localized manifests, health visibility, review, actual playback, and tempo persistence.
Chrome decodes all 66 original clips and confirms that exported timings never underestimate their decoded lengths.
Standalone browser checks use the WebKit property because CDP cannot override display mode.

The restricted Docker context preserves all 11 new public assets.
Pinned nginx returns their exact bytes, security headers, and the correct manifest MIME type.
The full frontend image build stops at npm installation because local Docker storage has insufficient space.
Only the failed task container is removed; no shared images, volumes, or caches are pruned.
No dependencies, private configuration, original voice files, deployed services, or account schema change.

Remaining manual checks:
1. Install with Chrome on Android and Safari on an iPad.
2. Check the favicon, Home Screen icon, launch, and standalone navigation.
3. Check browser language before login and saved account language after login.
4. Play real short notes and accidentals without cut words or overlapping notes.
5. Adjust tempo and confirm its return after navigation and reload in the same browser.
6. Complete the normal CI image build and deployment before checking the production installation.

### Password policy follow-up
The owner reduces the default password minimum to 8 characters on 2026-10-01.
Backend defaults, both Compose files, example configuration, and all 3 language hints use the new minimum.
Creation, reset, change, and emergency credentials share the same configured policy.
Passwords shorter than 8 characters remain invalid; the maximum length remains 256 characters.
Existing hashes, sessions, rate limits, and private configuration remain unchanged.

Set `PASSWORD_MIN_LENGTH=8` in an existing deployment environment if it explicitly overrides the old default.
Restart the backend after updating its deployed configuration.
All 42 auth tests and 4 documentation checks pass with an isolated PostgreSQL database.
The translated hints, frontend build, and all repository quality hooks pass.

### Previous PHASE 7 completion
PHASE 7: hardening and documentation review.
Status: complete after deployed owner acceptance on 2026-10-01.
The owner authorizes the entire phase without intermediate confirmations on 2026-10-01.
PHASE 7 merges from `feat/phase7-hardening` as source `165a1397`.
The owner retains all 66 speech clips and declines regeneration.
The task does not call the paid speech generator.

### PHASE 7 implementation
- Add a configurable 6144 MiB cold-image budget and 2048 MiB free reserve.
- Measure Docker and release storage before pulls and check the reserve again before changing services.
- Fail closed for unknown storage, invalid limits, insufficient space, and remote Docker daemons.
- Preserve active services, database volumes, release state, and existing rollback images after capacity refusal.
- Add a translated application 404 page with a language selector and home link.
- Preserve HTTP 404, HEAD behavior, API JSON errors, authenticated file checks, and direct internal-file denial.
- Add CSP, frame denial, MIME protection, no-referrer, restricted browser permissions, and HTTPS-only HSTS.
- Reject insecure HTTPS cookies and non-loopback HTTP authentication during settings validation.
- Add structured backend, worker, and nginx access records without request bodies, tokens, or query strings.
- Keep exception types and frame locations without logging exception values.
- Record backend lifespan failures before rethrowing them; preserve cleanup and safe exception diagnostics.
- Verify existing production log rotation and OMR/Telegram healthchecks.
- Add strict Python and JavaScript dependency audits to CI.
- Add documentation checks for required guides, environment coverage, relative links, and sentence lengths.
- Review developer and user documentation; correct stale phase, schema, deployment, and prototype statements.
- Add the missing language and troubleshooting guides and the complete final VPS smoke checklist.

### PHASE 7 validation and deployment boundary
Local backend and frontend suites, quality hooks, dependency audits, image builds, and real container checks pass.
Local checks pass 150 backend tests, 137 frontend tests, and 56 deployment/container tests.
Container checks cover 404 statuses, headers, API/file boundaries, Range playback, log rotation, migrations, and compatible rollback.
Disk tests cover the exact 8192 MiB pre-pull boundary and the 2048 MiB post-pull reserve.
Documentation checks cover all product environment variables and the complete user/developer guide set.
The existing tracker test passes in the pinned Node container; no unrelated flaky-test change is necessary.

The updated PHASE 7 stand responds at `http://127.0.0.1:18080/`.
PostgreSQL, backend, frontend, and OMR report healthy states; Telegram remains stopped.
Public health and unknown-page HEAD checks pass against this persistent stand.
The strengthened rollback check confirms that disk refusal preserves all running service identities and release state.

Local commits record the complete implementation.
The owner publishes the branch and opens pull request #2 on 2026-10-01.
Product CI run `36896694237` succeeds for source `725e2a5`.
All 5 jobs pass: dependencies, checks, backend, frontend, and containers.

The owner merges pull request #2 as `165a1397` on 2026-10-01.
Publication run `36921037861` completes image verification and the production deployment successfully.
The public HTTPS health endpoint returns exactly `{"status":"ok"}`.
The owner confirms completion of PHASE 5 and PHASE 6 after deployment on 2026-10-01.
The owner subsequently confirms final PHASE 7 smoke acceptance on 2026-10-01.
PHASE 5, PHASE 6, and PHASE 7 are complete.

Main-branch CI run `36866682091` succeeds for merged PHASE 6 source `f3ba47f`.
Publication run `36867434244` verifies its images but deployment fails with `OMR_MEMORY_INSUFFICIENT`.
The recorded failure is historical evidence from its configured target, not a current capacity measurement.

The owner explicitly removes the host-memory preflight on 2026-10-01 after the recorded failure.
Rollout no longer inspects `/proc/meminfo` or rejects insufficient host RAM.
Docker memory limits, disk checks, worker healthchecks, and compatible rollback remain active.
The obsolete host-reserve setting is removed from the example and production Compose.
This change does not rewrite private server configuration or restart unrelated services.
The follow-up passes 37 rollout, real rollback, and documentation checks, plus all quality hooks.

Follow-up CI run `36919176347` passes all 5 jobs for source `4af7f90` before merge.
The verified production rollout and owner-confirmed smoke acceptance close the final PHASE 7 gates.
Chrome command-line DOM verification times out in this environment.
HTTP and React component checks pass; they do not establish a successful real-browser acceptance pass.
The owner confirms PHASE 7 acceptance; no new automated browser or device-specific evidence is inferred.

### Previous PHASE 6 acceptance
PHASE 6 spoken notes are complete with owner-confirmed acceptance after production deployment.
The owner confirms PHASE 5 and PHASE 6 completion on 2026-10-01.
This acceptance does not add automated Safari evidence or browser-specific measurements.
The owner authorizes complete phase automation and postpones PHASE 5 deployment on 2026-09-30.
Work uses `feat/phase6-spoken-notes` so main-branch publication cannot deploy these changes.
The owner supplies the private OpenAI key and opens pull request #1 on 2026-10-01.
All 66 actual speech clips are generated, verified, and committed.
The owner confirms audible Chrome acceptance in the local container stand on 2026-10-01.
The owner requests and receives 3 follow-up fixes after the listening pass, detailed below.

### PHASE 6 follow-up fixes after owner acceptance
- Poor photo quality causes genuine OMR chords and backups in exercises 32 and 33, so the strict
  parser correctly refuses to speak them. `docs/PRODUCT_BRIEF.md`, `docs/PHASES.md`, and
  `docs/user/manager.md` now document the required photo quality before OMR upload.
- Spoken playback previously changed pitch per note duration because the rate limiter clamped
  long notes down to `minRate`. The rate now floors at 1 and pads spare time with silence, so
  every note keeps one natural voice pitch. `minRate` is removed from the spoken configuration.
- The generator adds a native-accent hint per language (`ACCENT_HINTS` in
  `worker/generate_spoken.py`). The fingerprint does not hash the instructions text, so the 66
  committed clips remain valid without regeneration; applying the new accent requires the owner
  to regenerate into a fresh `SPOKEN_OUTPUT` directory with their own key, listen, and replace the
  committed set. This is optional future work, not a PHASE 6 blocker.
- `Listening.tsx` now shows the spoken-notes controls with a dedicated message when an approved
  exercise has no recorded audio, instead of the generic "image only" message.
- All 3 fixes are committed, pushed, and merged through pull request #1; pre-commit and
  `backend/tests/test_spoken_generation.py` are green.

PHASE 6 acceptance uses the local container stand at `http://127.0.0.1:18080/` on 2026-10-01.
Removing duplicate database credentials from the private `.env` resolves the local migration authentication failure.
Migration exits successfully; PostgreSQL, backend, frontend, and OMR report healthy states.
The startup recovery serves speech assets, preserves database passwords and volumes, and does not start Telegram.
Local OMR repair on 2026-10-01 addresses the owner's exercises 32 and 33 without VPS changes.
Disabling indentation-based movement splitting keeps both systems of exercise 32 in one score.
A bounded threshold retry recovers an export for exercise 33 after faint staff detection fails.
The original images remain unchanged and uncommitted; both results require manager review.
Recognition errors remain: exercise 32 has clef and pitch errors; exercise 33 omits a measure and misreads notes.
See `docs/developer/omr-pipeline.md` for the repair evidence and remaining quality limits.
The repair passes 29 targeted backend tests, 22 frontend tests, all quality hooks, and the real container scale regression.
Local Chrome renders both repaired scores in manager review; neither score receives automatic approval.
The repair leaves the owner's Telegram container unchanged.
The owner accepts PHASE 5 after the successful production deployment on 2026-10-01.
The owner reports a new VPS target; this task does not connect to or deploy on that host.
The previous VPS memory failure remains historical evidence, not a measurement of the new host.
The owner confirms PHASE 4 acceptance and authorizes complete PHASE 5 automation on 2026-09-30.
The owner reports unlinking Telegram; this phase does not restore that association.
The previous VPS check records approximately 18 GiB free disk space after owner cleanup.
That host has approximately 116 MiB available RAM, no swap, and no noninteractive sudo access at the recorded check.
The owner confirms all PHASE 3 checks and authorizes complete PHASE 4 automation on 2026-09-29.
The application 404 page is scheduled in PHASE 7.
The owner confirms all PHASE 2 checks and authorizes the complete PHASE 3 without intermediate confirmations on 2026-09-29.
The owner confirms all PHASE 1 manual checks on 2026-09-29.
The owner authorizes the entire PHASE 2 without intermediate confirmations on 2026-09-29.
Manual checks follow the complete implementation.
PHASE 0 is complete with owner-confirmed deployed browser acceptance.
The owner confirms the requested local health-page and PostgreSQL restart scenarios on 2026-09-29.
The owner confirms the remaining bot checks and continuation on 2026-09-29.
PHASE 0.5 is complete; the failed PWA result remains unchanged.

## Completed PHASE 7 plan
- [x] Add deployment storage preflight and reserve checks.
- [x] Add translated application 404 content without changing API or protected-file errors.
- [x] Verify cookie, CSRF, upload, and proxy boundaries; add security headers.
- [x] Add structured logs and verify bounded rotation and worker readiness.
- [x] Add Python and JavaScript dependency audits.
- [x] Review documentation and complete the environment reference and missing guides.
- [x] Prepare the complete final VPS smoke checklist.
- [x] Run local tests, builds, audits, and quality hooks.
- [x] Obtain successful remote CI for the PHASE 7 branch.
- [x] Deploy a verified release through the standard production workflow.
- [x] Obtain owner confirmation of final production smoke acceptance.

## Separate Material Design feature
The owner requests a separate visual migration through `material_design.md` after PHASE 7.
Read-only analysis covers React compatibility, screens, styles, and migration constraints.
The owner starts implementation on 2026-10-01 after the analysis.
Step 2 installs Material UI `9.4.0`, Community DataGrid `9.14.0`, Emotion, and self-hosted Roboto.
React and React DOM remain at `19.3.0`; the installed libraries support React 19.
The official Material UI v9 guide requires Chrome 117+ and Safari 17+ when components use the library.
No charts exist, so Charts remains absent.
Date Pickers requires an additional date library outside the allowed dependencies.
Native date controls remain until the owner approves that exception.
The owner authorizes the remaining steps without intermediate confirmations on 2026-10-01.
The application uses a shared blue-gray theme with light and dark schemes, Roboto, and rounded Material controls.
The theme toggle persists locally without changing account settings or remounting playback.
Login, password, settings, users, exercises, journal, Telegram, student playback, OMR, health, and 404 presentation use Material components.

Both tables use Community DataGrid with existing external server pagination.
Grid sorting, filtering, selection, resizing, menus, and dynamic evaluation remain disabled.
Native selects preserve existing event handlers and keyboard behavior.
Native audio, file inputs, date inputs, and the tempo slider retain their existing operations.

Score rendering keeps its refs and effects; the score surface remains white in both themes.
Inline editors and confirmations remain inline; no new modal flow appears.
The migration removes the unused legacy stylesheet without adding a new CSS file.

The build, linter, all 148 frontend tests, and dependency audit pass.
AST comparison confirms 200 unchanged business hooks and event handlers across 11 feature files.
Theme tests verify text contrast of at least 4.5:1 and input outline contrast of at least 3:1.
Playback tests preserve the audio element, listening session, tempo, and speech player when the theme changes.
Chrome 154 checks 80 screen, width, and theme combinations with synthetic data and the production CSP.
These checks cover widths of 320, 390, 768, and 1280 px, keyboard focus, local fonts, and white score surfaces.

All 3 languages pass browser metadata and toggle checks without application runtime errors or CSP violations.
Screenshots and reproducible browser checks remain in the session artifacts.
Safari 27 refuses driver sessions because **Allow remote automation** is disabled.
This task does not change browser preferences or claim successful Safari automation.

Vite warns about the application and score bundle sizes; the build succeeds.
Business logic, backend APIs, speech clips, private configuration, and deployed services remain unchanged.
Do not include this migration in PHASE 7 or change existing business logic.

### Completed Material Design checklist
- [x] Analyze screens, compatibility, and dependency constraints.
- [x] Install only approved dependencies.
- [x] Add the shared theme, local font, and translated theme toggle.
- [x] Migrate login and account settings.
- [x] Migrate users and journal to Community DataGrid.
- [x] Migrate exercises, OMR review, Telegram, playback, health, and 404.
- [x] Remove unused legacy CSS.
- [x] Verify contrast, focus, mobile layouts, and uninterrupted playback.
- [x] Run the frontend suite, build, audits, and quality checks.
- [ ] Obtain final Safari and real-media visual acceptance.
- [ ] Publish the feature through a new PR and the standard deployment workflow.

## Completed PHASE 6 plan
- [x] Add shared vocabulary and a strict MusicXML sequence parser.
- [x] Add offline OpenAI generation, AAC conversion, resumability, and manifest verification.
- [x] Generate, verify, and commit the real speech clips after private API-key configuration.
- [x] Add approved-only speech, tempo controls, cancellation, and score highlighting.
- [x] Preserve recorded-audio playback and journal boundaries.
- [x] Finish local checks and record their evidence.
- [x] Enable branch CI through the owner-created pull request #1.
- [x] Update user and developer documentation.
- [x] Obtain audible Chrome acceptance after clip generation.
- [x] Obtain owner confirmation of complete PHASE 6 acceptance after production deployment.

## Completed PHASE 5 plan
- [x] Add versioned OMR jobs, leases, retries, review, and protected MusicXML.
- [x] Package Audiveris and implement the bounded worker.
- [x] Add manager review, approved-score rendering, and localized note labels.
- [x] Measure actual recognition quality and verify local browser workflows.
- [x] Deploy the verified OMR release through the standard production workflow.
- [x] Complete developer and user documentation.
- [x] Obtain final owner acceptance after production activation.

## Completed PHASE 4 plan
- [x] Add manager linking, durable imports, role checks, and retry protection.
- [x] Add Telegram polling and reuse protected AAC storage.
- [x] Add the translated manager import interface.
- [x] Verify locally, publish, and replace only the existing bot poller on the VPS.
- [x] Complete documentation and the final manual checklist.

## Completed PHASE 3 plan
- [x] Add per-student pointers and listening sessions with migration `0004_listening`.
- [x] Add sequential/random selection and idempotent, beacon-safe event handling.
- [x] Add student playback, pause/resume, heartbeats, completion, and exit handling.
- [x] Add manager journal filters, pagination, deleted-exercise labels, and translations.
- [x] Complete local PostgreSQL, container, and actual Chrome tab-close scenarios.
- [x] Deploy and verify the exact release over public HTTPS.
- [x] Complete documentation and the final manual checklist.
- [x] Obtain owner acceptance after implementation.

## Completed PHASE 2 plan
- [x] Add exercise and media models, migration, CRUD, soft deletion, and atomic reordering.
- [x] Add bounded uploads, signature checks, original images, AAC conversion, and duration checks.
- [x] Add protected file endpoints and nginx byte-range delivery.
- [x] Add translated exercise forms, upload progress, previews, and drag-and-drop controls.
- [x] Complete browser scenarios, container verification, and deployment.
- [x] Complete documentation and the final manual checklist.
- [x] Obtain owner acceptance after the complete implementation.

## Completed PHASE 1 plan
- [x] Add typed users, sessions, login budgets, and migration `0002_auth`.
- [x] Add scrypt authentication, secure cookies, sliding expiry, CSRF, and login limits.
- [x] Add startup emergency synchronization and all required lifecycle cases.
- [x] Add manager-only user administration, password resets, and session revocation.
- [x] Add persisted language/naming settings and obligatory password changes.
- [x] Add translated login, role guards, user administration, and settings forms.
- [x] Complete automatic browser scenarios and the deployed release verification.
- [x] Complete documentation and the final manual checklist.
- [x] Obtain owner acceptance after the complete implementation.

## Completed PHASE 0 plan
- [x] Add the product layout and locked Python and TypeScript tooling.
- [x] Add the public FastAPI health endpoint and translated React health page.
- [x] Add isolated local Docker images, nginx, Compose, and initial CI.
- [x] Select synchronous SQLAlchemy 2.0 with psycopg 3.
- [x] Add PostgreSQL, an empty Alembic migration, and database settings.
- [x] Add real PostgreSQL tests and migration checks to CI.
- [x] Add shared pre-commit checks locally and in CI.
- [x] Add production Compose configuration and isolated integration checks.
- [x] Add CI-gated image publication and verified release bundles.
- [x] Add targeted VPS deployment, migration, health verification, and rollback.
- [x] Complete the deployed health-page manual check.

## Completed PHASE 0.5 plan
- [x] Prepare the OMR sample set and owner-approved evaluation criteria.
- [x] Run Audiveris in Docker and report recognition results.
- [x] Demonstrate protected `.m4a` delivery with X-Accel-Redirect and Range.
- [x] Prepare the prototype deployment plan for owner review.
- [x] Evaluate Android PWA sharing and record its failure.
- [x] Demonstrate the Telegram replacement with owner-confirmed receipt and playback.
- [x] Record the owner-approved replacement of PWA audio sharing with the bot.
- [x] Complete the remaining Telegram checklist, as confirmed by the owner.

## Done
- PHASE 6 adds shared localized vocabulary, duration parsing, rests, ties, accidentals, and explicit unsupported-score errors.
- Speech uses the Web Audio clock with bounded playback rates, silent tails, tempo controls, and score highlighting.
- Current approval and job version are checked before every start.
- Speech and recorded audio stop each other without changing recorded-audio completion.
- Exit, hidden tabs, logout, score changes, and settings changes cancel pending and scheduled speech.
- The offline generator produces bounded AAC assets with resumable receipts and an atomic verified manifest.
- Conversion tests replace only the OpenAI transport and use real ffmpeg.
- Local checks pass 125 backend tests, 128 frontend tests, and 38 deployment/container tests.
- The 9 generation tests pass with real committed assets; missing assets now fail instead of skipping verification.
- The frontend production build and all 6 pre-commit checks pass.
- Headless Chrome verifies 8 seconds, 4 spoken attacks, silent rests and tails, and 7 written cursor positions.
- That browser check uses synthetic signals; it does not verify actual pronunciation or speaker output.
- Source commits `2a7d008`, `a86e4fa`, and `8285252` belong only to `feat/phase6-spoken-notes`.
- The last fix coordinates speech with manager audio previews as well as student recordings.
- The owner resolves the initial key and PR blockers on 2026-10-01.
- Commit `39545ef` adds 66 real OpenAI speech clips, 66 receipts, and the verified manifest.
- AAC data totals 600676 bytes; the frontend build includes the complete verified set.
- Chrome decodes all 66 clips and verifies 24-second schedules in all 6 language and naming combinations.
- Each schedule contains 15 clips, all accidental suffixes, and a silent final rest.
- Natural quarter notes fit 72 BPM in every combination; actual pronunciation still requires owner acceptance.
- Pull request #1 starts CI; run `36816378757` passes for the earlier source `2782422`.
- Read [the PR checks](https://github.com/mordanov/solfeo-exercises/pull/1/checks) for the current branch result.
- No merge to main, image publication, or deployment occurs.
- Cleanup removes the stopped phase-six browser profile; temporary browser and frontend processes remain stopped.
- `docs/developer/spoken-notes.md` and the student guide contain regeneration and final audible acceptance steps.
- PHASE 5 source `be0000d1e8208489b65fc939b77e1bbb013422e7` passes CI run `36674676116`.
- Run `36675174373` publishes both immutable images and verifies the pulled x86-64 images.
- Its deployment job stops with `OMR_MEMORY_INSUFFICIENT` before image pulls, service changes, or migration.
- Before/after snapshots match all VPS container IDs, start times, image references, and release state.
- Public health remains available; production schema remains `0005_telegram`.
- The job removes temporary registry and SSH credentials after the blocked deployment.
- The verified bundle remains available for an operator-approved retry after provisioning RAM.
- PHASE 5 passes 117 backend tests, 92 frontend tests, and 38 deployment/container tests locally.
- All 6 pre-commit checks pass; the production frontend build also passes.
- PHASE 5 adds migration `0006_omr`, image-bound jobs, expiring claim tokens, retries, and explicit manager review.
- Upload transactions enqueue recognition; replacement and rerun invalidate previous scores.
- Student MusicXML access requires current approval; original images remain available.
- OpenSheetMusicDisplay renders scores, with optional localized lyrics and explicit rendering-error fallback.
- The worker uses pinned Audiveris, a 512 MiB Java heap, a 1024 MiB container limit, and one CPU.
- A native-library failure reveals that JavaCPP needs executable mappings in its bounded temporary filesystem.
- The final container check uses `exec` on that mount and succeeds without network access.
- The local browser verifies actual recognition, side-by-side review, approval, rejection, original fallback, and localized note labels.
- Synthetic scale recognition is 100 %; rhythm recognition is 57.14 %; the accidentals fixture produces no export.
- Private images 1 and 7 reproduce the earlier event sequences; image 6 still fails.
- The measured worker peak is 325550080 bytes; this is not a safe maximum for larger inputs.
- The deployment guard requires 1536 MiB available host memory with default limits.
- The latest VPS check finds approximately 116 MiB available, so activation must wait.
- Only identified obsolete local Solfeo images and cache records are removed during build-space recovery.
- The task does not stop unrelated services or change VPS swap, Telegram associations, or production exercises.
- Cleanup removes the isolated Chrome profile and disposable test database.
- All 5 services in the persistent local development stand remain healthy.
- PHASE 4 is active at `https://solfeo.miveralta.ru/manager/telegram` with `@solfeo_exercises_bot`.
- Source `3e898fc08771dfecfec43533b9ee8a329d4a4f5e` passes CI run `36633406979`.
- Run `36633989417` publishes and verifies both images; its initial deployment fails because the VPS disk fills.
- PostgreSQL temporarily cannot start; its schema remains `0004_listening` before recovery.
- Targeted removal of 8 unused historical Solfeo images restores space without deleting production volumes or files.
- The standard rollout script successfully deploys the same verified bundle through SSH and advances to `0005_telegram`.
- GitHub denies the CLI's request to rerun the failed job; its historical failure remains visible.
- Public HTTPS Chrome verifies linking-code UI, private previews, byte ranges, exercise creation, confirmed replacement, image retention, reload, and logout.
- Independent verification confirms immutable images, bot identity, live polling, readiness, private media mounts, and registry credential cleanup.
- A targeted product-worker restart preserves the durable offset and synthetic import references.
- Shared commit `87fd752` removes only the prototype poller's automatic registration.
- The prototype stays stopped; all its saved audio remains byte-identical.
- All 43 unrelated VPS containers retain exact IDs and start times.
- Product PostgreSQL retains its container ID and data; its start time changes during disk recovery.
- The browser scenarios retain 3 soft-deleted synthetic exercises and 4 synthetic imports, including 2 unused fixtures from a timing retry.
- Both synthetic manager accounts are inactive.
- Cleanup removes the isolated browser profile and disposable local test database.
- The persistent development stand and all 4 product services remain healthy.
- PHASE 4 passes 98 backend tests, 76 frontend tests, and 36 container/release checks locally.
- Local Chrome verifies code generation, AAC preview and seeking, new exercises, confirmed audio replacement, image retention, reload, and logout.
- Simulated Telegram transport tests verify intake, actual conversion, durable offsets, duplicate updates, retry recovery, and notifications.
- Bot startup identity and webhook checks pass against the real Telegram service.
- The private product configuration contains the existing token; only the product worker polls the bot.
- Headless Chrome reports a host audio-renderer error; `--disable-audio-output` permits real decoding and timeline verification.
- The common AAC format remains unchanged; the unsuccessful sample-rate experiment is removed.
- PHASE 3 adds student listening and the manager journal.
- Source `e141b75c803ad56733731965056ef969f0e22c8a` passes CI run `36621440972` and publication/CD run `36621939822`.
- The pulled immutable images pass all 35 container/release checks before deployment.
- Public HTTPS Chrome verifies selection, pause/resume, completion, actual tab closure, journal filters, and retained deleted exercises.
- The tab-close terminal beacon arrives; the journal shows one completed session and one incomplete session.
- Independent VPS checks confirm exact image provenance, migration compatibility, private media, retained journal rows, and registry credential cleanup.
- All 45 other VPS containers retain their exact IDs and start times.
- The 2 synthetic production exercises remain soft-deleted; their 2 journal rows and media remain intact.
- Both synthetic accounts are inactive; real accounts and exercises remain unchanged.
- Cleanup removes isolated Chrome, its temporary profile, and the disposable test database.
- The local development stand and both public health endpoints remain healthy.
- PHASE 3 passes 87 backend tests, 72 frontend tests, and 35 container/release checks locally.
- Real Chrome verifies random history, sequential persistence, pause/resume, heartbeats, completion, and actual tab closure.
- The local journal retains the interrupted session after deletion and supports student/exercise filters.
- Explicit quality checks pass Ruff, mypy strict, ESLint, Prettier, TypeScript, and frontend builds.
- PHASE 2 adds exercise management at `https://solfeo.miveralta.ru/manager/exercises`.
- Publication/CD run `36609836972` succeeds for source `61ed497df1c2bc295363df1f59248f76f251c14c`.
- The published immutable images pass all 34 container/release checks before deployment.
- Public HTTPS Chrome repeats creation, a 3 MiB image upload, Opus conversion, playback, seeking, editing, reordering, reload, and deletion.
- Independent HTTPS checks confirm authenticated byte ranges, anonymous denial, and rejection of direct internal-file URLs.
- The 2 synthetic production exercises remain soft-deleted with their original images and converted audio.
- Independent VPS verification confirms release provenance, `0003_exercises`, private volume ownership, read-only nginx access, and registry credential cleanup.
- All 45 other VPS containers retain their exact IDs and start times, including PostgreSQL, shared nginx, and both prototypes.
- Cleanup stops isolated Chrome, removes its temporary profile, and removes the disposable test database.
- The local development stand remains healthy with its persistent database and media volumes.
- PHASE 2 implementation uses migration `0003_exercises`, protected persistent media, and translated manager forms.
- Source `61ed497df1c2bc295363df1f59248f76f251c14c` passes CI run `36609358064`.
- The suites pass 77 backend tests, 57 frontend tests, and 34 container/release checks.
- Real Chrome 154.0.8037.58 completes local uploads above 1 MiB, Opus conversion, playback, seeking, editing, reordering, and soft deletion.
- Container tests verify original bytes, protected GET/HEAD, normal/suffix/invalid ranges, restart persistence, and denial after deletion.
- Backend tests cover Opus, Ogg, MP3, WAV, AAC, M4A, PNG, JPEG, and WebP.
- Additional checks cover malformed media, byte/pixel/duration limits, chunked requests, permission boundaries, and atomic replacement.
- A replacement regression identifies a foreign-key ordering error; media inserts now complete before exercise updates.
- The shared proxy change `fb55be7` delegates upload limits to the product proxy and permits conversion time.
- Shared nginx validates and reloads without container recreation; its rebuilt image preserves the updated templates.
- The preceding PHASE 1 release uses source `481c72b0cb137aa512798172f377e89e2aca42d8`.
- CI run `36593904877` and publication/CD run `36594338338` succeed.
- The PHASE 1 suites pass 62 backend tests, 46 frontend tests, and 33 deployment/release checks.
- Real Chrome 154.0.8037.58 completes the manager/student workflow locally and over public HTTPS.
- The scenarios cover user creation, obligatory password change, all 3 languages, saved naming, role denial, reset, revocation, activation, and logout.
- The public browser check waits for user-list loading before editing; its first attempt identifies a test-harness timing issue.
- All 4 synthetic VPS accounts remain inactive; their generated passwords do not enter logs or Git.
- The 2 synthetic local accounts remain inactive.
- Cleanup removes the disposable test database and isolated Chrome profile; the development stand remains running.
- The private VPS configuration contains the generated `recovery-manager` credentials and HTTPS-only authentication settings.
- The emergency password remains only in `~/solfeo-production/.env.production`; the operator retrieves it through trusted SSH.
- Independent verification confirms exact image digests, `0002_auth`, secure settings, private network boundaries, and removal of temporary registry credentials.
- All 45 other containers retain their IDs and start times, including PostgreSQL, shared nginx, the PWA, and the Telegram worker.
- PHASE 1 backend tests first fail because the user/session models do not exist.
- UI tests first fail because the account component does not exist.
- Account service tests use real PostgreSQL; no database mocks replace permission or lifecycle checks.
- The migration adds `users`, `login_sessions`, and `login_limits` above the previous empty baseline.
- Login, logout, current-password checks, reset, expiry, and active/role changes enforce session boundaries.
- Startup synchronizes the emergency manager and explicitly fails when recovery cannot reach the database.
- All 3 languages include account forms, permission errors, manager controls, and settings.
- Settings save to PostgreSQL and apply immediately after successful updates.
- Container checks cover real nginx authentication, student API denial, session/settings persistence, and nginx throttling.
- Local Chrome completes the full manager/student scenario, including reset, revocation, activation, persisted settings, and logout.
- The local migration and backend now share one image, preventing a stale migration image during targeted builds.
- Native Safari automation is unavailable because Allow Remote Automation is disabled; no system setting is changed.
- A malformed non-ASCII CSRF header returns the stable rejection code instead of causing a server error.
- The owner confirms Chrome/Safari, RU/EN/ES, status refresh, and failure/recovery checks on the deployed PHASE 0 health page.
- PHASE 0 closes with successful CI, targeted CD, updated documentation, and owner acceptance.
- The initial PHASE 0 release uses source `13a081745a8cf0a5804f75f9a5831c0e9e7f4137`.
- CI run `36585295551` and publication/CD run `36585683212` succeed.
- The runner passes all 30 release and production checks before deployment.
- Actions verifies the owner's SSH configuration with pinned host keys and deploys through the separate product project.
- The VPS stores 3 independent database passwords in private `.env.production`; no password enters Git or output.
- Independent checks confirm the exact image digests, schema heads, container health, loopback-only frontend port, and proxy network membership.
- The deployment removes its temporary registry credentials.
- Chrome 154.0.8037.58 passes public HTTPS, all 3 languages, browser metadata, blocked-API failure, and recovery.
- The browser-only failure scenario does not stop the VPS backend.
- Shared commit `ac76b1c` persists nginx routing and its dedicated proxy network attachment.
- Nginx validates and reloads without container recreation; its rebuilt image preserves the templates for later recreation.
- All 44 pre-existing VPS containers retain their IDs and start times.
- The Telegram worker remains healthy; `/prototype-share/` keeps its route and method restrictions.
- The owner confirms Actions secret setup and requests continuation.
- Rollout tests first fail because the implementation module does not exist.
- The rollout validates archive provenance and hashes before activation.
- Real-container scenarios pass for first deployment, migration failure, health failure, and compatible previous-image recovery.
- The proxy network test confirms that only the product frontend joins the external network.
- The owner confirms final browser acceptance; automated Chrome evidence remains separate from that confirmation.
- The first CI attempt finds a missing temporary parent directory on a fresh runner.
- The rollout fixture now creates that directory explicitly before its disposable container scenario.
- The first product publication succeeds for source `03260e554b13c23b640ef6432775c50b331a7a39`.
- Publication run `36572516719` pulls and checks the published x86-64 images before creating the release bundle.
- The downloaded bundle matches the source files, manifest hashes, and CI run `36572315149`.
- The first publication's prerequisite report finds all 4 SSH secrets unavailable; the owner resolves this before the successful CD run.
- `publish-product.yml` publishes backend and frontend images only for a main-branch commit with matching successful CI.
- It pulls the registry images by digest, checks their source labels, and runs the production container scenarios.
- `deploy/release.py` packages only deployment files and a provenance manifest with immutable image references and file hashes.
- All 13 release-bundle unit tests pass; the runtime dependencies remain unchanged.
- A separate Actions job reports SSH-secret presence without exposing values or accessing the VPS.
- That first publication task does not change shared infrastructure, the active bot, or public routing.
- `deploy/compose.prod.yaml` uses supplied images without building application code on the server.
- It publishes only the frontend on loopback and keeps PostgreSQL on a private network.
- Production uses separate bootstrap administrator, migration owner, and runtime application roles.
- The runtime role can change table data but cannot create, alter, or drop tables.
- Alembic metadata uses a private production schema, inaccessible to the runtime role.
- The development version table remains in `public`; regression checks prevent an unwanted autogeneration diff.
- Production startup waits for migrations; the integration test proves a failed migration blocks a stopped backend from starting.
- Docker logs have configured size and file-count limits.
- The backend suite passes 33 tests; 3 separate production container scenarios pass.
- Production tests verify SQL permissions, hidden privileged credentials, unpublished ports, restart persistence, migration failure, and recovery.
- The tests remove their own temporary projects and volumes without changing the development database or VPS.
- `docs/developer/deploy.md` documents production configuration and the remaining TLS/CD integration.
- The owner confirms that the requested local health-page and database persistence scenarios pass.
- `.pre-commit-config.yaml` runs Ruff, Ruff format, strict mypy, ESLint, Prettier, and TypeScript.
- Python hooks use the locked project tooling; JavaScript hooks use isolated Node.js 22.23.3 and npm 12.1.0.
- The JavaScript hooks use existing workspace dependencies without replacing the system Node.js.
- All 6 hooks reject deliberate lint, formatting, or type errors and pass after those temporary probes are removed.
- Hook configuration changes trigger all checks; prototype-only changes trigger none of these product hooks.
- The repository Git hook is installed locally without overwriting existing hooks.
- CI runs the same configuration through its `checks` job; tests, migrations, and builds remain separate jobs.
- The pre-commit dependency belongs only to development tooling; the runtime dependency export is unchanged.
- The product backend and frontend remain separate from disposable prototypes.
- `/api/health` returns `{"status":"ok"}` without authentication or caching.
- This endpoint checks the process, not PostgreSQL or other services.
- The health page supports English, Russian, and Spanish, with pending, success, failure, and retry states.
- The page shows explicit network, timeout, unavailable-service, and invalid-response errors.
- Language changes update the page, document title, and document language.
- The root `.env.example` documents all settings for this slice.
- Root `uv.lock`, `requirements.txt`, and `package-lock.json` lock dependencies.
- The health-page task passes 12 backend tests, 34 frontend tests, and all configured code checks.
- The database task extends the backend suite to 30 passing tests against real PostgreSQL.
- Ruff, formatting, and strict mypy pass for the database implementation and migrations.
- PostgreSQL 17 uses a pinned image, a persistent development volume, and a loopback host port.
- A separate disposable PostgreSQL stand isolates tests from the development database.
- Alembic revision `0001_initial` records an empty baseline without product tables.
- The migration check covers a fresh schema, repeated upgrade, downgrade, upgrade, and model drift.
- FastAPI owns the connection pool and disposes it during shutdown.
- Request sessions close without automatic commit; explicit transactions commit or roll back.
- Configuration requires a private database password and hides SQL parameter values in errors.
- A private root `.env` uses mode `0600` and remains outside Git.
- Local Compose waits for PostgreSQL and successful migrations before starting the backend.
- A local PostgreSQL restart preserves revision `0001_initial`; native and container migration commands confirm the current schema.
- The production frontend build and isolated Compose healthchecks pass.
- Desktop Chrome verifies the built page, all 3 languages, a stopped backend, explicit failure, and recovery.
- The local stand remains available at `http://127.0.0.1:18080/` for owner checks.
- `.github/workflows/ci.yml` checks the product without publishing or deploying images.
- `docs/developer/setup.md` explains local execution and checks.
- Product authentication, domain models, and Telegram integration are not implemented.
- The working VPS, bot, and superseded PWA deployment remain unchanged in this task.
- The owner approves the PHASE 0.5 plan.
- The owner approves 10 initial images, recognition criteria, and an owner-reviewed engine recommendation.
- Local sample preparation uses images 1 through 10; image 11 remains outside the initial evaluation.
- `docs/developer/omr-pipeline.md` defines sample handling, evaluation, and reporting.
- `docs/DECISIONS.md` records the approved evaluation criteria and the decision to continue with Audiveris.
- Docker access is restored before the OMR run.
- `prototypes/omr/` contains the pinned Audiveris build, offline runner, settings, dependency lock, and 26 passing tests.
- Ruff and strict mypy pass for the prototype.
- Audiveris `5.11.0` runs natively on ARM64 against all 10 selected images.
- The run exports MusicXML for 9 images; image 6 fails during staff detection.
- The reviewed classification is 8 fully recognized, 0 partly recognized, and 2 failed images.
- Images 8 and 9 meet the threshold but contain notation errors.
- `docs/developer/omr-pipeline.md` contains reproduction commands, per-image results, limitations, and the recommendation.
- The owner confirms the engine recommendation on 2026-09-28.
- Manager review and the original-image fallback remain mandatory.
- The owner confirms completion of the OMR manual checks on 2026-09-28.
- `prototypes/files/` contains the local protected-audio stand and its conversion helper.
- FastAPI authorizes the request; nginx serves the `.m4a` through an internal location.
- All 17 files unit tests and 13 live curl cases pass, with Ruff and strict mypy.
- `docs/developer/protected-audio.md` contains measured Range results and the Safari checklist.
- The files prototype containers and networks stop after verification; local media and evidence remain available.
- The owner confirms completion of the protected-audio manual step on 2026-09-29.
- `docs/developer/pwa-share.md` proposes the static HTTPS prototype and the shared-infrastructure changes.
- The owner approves the static PWA scope and deployment plan on 2026-09-29.
- `prototypes/pwa/` contains the local React/i18n shell, share receiver, IndexedDB storage, manifest, icons, and static Docker image.
- All 28 PWA tests, TypeScript, ESLint, Prettier, and the production build pass.
- Desktop Chrome verifies real multipart navigation, receipt, persistent storage, clear, and explicit errors against the built image.
- nginx rejects unhandled POSTs; browser-handled shares remain on the device.
- The local PWA container and isolated test browser stop after verification.
- The owner confirms the GHCR destination and authorizes shared configuration, publication, and targeted VPS deployment.
- DNS and SSH access identify the existing x86-64 VPS.
- Shared configuration adds the prototype without a database, Redis, or landing-page link.
- A prototype-only workflow validates and publishes the x86-64 image without automatic VPS deployment.
- The publishing workflow succeeds for application commit `8efc058`.
- The VPS runs the published image by digest at `https://solfeo.miveralta.ru/prototype-share/`.
- Shared infrastructure commits `900f62e` and `4578b73` persist on `main` and the VPS.
- A one-time `[skip ci]` synchronization prevents the general shared deployment from restarting unrelated applications.
- The hostname certificate is valid; the existing certificate watcher activates HTTPS.
- All 17 public HTTP checks pass, including certificate validation, manifest icons, worker headers, and early POST rejection.
- Desktop Chrome verifies the public share flow, persistence, clearing, and manifest installability without errors.
- All 12 deployed static files match the locally validated build.
- All 41 unrelated containers retain their original IDs and start times.
- `docs/user/pwa-prototype.md` provides the Android acceptance procedure.
- The owner approves the diagnostic follow-up after failed Android acceptance.
- The prototype maps text, title, and URL fields and distinguishes text-only, empty, and unexpected file-field input.
- On-device diagnostics retain field categories, file counts, types, and sizes without message contents, links, or filenames.
- Diagnostics and the last successful file have separate storage and clear actions.
- All 41 prototype tests, ESLint, Prettier, TypeScript, and the production build pass locally and in GitHub Actions.
- Diagnostic source commit `d171be5` is published and deployed by digest.
- Public HTTPS verifies the new manifest mappings and privacy-safe diagnostics through real browser form submissions.
- Failed attempts preserve the last successful file; diagnostic clearing persists independently.
- All 42 other containers, including nginx, retain their IDs and start times during this update.
- The owner confirms successful playback of `199163078.m4a` on 2026-09-29.
- The owner replaces product PWA audio sharing with the Telegram bot.
- The product brief and PHASE 4 plan now specify manager-only Telegram audio import.
- The existing web application scope, authentication, and student restrictions remain unchanged.
- The PWA report remains historical evidence of a failed approach, not an open product acceptance requirement.
- A targeted VPS restart preserves the saved audio hash, bot identity, and update checkpoint.
- The avatar worker accepts figures that touch a cell edge, regenerates an invalid sheet once, and logs `error_code` and the failing cell.
- Generated avatars get a 31st face-circle image (`portrait.png`, best effort); the chooser gallery shows it.

## PHASE 0.5 deployment record
- The files protocol checks and owner manual step are complete.
- Basic authentication is a localhost-only prototype assumption, not a product authentication decision.
- The HTTPS deployment works, but Android messenger sharing fails owner acceptance.
- On 2026-09-29, the owner reports "No audio file was received" after sharing from Telegram or WhatsApp.
- The owner repeats the Android test and reports a current attempt timestamp, `EMPTY_SHARE`, 0 file fields, and no form fields.
- The receiver observes an empty form; the point where data disappears remains unknown.
- Message-only sharing remains an unconfirmed hypothesis.
- The owner approves a separate Telegram prototype and deployment on the existing VPS.
- The bot implementation accepts allowlisted private attachments and saves validated AAC audio without creating exercises.
- All 27 bot tests, Ruff, and strict mypy pass locally and in CI, including actual Opus-to-AAC conversion.
- A non-root, read-only Docker check verifies simulated Telegram ingestion through real AAC conversion and durable checkpointing.
- Bot source `ac3442e` is published; shared configuration `3b94837` is synchronized to the VPS.
- The VPS `.env` pins the bot image digest.
- The published x86-64 image passes an offline runtime check on the VPS using simulated Telegram and actual AAC conversion.
- All 43 existing containers retain their original IDs and start times.
- The owner supplies the dedicated bot configuration privately.
- Telegram identity and webhook checks pass locally and from the VPS without exposing credentials.
- Shared commit `5e2f6c0` registers and activates only the Telegram worker.
- `https://t.me/solfeo_exercises_bot` is active, healthy, and polling Telegram.
- Both configuration files use mode `0600`; no token or allowed user ID enters Git or command output.
- All 43 pre-existing containers remain unchanged during activation.
- The owner confirms successful real audio receipt on 2026-09-29.
- The reported bot reply identifies `199163078.m4a`, with a size of 636644 bytes.
- The owner subsequently confirms that the remaining manual checks pass on 2026-09-29.
- This confirms the voice, forwarded-audio, document, and unauthorized-sender cases requested in the previous handoff.
- The owner does not supply device versions or a per-message evidence record.

## Next step
- Publish the completed Material Design branch through a new PR; do not reuse merged PR #3.
- Complete the visual checks in both user guides, especially Safari and real-media playback.
- Preserve the accepted product behavior, disk guards, container limits, and compatible rollback.
- Reuse `docs/developer/smoke-check.md` after future production changes.
- Retain the owner-accepted PHASE 5, PHASE 6, and PHASE 7 results; do not regenerate the existing speech clips.
- Preserve prototype files and the historical PWA deployment.

## PHASE 0 boundaries

The owner requests continuation after completing PHASE 0.5 checks.
The first implementation task establishes a local health page, not a complete production deployment.
The database task adds synchronous SQLAlchemy and an empty Alembic baseline.
It does not add users, exercises, journal records, or worker jobs.

Keep authentication in PHASE 1 and exercise/file operations in PHASE 2.
Integrate the bot with manager accounts and exercises in PHASE 4.
Do not copy disposable prototype authentication into the product.

## Acceptance details
- The owner confirms the requested local scenarios without browser versions or a detailed browser matrix.
- The owner confirms the requested final VPS scenarios on 2026-09-29.
- Owner-tested browser versions and a per-browser evidence matrix are not supplied.

## Final PHASE 1 manual acceptance
- [x] Sign in as a manager in Safari and Chrome.
- [x] Create a student and complete the obligatory password change.
- [x] Confirm language and naming persistence after reload and a new sign-in.
- [x] Confirm student denial at `/manager/users`.
- [x] Confirm password reset, deactivation/reactivation, and logout behavior.

The owner confirms all PHASE 1 checks on 2026-09-29.
Chrome automation covers these scenarios separately.
Safari 26.6.2 refuses WebDriver sessions until Allow Remote Automation is enabled.
The task does not change that system permission or claim automated Safari success.

## Final PHASE 2 manual acceptance
- [x] Create an exercise with a real Opus file and image in Chrome and Safari.
- [x] Play and seek forward and backward after conversion.
- [x] Edit metadata and replace attachments.
- [x] Reorder exercises by dragging or buttons; confirm the order after reload.
- [x] Confirm soft deletion and explicit errors for invalid or missing files.
- [x] Confirm student denial at `/manager/exercises`.

The owner confirms all PHASE 2 checks on 2026-09-29.

## Final PHASE 3 manual acceptance
- [x] Complete the first audio exercise and interrupt the second by closing the tab.
- [x] Confirm completed and incomplete sessions in the manager journal.
- [x] Confirm pause/resume uses one row and replay after natural completion uses another.
- [x] Check sequential persistence, random selection, Previous, and no automatic playback.
- [x] Check journal filters and retention after exercise deletion.
- [x] Confirm student denial at `/manager/journal` in Chrome and Safari.

The owner confirms all PHASE 3 checks on 2026-09-29.

## Final PHASE 4 manual acceptance
- [x] Link a normal manager account to the bot.
- [x] Import real voice, forwarded audio, and audio documents.
- [x] Create an exercise and replace another exercise's audio.
- [x] Play and seek in Chrome and Safari; confirm original-image and journal retention.
- [x] Check unsupported input, size errors, and retry behavior.
- [x] Confirm unlinking and student denial.

The owner confirms all PHASE 4 checks, Telegram unlinking, and VPS disk cleanup on 2026-09-30.

## Final PHASE 5 manual acceptance
- [ ] Review and approve a real image in Chrome and Safari.
- [ ] Confirm original-image fallback before approval and after rejection or replacement.
- [ ] Check note labels for letters and solfège in all 3 languages.
- [ ] Toggle labels during audio playback without interrupting the listening session.
- [ ] Check failed recognition, retry, and student permission boundaries.

Production deployment and owner acceptance remain pending.

## Manual checks the owner must do
- [x] Confirm that images 1 through 10 represent the intended exercises.
- [x] Review the criteria in `docs/developer/omr-pipeline.md`.
- [x] Review the local MusicXML against the original images, especially images 7–9.
- [x] Review the image 6 failure and the manual event counts.
- [x] Confirm the recommendation to continue with Audiveris.
- [x] Complete the protected-audio manual step, as confirmed by the owner.
- [x] Confirm one successful real audio receipt through the Telegram bot.
- [x] Confirm successful playback of the saved audio.
- [x] Select Telegram instead of PWA sharing for product audio import.
- [x] Verify preserved audio and checkpoint state after a targeted VPS restart.
- [x] Complete the real-message bot checklist, as confirmed by the owner.
- [x] Confirm that the local health page opens.
- [x] Confirm that the local schema revision survives a PostgreSQL restart.
- [x] Confirm Chrome and Safari behavior, all 3 languages, and failure/recovery during final VPS acceptance.
- [x] Configure the 4 deployment secrets, as confirmed by the owner.

The superseded Android PWA checklist is no longer required.
The new local health-page procedure appears in `docs/user/manager.md` and `docs/user/student.md`.
The owner confirms final PHASE 0 browser acceptance at the public HTTPS address.
The final PHASE 5 procedure is in `docs/user/manager.md`.
After deploying the avatar fix, generate a new avatar: it must reach review, and its saved-gallery tile must show a round face (job 1 failed and must be recreated).

## Known issues
- PHASE 5 and PHASE 6 have owner acceptance; automated Safari evidence remains unavailable.
- PHASE 7 has final owner acceptance after successful production deployment on 2026-10-01.
- Earlier publication run `36867434244` fails at the former OMR RAM guard; run `36921037861` deploys successfully.
- Native Chrome DOM automation times out; local HTTP and React tests do not replace final browser acceptance.
- The owner-created PR resolves the initial CI blocker without changing CLI permissions.
- The previous VPS check finds approximately 18 GiB free disk space but insufficient RAM for PHASE 5 activation.
- The owner postpones deployment and reports a new host; this task does not verify or change that host.
- The initial PHASE 4 CD attempt fails from disk exhaustion; the verified SSH recovery succeeds.
- The current CLI cannot rerun Actions jobs with its token; GitHub returns a permission error.
- The owner confirms real Telegram acceptance and subsequently unlinks the association.
- Image 6 produces no MusicXML; image 7 receives 46 % recognition.
- Images 8 and 9 receive 95.35 % and 88 %, with important errors despite their `fully recognized` labels.
- Local artifacts are under `prototypes/omr/output/20260928T201957Z-84f49a71/`.
- Files evidence is under `prototypes/files/output/curl-20260928T204244Z-ec7ed479/`.
- The owner reports completion of the files manual step; device versions and the test setup are not recorded.
- Basic authentication remains a disposable prototype mechanism; PHASE 1 uses independent product session cookies.
- The files prototype image remains local; operating-system package repositories remain unpinned.
- The PWA keeps only the latest successful share and rejects files above 25 MiB by default.
- Desktop browser checks do not establish Android sharing compatibility.
- The owner reports failed Android messenger sharing; successful desktop checks do not override this result.
- The PWA diagnostic receiver observes an empty form; the loss point remains unknown and is no longer under active investigation.
- PWA browser and static-server evidence remain in `prototypes/pwa/output/`.
- Samples and generated MusicXML remain local; a fresh clone does not contain them.
- The HTTPS PWA runs at `https://solfeo.miveralta.ru/prototype-share/`.
- The onboarding guide is `../web-projects/web-folders/documentation/onboarding.md`.
- npm 10 fails during fresh workspace dependency resolution; npm 12.1.0 resolves the declared dependencies.
- Anonymous language selection remains temporary; authenticated language and note naming now persist per user.
- Product CD and public nginx integration are active; the owner confirms final VPS acceptance.
- The PHASE 0 image cannot recognize `0002_auth`; rollback across that schema boundary requires a compatible forward fix.
- PHASE 1 images cannot recognize `0003_exercises`; PHASE 2 recovery requires a compatible image.
- PHASE 2 images cannot recognize `0004_listening`; PHASE 3 recovery requires a compatible image.
- PHASE 3 images cannot recognize `0005_telegram`; PHASE 4 recovery requires a compatible image.
- PHASE 4 images cannot recognize `0006_omr`; recovery after that migration requires a compatible image.
- Schema-incompatible rollback stops the product services and requires operator recovery; no automatic database downgrade occurs.
- The current CLI credential cannot manage repository Actions secrets: the public-key API returns HTTP 403.
- The deployment job confirms valid SSH configuration and removes its temporary registry credentials.
- Development still uses the bootstrap database role; the separate production configuration does not.
