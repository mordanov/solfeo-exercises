# Student guide

This document explains student listening, account settings, and access boundaries.

Prerequisites:
- Use Chrome 117+ or Safari 17+.
- Obtain your username and temporary password privately from a manager.
- Open `https://solfeo.miveralta.ru/`.

## Change the visual theme

1. Click **Use dark theme** or **Use light theme** above the account area.
   The page changes colors without changing the exercise or stopping playback.
2. Reload the page.
   This browser retains your visual choice.

The theme does not change saved language or note naming settings.
The score surface stays white in both themes.

## Material Design visual checklist

1. Open the student area and Settings in Chrome and Safari.
2. Check both themes at desktop and mobile widths.
3. Check all 3 interface languages.
4. Use Tab to reach the listening mode, playback controls, navigation, and theme toggle.
   The current control shows a visible focus indicator.
5. Play and seek a real recording.
6. Change the theme during playback.
   The current exercise and playback position remain unchanged.
7. Speak an approved score and change its tempo.
8. Change the theme during speech.
   The tempo and speech playback remain unchanged.
9. Confirm that manager pages still refuse access.

## Sign in and change a temporary password

1. Enter your username and password.
2. Click **Sign in**.
   The student area opens, unless a password change is required.
3. Enter the current password and a new password when requested.
4. Repeat the new password.
5. Click **Change password**.
   The student area becomes available.

An incorrect password shows an error.
New passwords require at least 8 characters by default.
Repeated attempts can temporarily block sign-in.
Ask a manager to reset a forgotten password.
A manager reset ends your existing sessions.

## Save your settings

1. Open **Settings**.
2. Select Russian, English, or Spanish.
   The application saves the language and immediately changes the page text and browser title.
3. Select letters or solfège note names.
   The application saves that choice.
4. Reload the page.
   Both choices remain.
5. Click **Save settings** to retry a failed save.
   The page confirms success or shows an explicit error.

Letters use C–D–E by default; solfège uses do–re–mi.
You can also change your password in Settings.
A successful password change ends your other sessions.

## Access and sign-out

Students cannot list, create, edit, deactivate, or reset other users.
Opening `/manager/users` does not grant manager access.
Students can view original images and listen to exercise audio.
An approved score replaces the original image in the listening area.
Unapproved, rejected, or failed recognition keeps the original image visible.
Rendering or access errors show an explicit message and the original image.
Students cannot approve or change recognition results.
Only managers can read the listening journal.
Opening `/manager/journal` does not grant journal access.
Opening `/manager/telegram` does not grant Telegram import access.
Opening `/manager/exercises` does not grant exercise management rights.
The separate Telegram prototype does not grant product import rights.

1. Click **Sign out** on a shared device.
   The sign-in form replaces protected information.
2. Reload the page.
   The application still requires sign-in.

The normal session survives browser reloads and backend restarts.
Browser privacy settings can remove stored cookies.
The service-status panel confirms backend liveness only.

## Final PHASE 1 manual check

1. Repeat sign-in and obligatory password change in Chrome and Safari.
2. Check all 3 languages and both naming choices.
3. Confirm the saved choices after reload and a new sign-in.
4. Verify that `/manager/users` refuses access.
5. Confirm that manager reset or deactivation ends your access.
6. Verify sign-out after page reload.

## Listen to exercises

1. Open **Student area**.
   The saved sequential exercise appears with its description and approved score or original image.
2. Press the audio play control.
   Playback starts, and the application records a listening session.
3. Pause and resume when necessary.
   Both actions belong to the same listening session.
4. Use the audio position control to seek.
   The journal records the maximum position reached, not total listening time.
5. Click **Next** or **Previous**.
   The application ends the current session and shows another exercise without automatic playback.

Reaching 90 % of the duration or receiving the natural ended event marks the session complete.
Completion saves the next sequential exercise but leaves the current exercise visible.
Replay after natural completion creates a new listening session.
The ordered sequence wraps after the last exercise and before the first.
Reload or a new sign-in restores the saved sequential pointer.
An image-only exercise has no audio control and creates no journal row.
An approved exercise without recorded audio shows the spoken notes controls instead of an audio control.
Speech still does not create a journal row.

