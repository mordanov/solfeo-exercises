# Manager guide

This document explains accounts, exercise management, the listening journal, and manual acceptance.

Prerequisites:
- Use Chrome or Safari.
- Obtain manager credentials privately from the operator.
- Open `https://solfeo.miveralta.ru/`, or use the local stand from `docs/developer/setup.md`.

## Sign in

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
Passwords require at least 12 characters by default; the operator can adjust that minimum.
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
Students now have a separate listening interface; score recognition belongs to a later phase.
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
The bot prototype remains independent and cannot create product exercises yet.

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
