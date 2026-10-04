# Manager guide

This document explains accounts, exercise management, the listening journal, and manual acceptance.

Prerequisites:
- Use Chrome 117+ or Safari 17+.
- Obtain manager credentials privately from the operator.
- Open `https://solfeo.miveralta.ru/`, or use the local stand from `docs/developer/setup.md`.

## Create a game profile

1. Click the round Unicorn badge at the upper left.
   The player list opens.
2. Click **Create player**.
   The form shows a name field and eligible accounts.
3. Enter a player name.
4. Select an eligible account.
   Use **Next** and **Previous** to find accounts beyond the first page.
5. Click **Create player**.
   The new profile appears with level 1 and a Unicorn avatar.
6. Select the profile.
7. Choose the difficulty and number of notes.
8. Set **Show the sound hint** and **Show the correct answer**.
   The hint starts enabled; the correct answer starts hidden.
   Each disabled switch shows **+1 point**; each enabled switch shows **0 points**.
9. Click **Let's go!**.
   The piano loads before the first round starts.

Only managers create profiles.
The selector excludes inactive accounts, accounts with profiles, and the emergency manager.
Each eligible account can receive one new profile.
An empty selector shows **All players already have game accounts** instead of a form.
Existing profiles and their progress remain unchanged.
The badge shows **Play Guess the Note** on hover or keyboard focus.
The existing **Guess the Note** menu link remains available.
Each student sees profiles assigned to their account.
The application does not create a profile automatically when an account signs in.
A failed request shows an error and **Try again**, not an empty player list.

Rounds use standard treble and bass clefs.
The treble clef identifies G4 on the second line from the bottom.
The bass clef identifies F3 on the fourth line from the bottom.
The symbols retain their proportions across interface fonts, themes, and screen sizes.
Treble questions use natural notes C4–A5; bass questions use E2–C4.
The 7 buttons answer C through B without selecting an octave.
Buttons and revealed answers follow the account's note naming and interface language.
The optional correct answer appears to the right of the centered playback control during feedback.
The staff keeps the same size across clefs and note counts.
Each disabled switch adds 1 point once per completed round, including a losing round.
These points do not change XP or the requirement for 5 correct answers to win.
Easy allows 13 s per question, Medium 10 s, and Hard 7 s.
The difficulty changes the time limit, not the notes or scoring.
The switches retain their choices between rounds until you leave the game area.
Piano failures permit retry without consuming a round.

## Listen to game notes

1. Click the white round **Listen to notes** button below the staff during a round.
   You hear all shown notes in order, with their written pitches and octaves.
2. Click **Stop listening** to stop early.
3. Click **Listen to notes** again to repeat the notes.
4. Select an answer with a colored note button.
   The answer stops the hint and plays the selected piano pitch.
   Its octave matches the current question note, even when you choose the wrong name.

The white button appears only when **Show the sound hint** is enabled.
Listening plays sampled piano notes without spoken names or automatic answers.
Matching answer buttons and hints use the same piano sound and octave.
It does not pause the timer or change points.
Playback stops when time expires or you leave the round.
A playback failure shows an error and permits another attempt.

## Game avatar management

1. Open **Guess the Note** and select a player.
2. Click **Choose avatar**.
   The window shows all 11 built-in characters, including Lion, Panda, and Rhino.
3. Select a character.
   The player retains XP and uses the corresponding avatar level.
4. Inspect the player cards and game results.
   Cards show the saved appearance; results show the emotion associated with the correct-answer count.
5. Use the question mark only when you want to generate an original character.
   The student guide explains preview, acceptance, and discard.

Managers bypass the daily generation quota.
The private deployment configuration still needs `OPENAI_API_KEY`.
Generation remains unavailable without that setting.
The avatar worker starts with the normal application release.

## Change the visual theme

1. Click **Use dark theme** or **Use light theme** above the account area.
   The page changes colors without resetting forms or stopping playback.
2. Reload the page.
   The browser retains the visual choice.

The light/dark mode stays in this browser, not in your account settings.
The score surface stays white in both themes.
User and journal tables retain the existing Previous and Next controls.

Screens below 600 px show labeled cards instead of wide tables.
Each card retains every field and permitted action.
Larger screens retain the existing tables.
Date filters continue to use your browser's native date controls.

## Customize appearance

1. Open **Settings** and find **Appearance**.
2. Select light and dark schemes independently.
   Classic, Forest, Warm, and Plum provide coordinated component colors.
3. Select Roboto, System, or Serif and a base size of 16, 18, or 20 px.
4. Select the example's Light or Dark mode.
   The example shows backgrounds, panels, text, a field, and buttons without changing the active page.
5. Click **Save appearance**.
   Your account retains the appearance across devices.