1. Select **Random** in Listening mode.
   The application selects a different exercise when more than one exists.
2. Click **Next** for another random selection.
3. Click **Previous** to revisit the previous random selection from this page.
4. Select **In order** to restore the saved sequential position.

Reload starts in sequential mode and clears the page's random history.
Changing modes ends the current listening session without automatic playback.
Settings navigation and tab closure also attempt to send an end event.
The last accepted heartbeat keeps a valid journal row even if the browser cannot send that event.

A delivery error pauses playback and shows an error.
Check your connection before pressing play again.
Reload if the manager replaces the current audio.
The application does not silently switch a running player to a replacement file.

## Show note names

1. Open an exercise with an approved score.
2. Select **Show note names**.
   Labels appear below the written notes.
3. Open **Settings** to change letters or solfège naming and the interface language.
4. Return to the exercise and select **Show note names** again.
   Labels use the saved settings.
5. Clear the checkbox to restore the unlabelled score.

Rests have no note-name label.
Accidentals use musical sharp and flat symbols.
Changing this checkbox does not stop or recreate the audio player.
The checkbox is local to the current score, not a saved account setting.

## Final PHASE 3 listening checklist

1. Sign in as a student in Chrome and Safari.
2. Play an exercise, pause, and resume.
3. Complete the first exercise.
4. Click **Next** and play the second exercise for at least 5 seconds.
5. Close the tab before reaching 90 %.
6. Ask the manager to check one completed session and one incomplete session.
7. Reopen the application and confirm the saved sequential position.
8. Check Random, Previous, and return to In order.
9. Confirm that `/manager/journal` refuses student access.

## Use spoken notes

The release includes the existing 66 voice files; no regeneration is required.
The voice speaks note names; it does not sing.
The page identifies the voice as AI-generated.

1. Open an exercise with an approved score.
   The **Spoken notes** controls appear.
2. Set the tempo with the slider.
   The label shows beats per minute.
3. Click **Speak notes**.
   The cursor follows the spoken sequence.
4. Click **Stop speaking** when necessary.
   Playback and pending preparation stop.
5. Lower the tempo if a name cannot fit its note.
6. Click **Speak notes** again after changing the tempo.
   Playback restarts from the beginning.

Rests remain silent, and tied notes have one combined duration.
A short spoken name can leave silence inside a long note.
Sharps and flats follow the note name.
Your saved language and naming settings determine the speech.
Unsupported notation or missing clips produce an error, not guessed speech.

Speech pauses the audio recording, and the recording stops speech.
Leaving the page, hiding the tab, or signing out also stops speech.
Speech does not complete the audio recording's listening session or advance the saved sequential pointer.
Image-only speech creates no journal row.

## Final PHASE 6 manual checklist

1. Repeat the checks in Chrome and Safari after the operator publishes the clips.
2. Check all 3 languages with letters and solfège naming.
3. Listen for correct names, clear speech, and no singing or added words.
4. Check whole notes, quarter notes, dotted notes, rests, and ties.
5. Check sharp, flat, double-sharp, double-flat, and natural pitches.
6. Change the tempo and confirm complete words without overlap.
7. Toggle note labels during speech and confirm stable timing and cursor position.
8. Alternate speech and the exercise recording.
   Only one plays at a time.
9. Stop during loading, hide the tab, navigate, and sign out.
   No delayed sound starts.
10. Ask the manager to verify unchanged audio completion after speech alone.
11. Ask the manager to revoke approval before another start.
    Speech cannot start from the stale page.

## Recover from an unknown page

1. Open an unknown application address.
   The page shows **Page not found**.
2. Select Russian, English, or Spanish.
   The page translates the message and home link.
3. Click **Go to home**.
   The application opens your student area when your session remains valid.
4. Sign in when your session expires.
   The application restores your saved settings.

The unknown-page screen does not play audio or create a listening session.

## Final PHASE 7 manual checklist

1. Repeat the final listening and spoken-notes checks in Chrome and Safari after deployment.
2. Confirm all 3 unknown-page translations and the home link.
3. Reload `/student` and `/settings` directly.
   Valid routes remain available.
4. Confirm that manager pages still refuse your access.
5. Ask the manager to verify journal retention after deleting a test exercise.
