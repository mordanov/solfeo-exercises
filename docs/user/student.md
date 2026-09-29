# Student guide

This document explains student sign-in, password changes, settings, and access boundaries.

Prerequisites:
- Use Chrome or Safari.
- Obtain your username and temporary password privately from a manager.
- Open `https://solfeo.miveralta.ru/`.

## Sign in and change a temporary password

1. Enter your username and password.
2. Click **Sign in**.
   The student area opens, unless a password change is required.
3. Enter the current password and a new password when requested.
4. Repeat the new password.
5. Click **Change password**.
   The student area becomes available.

An incorrect password shows an error.
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
Exercises, playback, and the journal arrive in later phases.
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