6. Click **Restore standard appearance** when necessary.
   The example returns to Classic, Roboto, and 16 px.
7. Click **Save appearance** to commit the restoration.
   Language and note naming remain unchanged.

Appearance changes preserve form values, recordings, speech tempo, and score engraving.
The header's light/dark mode remains browser-local.
An error retains the draft instead of claiming that saving succeeds.
See the student guide for the complete appearance procedure.

## Mobile layout checklist

1. Open all manager pages at 320, 360, 390, and 430 px.
2. Check both themes and all 3 interface languages.
3. Inspect long names, exercise titles, descriptions, and selected values.
4. Edit a user and use Previous and Next.
   Cards retain the same actions and pagination as tables.
5. Select dates and files in Safari on an iPhone.
6. Open recognition review and inspect every measure and note label.
   Review shows only the score; the exercise preview retains the original image.
7. Turn the device during audio preview or spoken playback.
   The score adjusts to the available width without resetting playback.
8. Confirm a Telegram replacement and inspect its selected exercise and confirmation control.

## Material Design visual checklist

1. Open login, Settings, Users, Exercises, Listening journal, and Telegram imports in Chrome and Safari.
2. Check both themes at desktop and mobile widths.
3. Use Tab to reach links, controls, table actions, and buttons.
   The current control shows a visible focus indicator.
4. Check Russian, English, and Spanish labels.
5. Create and edit a user, reset a password, and test both pagination buttons.
6. Upload files, reorder exercises, and review a recognized score.
7. Apply date filters and inspect a deleted exercise in the journal.
8. Confirm a Telegram audio replacement and preview its audio.
9. Change the theme during playback.
   Playback and the current form values remain unchanged.

## Review recognized notes

1. Upload an exercise image.
   Recognition enters the queue; students continue to see the original image.
2. Click **Review recognition** beside the exercise.
3. Click **Refresh status** after processing.
   The recognized score appears without a duplicate original image.
4. Compare every note, rest, duration, clef, accidental, and measure with the original image in the exercise preview.
5. Select **Show note names** to check labels in your saved naming system.
6. Click **Approve** only when the score is correct.
   Students can now see the rendered score.
7. Click **Reject** when the score contains errors.
   Students see the original image instead.
8. Click **Run recognition** to retry or process an existing image.
   This action withdraws the previous score until you approve the new result.

The exercise preview retains the original image even when recognition fails.
One exercise can continue on several lines; a line break does not require a separate upload.
The worker retries missing staff detection once with a threshold for faint lines.
If staff detection still fails, the page requests a clearer image.
Some clear images still produce incomplete or incorrect notation.
Check every line and measure even when recognition succeeds.
Reject the score when it contains a stray chord, an extra measure, or a missing measure. Reshoot the image.
An approved score with these errors also makes the spoken notes feature refuse that score.
See `docs/PRODUCT_BRIEF.md` (Photo quality requirements) for how to photograph an exercise before upload.
Use the original image when repeated recognition fails.
Replacing an image always requires new recognition and approval.
Editing text or replacing audio preserves the current score.

## Final PHASE 5 manual checklist

Complete these checks after the operator resolves the production memory constraint and deploys PHASE 5.

1. Repeat the review procedure with a real image in Chrome and Safari.
2. Confirm that an unapproved or rejected score leaves the original visible to a student.
3. Approve a correct score and open it as a student.
4. Check note names in all 3 languages with letters and solfège settings.
5. Toggle labels during audio playback and confirm uninterrupted playback.
6. Replace the image and confirm that the old approved score disappears.
7. Retry a failed recognition and confirm the visible status and retained original.
8. Confirm that students cannot approve, reject, or rerun recognition.

## Sign in to the application

1. Enter your username and password.
2. Click **Sign in**.
   The Users page opens for an active manager.
3. Change your password if the page requires it.
   User administration becomes available after a successful change.

An incorrect password shows an error without granting access.
Repeated attempts can temporarily block sign-in.
The default login session lasts 90 days and extends during authenticated use.
Click **Sign out** to end the current session.

The operator manages emergency credentials through private server configuration.
Do not share those credentials in chat or store them in this repository.
Use an ordinary manager for daily work.
The manager interface cannot edit the emergency account or reset its password.

## Create and manage users

1. Open **Users**.
   The page shows usernames, names, roles, and active status.
2. Enter a unique username, first name, last name, and temporary password.
3. Select **Student** or **Manager**.
4. Keep the password-change option selected when the user must choose a private password.
5. Click **Create user**.
   The new user appears in the list.
6. Give the credentials to that user through a private channel.

Usernames accept 3–64 ASCII letters, digits, dots, underscores, or hyphens.
They must start with a letter or digit.
The application treats uppercase and lowercase usernames as the same username.
Passwords require at least 8 characters by default; the operator can adjust that minimum.
The application never shows stored passwords.

