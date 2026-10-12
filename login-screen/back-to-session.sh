#!/bin/bash
# Run from a text console when the lock screen cannot be passed: unlocks your graphical
# session and switches back to it, without ending it.
set -euo pipefail

trap 'echo; echo "STOP: failed at line $LINENO."' ERR

found=0
for s in $(loginctl list-sessions --no-legend | awk -v u="$USER" '$3 == u { print $1 }'); do
  type="$(loginctl show-session "$s" -p Type --value)"
  if [ "$type" = x11 ] || [ "$type" = wayland ]; then
    sudo loginctl unlock-session "$s"
    sudo loginctl activate "$s"
    found=1
  fi
done

if [ "$found" = 1 ]; then
  echo "DONE: switched to your graphical session."
else
  echo "STOP: no graphical session of $USER was found."
fi
