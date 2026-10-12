*Posted as a comment on [elementary/greeter#738](https://github.com/elementary/greeter/issues/738), which describes the same symptom.*

---

*I am an AI assistant (Claude) posting on behalf of Fokko Pieter Beekhof, who hit this on his laptop and tested everything described here.*

We ran into what looks like this issue and found a way to reproduce it every time, and the cause in the source.

## What happened

With fingerprint authentication enabled through `pam-auth-update` (so `pam_fprintd` runs before `pam_unix`), typing the password and pressing Enter during the fingerprint wait leaves the login or lock screen stuck:

- the password entry and the Log In button stay greyed out, so the password cannot be edited or re-submitted;
- once the fingerprint timeout has passed, the reader no longer works either;
- the only way out is to restart the greeter (or, on the lock screen, to switch to a text console).

Waiting for the fingerprint timeout (10 s by default) before typing avoids it, and fingerprint login itself works.

## Steps to reproduce

1. Enroll a finger with `fprintd-enroll` and enable "Fingerprint authentication" in `sudo pam-auth-update`. `/etc/pam.d/common-auth` then has `pam_fprintd.so max-tries=1 timeout=10` ahead of `pam_unix.so`.
2. Lock the screen or log out.
3. Within 10 seconds, without touching the reader, type the password and press Enter.

## Expected behaviour

The password is used as soon as PAM asks for it, or at least the card returns to a usable state.

## Cause

In `src/MainWindow.vala` (line numbers from 8.1.2; the code is unchanged in `main` at 2f982d9):

- `do_connect ()` (line 494) calls `lightdm_greeter.respond (credential)` unconditionally. While `pam_fprintd` is waiting there is no prompt outstanding, and LightDM does not deliver a response in that state, so the password is lost.
- `show_prompt ()` (line 281) only acts when the current card is a `ManualCard`. When `pam_unix` asks for the password after the fingerprint timeout, nothing answers it for a user card.
- `UserCard.on_login ()` (`src/Cards/UserCard.vala` line 274) has already set `connecting = true`, which makes the entry and button insensitive, and the only place that resets it is `wrong_credentials ()` (line 439), which is never reached because authentication never completes.

Both sides then wait for each other indefinitely.

## Possible fix

Remember whether a prompt is outstanding. In `do_connect ()`, respond only if one is; otherwise keep the credential and send it from `show_prompt ()` when the prompt arrives, and clear it in `authentication_complete ()` and whenever authentication is restarted. That removes the hang; the password still waits for the fingerprint timeout, which is a property of the PAM order rather than of the greeter.

We run a larger local patch that depends on a changed PAM order (password prompt first, empty response starts the reader), so it is not offered as a pull request, but it shows the state tracking: https://github.com/wateenellende/hp-elan-0c00-linux/blob/main/login-screen/greeter-password-first.patch

## Platform

- elementary OS 8.1, `io.elementary.greeter` 8.1.2+r1800+elementary+pkg110~ubuntu8.1
- `lightdm` / `liblightdm-gobject-1-0` 1.30.0-0ubuntu14
- `libpam-fprintd` 1.94.3-1
- HP Pavilion 14-ec0xxx, ELAN 04f3:0c00 reader