1. Click **Edit** beside another ordinary user.
2. Change the names or role.
3. Click **Save user**.
   The list shows the updated account.
4. Enter a new temporary password in the password-reset form when required.
5. Select whether the next sign-in requires a password change.
6. Click **Reset password**.
   Existing sessions for that user stop working.
7. Click **Deactivate** beside a user to remove access.
   The account remains in the list, and existing sessions stop working.
8. Click **Activate** to permit sign-in again.
   The account uses its current password.

You cannot change your own role or active status through user administration.
Use **Settings** to change your own password.
Role changes also end the target user's existing sessions.

## Change your settings

1. Open **Settings**.
2. Select Russian, English, or Spanish.
   The application saves the choice and immediately changes its text and browser title.
3. Select letters or solfège note names.
   The application saves the naming choice.
4. Reload the page.
   Both choices remain.
5. Use **Save settings** to retry if a failed request prevents saving.
   An explicit error remains visible until a successful retry.

The letters option uses C–D–E by default.
The solfège option uses do–re–mi.
The Exercises page previews original images and converted audio.
Students have a separate listening interface with approved scores and spoken notes.
The Telegram prototype remains separate and does not create exercises.

## Final PHASE 1 manual checklist

Complete this checklist after the full implementation and automated deployment.

1. Sign in as a manager in Chrome and Safari.
2. Create a student with an obligatory password change.
3. Sign in as that student in a separate browser session.
4. Complete the password change.
5. Change the language and note naming.
6. Reload the page and sign in again.
   Both settings remain.
7. Open `/manager/users` as the student.
   The page refuses access, and no manager controls appear.
8. Reset the student's password as the manager.
   The previous student session stops working.
9. Deactivate and reactivate the student.
   Sign-in follows the selected active status.
10. Sign out and reload the page.
    Protected information does not remain visible.

The service-status panel checks backend liveness, not exercises or the Telegram bot.
The historical `/prototype-share/` route remains available independently.

## Manage exercises

1. Open **Exercises**.
   The page shows active exercises in their saved order.
2. Click **Create exercise**.
   The exercise form opens.
3. Enter a title and description.
4. Enter an optional category or level.
5. Attach a PNG, JPEG, or WebP image, an audio file, or both.
6. Click **Save exercise**.
   The page shows upload progress, then processing.
7. Wait until the form closes and the exercise appears.
   The server confirms persistence before the interface refreshes the list.
8. Click the audio play control.
   Playback starts only after your action.
9. Move the audio position control to check seeking.

The default limits permit 20 MiB images and 50 MiB audio files.
Audio must not exceed 1800 seconds by default.
The operator can change these limits.
The server checks actual file contents and converts audio to AAC.
It preserves original image bytes.
The upload percentage measures transfer, not conversion completion.
Do not close the page during processing.
After a network failure, refresh the list before retrying.

1. Click **Edit exercise** beside an exercise.
2. Change its metadata or select replacement files.
3. Leave file fields empty to keep the current files.
4. Select a removal checkbox only when another attachment remains.
5. Click **Save exercise**.
   The list shows the updated exercise and previews.

1. Drag an exercise to another position.
   The list refreshes after the server saves the order.
2. Use **Up** and **Down** when dragging is unavailable.
3. Reload the page.
   The saved order remains.

1. Click **Delete exercise**.
   The page requests confirmation.
2. Click **Confirm deletion**.
   The exercise disappears from the active list.

Deletion preserves the database record and files.
The interface does not offer restoration in PHASE 2.
The product bot supplies imports; only the website applies them to exercises.

## Final PHASE 2 manual checklist

1. Open Exercises as a manager in Chrome and Safari.
2. Create an exercise with a real `.opus` audio file and an image.
3. Wait for transfer and conversion to finish.
4. Play the audio and seek forward and backward.
5. Confirm the image and description.
6. Edit metadata without replacing files.
7. Replace audio and confirm the new playback.
8. Create another exercise and change their order.
9. Reload the page and confirm persistence.
10. Delete one exercise and confirm its removal.
11. Try an unsupported file and a form without attachments.
    The page shows errors without creating an exercise.
12. Open `/manager/exercises` as a student.
    The page refuses access.

## Read the listening journal

1. Open **Listening journal**.
   The page shows the newest listening sessions first.
2. Select a student or exercise when needed.
3. Set From date and To date to filter session start times.
4. Click **Apply filters**.
   The table and total show matching sessions.
5. Use **Previous** and **Next** for additional pages.
6. Click **Refresh journal** to load recent events and filter options.

