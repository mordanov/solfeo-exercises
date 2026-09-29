# Manager guide

This document explains sign-in, user administration, settings, and the final PHASE 1 checklist.

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
Exercise rendering and playback belong to later phases.
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
