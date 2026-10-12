#!/bin/bash
# Undoes install.sh: the stock login screen and the stock /etc/pam.d/lightdm come back.
set -euo pipefail
BIN=/usr/sbin/io.elementary.greeter
HELPER=/usr/local/libexec/pam-authtok-is-empty
PAM=/etc/pam.d/lightdm
PAM_BACKUP=/etc/pam.d/lightdm.before-login-fix

trap 'echo; echo "STOP: failed at line $LINENO."' ERR

if [ -e "$PAM_BACKUP" ]; then
  sudo cp -p "$PAM_BACKUP" "$PAM"
  sudo rm -f "$PAM_BACKUP"
fi
sudo rm -f "$HELPER"

if dpkg-divert --list "$BIN" | grep -q .; then
  sudo rm -f "$BIN"
  sudo dpkg-divert --local --rename --remove "$BIN"
fi
test -x "$BIN"
grep -q '^@include common-auth$' "$PAM"
echo "DONE: stock login screen and login rules are back; they are used the next time the login or lock screen starts."