Dates use the browser's displayed time zone.
Both selected calendar dates are inclusive.
Each row shows the student, original exercise title, start, last activity, end, maximum position, duration, and completion.
The completion rule is 90 % of duration or a natural ended event.
Seeking can satisfy the maximum-position rule; it does not measure uninterrupted listening.

**No end event received** does not mean the student is still listening.
A browser crash or lost connection can prevent the final event.
The start and last heartbeat preserve the session independently.
Deleted exercises remain in the journal with a deletion label.
Replacement audio does not change earlier session durations.
Manager audio previews do not create student journal records.

## Final PHASE 3 manager checklist

1. Prepare at least 2 audio exercises.
2. Ask a student to complete the first and close the second during playback.
3. Open Listening journal.
4. Filter by that student.
   The first row is complete; the interrupted session is incomplete.
5. Confirm that pause and resume did not create duplicate rows.
6. Filter by exercise and dates.
7. Delete one test exercise.
   Its journal entry remains with the original title, duration, and deletion label.
8. Repeat the browser scenario in Safari.

## Import audio from Telegram

1. Sign in with a normal manager account.
2. Open **Telegram imports**.
3. Click **Create linking code**.
   The page shows a private `/start` command and its expiry time.
4. Click **Open bot**.
5. Copy the complete command into the bot's private chat.
   The bot confirms the association.
6. Send an audio file, voice message, or audio document.
   The bot confirms storage after conversion.
7. Return to **Telegram imports**.
8. Click **Refresh imports**.
   Your audio appears with its processing status.
9. Play the preview.
10. Select **Create a new exercise** or an existing exercise.
11. Set the title and description.
12. Confirm audio replacement if the selected exercise already has audio.
13. Click **Save exercise**.
    The page confirms the saved exercise.

Files must fit Telegram's 20 MB download limit and the application's media limits.
Send the actual file, not a message link.
For WhatsApp audio, save or share the file into Telegram first.
Text alone does not create an import.
The bot does not automatically create exercises.

Only your manager account can see your staged imports.
Repeated delivery and repeated Save requests do not create duplicate exercises.
Replacement preserves the original image and earlier listening sessions.
Failed imports show an error and a Retry button.
Refresh the list after retrying.

Do not share linking codes.
Click **Unlink Telegram and cancel codes** to revoke the association.
Password changes, resets, deactivation, and role changes require a new association.
The emergency manager must link again after each backend restart.
Normal manager associations survive ordinary restarts.

## Final PHASE 4 manual checklist

1. Link a normal manager account to `@solfeo_exercises_bot`.
2. Send a voice message, forwarded audio, and audio as a document.
3. Refresh the import list.
   Each accepted attachment appears once.
4. Create an exercise from one import.
5. Replace another exercise's audio from a second import.
   Its original image and journal remain.
6. Play and seek in Chrome and Safari.
7. Send text, an unsupported file, and an oversized attachment.
   The bot does not create an exercise from them.
8. Unlink Telegram.
   New attachments cannot enter that manager's import list.
9. Confirm that a student cannot open `/manager/telegram`.

## Recover from an unknown page

1. Open an unknown application address.
   The page shows **Page not found**, not a manager form.
2. Select the required language.
   The message and home link change language.
3. Click **Go to home**.
   The application opens the home page and restores your authenticated access when the session remains valid.

This page does not reveal protected exercises or bypass sign-in.
An API or protected-file error does not use this application page.

## Final PHASE 7 manual checklist

1. Complete `docs/developer/smoke-check.md` with the operator after production deployment.
2. Repeat account, upload, seeking, OMR, speech, Telegram, and journal checks in Chrome and Safari.
3. Confirm the unknown-page message and home link in Russian, English, and Spanish.
4. Confirm that student accounts still cannot use manager operations.
5. Confirm that existing exercises, original images, imports, and journal rows remain unchanged.

## Check spoken notes

The operator must first publish the generated voice files.
Speech controls appear only for an approved score, including the manager's review page.
Approval permits playback; a review preview alone does not.

1. Open an approved exercise in the recognition review.
2. Click **Speak notes**.
   The application checks current approval again before playback.
3. Compare each spoken name with the original image.
4. Check the language and naming choice in **Settings**.
5. Reject incorrect recognition instead of accepting incorrect spoken notes.
6. Repeat the student guide's PHASE 6 checklist in Chrome and Safari.
7. Check the journal after a student uses speech alone.
   Speech does not create or complete a recorded-audio listening session.

Missing voice files require operator generation, not another OMR attempt.
The application chooses a safe tempo before playback and remembers adjustments in this browser.
The saved tempo separates accounts, exercises, score versions, languages, and naming choices.
The slider can extend below its usual minimum for short notes.
See the student guide for mobile installation and browser language defaults.
The Service status panel appears only in Settings.
See `../developer/spoken-notes.md` for generation and supported notation.
