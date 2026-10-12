# HP fingerprint reader 04f3:0c00 on Linux

Working fingerprint login for the ELAN match-on-chip reader `04f3:0c00` ("ELAN:ARM-M4") found in HP Pavilion laptops, plus a fix for elementary OS's login screen so that fingerprint and password can both be used without waiting for one another.

Tested on one machine: HP Pavilion 14-ec0xxx, reader firmware 2.81, elementary OS 8.1 (Ubuntu 24.04 base), fprintd 1.94.3.

This work was done by an AI assistant (Claude) working with and on behalf of Fokko Pieter Beekhof, who tested every step on the hardware. Nothing here is supported by HP, ELAN, libfprint or elementary.

## 1. The driver (`libfprint/`)

libfprint has no driver for this reader. Davide Depau wrote one, `elanmoc2`, which is still an open merge request ([libfprint !330](https://gitlab.freedesktop.org/libfprint/libfprint/-/merge_requests/330)). On this reader his branch detects the device but cannot complete a verification. The two patches here apply on top of his `elanmoc2` branch at commit `11f0316` and make enroll, verify, delete and clear work.

What was wrong, and what the reader actually does on the wire, is in [libfprint/NOTES.md](libfprint/NOTES.md).

Build and install next to the distribution's libfprint (nothing packaged is replaced):

```
sudo apt install fprintd libpam-fprintd git build-essential meson ninja-build pkg-config \
  libglib2.0-dev libgusb-dev libnss3-dev libpixman-1-dev libgudev-1.0-dev libssl-dev \
  libcairo2-dev libudev-dev systemd-dev
git clone --branch elanmoc2 https://gitlab.freedesktop.org/depau/libfprint.git
cd libfprint
git checkout 11f0316d069cc90c154c8cb0e46478388c5e2a74
git am /path/to/this/repo/libfprint/000*.patch
meson setup build --prefix=/usr/local --libdir=lib/x86_64-linux-gnu --buildtype=release \
  -Ddoc=false -Dgtk-examples=false -Dintrospection=false -Dinstalled-tests=false \
  -Dudev_rules_dir=/etc/udev/rules.d -Dudev_hwdb_dir=/etc/udev/hwdb.d
ninja -C build
sudo ninja -C build install
sudo ldconfig && sudo systemd-hwdb update && sudo udevadm control --reload
fprintd-enroll
sudo pam-auth-update     # tick "Fingerprint authentication"
```

`sudo ninja -C build uninstall && sudo ldconfig` removes it again.

`libfprint/probe.py` is a read-only probe that talks to the reader over raw usbfs (firmware version, number of stored prints); it needs write access to the USB device node.

Not tested: the other IDs the driver claims (0c4c, 0c5e, 0c7c, 0c90), and suspend/resume while a verification is running. The driver's recorded-device test in the libfprint tree has not been updated.

## 2. The login screen (`login-screen/`)

With the standard setup (`pam_fprintd` before `pam_unix`), elementary's login and lock screen has two problems:

- A password typed while the system is still waiting for a finger is dropped, and the card stays greyed out until the session is restarted. This is a bug in the greeter, present in 8.1.2 and in `main` as of 2026-10-11; see [upstream-reports/elementary-greeter-issue.md](upstream-reports/elementary-greeter-issue.md).
- Even without that bug, a password has to wait out the fingerprint timeout, and on the lock screen the reader is only available for the first seconds after locking.

The fix here changes the order instead of running the two in parallel:

- `pam/lightdm-auth.pam` replaces the `@include common-auth` line in `/etc/pam.d/lightdm`. The password prompt comes first, an empty response starts the reader, and a wrong password fails at once. It uses stock PAM modules and the three-line helper `pam/pam-authtok-is-empty` (install it as `/usr/local/libexec/pam-authtok-is-empty`, replace `@HELPER@` with that path and `@TIMEOUT@` with a number up to 99).
- `greeter-password-first.patch` applies to elementary greeter 8.1.2. The login screen then sends the empty response itself, so the reader is ready as soon as the screen appears, and a password typed during the fingerprint wait restarts authentication and is used immediately. When the reader's wait expires on an idle screen it is started again on the next key press, pointer movement or wake-up.

`sudo`, text consoles and everything else keep using `common-auth`.

The patch only makes sense together with the changed PAM order, so it is not proposed to elementary as it is. Build the greeter with `meson setup build --prefix=/usr --sysconfdir=/etc && ninja -C build src/io.elementary.greeter` and install `build/src/io.elementary.greeter` over `/usr/sbin/io.elementary.greeter` (use `dpkg-divert` to keep the packaged one). `uninstall.sh` and `back-to-session.sh` are the undo and recovery scripts used on the test machine; read them before running them, they assume that machine's paths.

`pamtest.py` drives a PAM stack from a private directory without root, which is how the new order was tested before it was installed.

Known limits: each time the reader is started the log gets one `pam_unix ... authentication failure` line for the empty response; `pam_fprintd`'s unlimited wait (`timeout=-1`) returns immediately in fprintd 1.94.3, hence the 99-second maximum.

## Licence

The patches are under the licence of the project they apply to (libfprint: LGPL-2.1-or-later; elementary greeter: GPL-2.0-or-later). Everything else in this repository is MIT.
