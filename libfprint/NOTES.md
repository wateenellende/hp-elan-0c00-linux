# elanmoc2 on 04f3:0c00: what was wrong and what the reader does

These notes go with the two patches in this directory, which apply on top of the `elanmoc2` branch of `depau/libfprint` at commit `11f0316` (the branch behind libfprint merge request !330).

With them, the reader in an HP Pavilion 14-ec0xxx enrolls, verifies and deletes through fprintd 1.94.3 and PAM. Without them, the branch tip detects the device but cannot complete a verification on it.

## Tested

Hardware: 04f3:0c00 "ELAN:ARM-M4", bcdDevice 2.81 (`40 19` answers `02 81`), elementary OS 8 / Ubuntu 24.04, kernel 7.0.

| Operation | Result |
|---|---|
| Enroll, 8 stages, with and without retries | committed |
| Enroll with another print already stored | committed |
| Enroll a finger that is already enrolled | old print deleted, new one stored |
| Verify enrolled finger | match |
| Verify unknown finger | no match |
| Cancel a pending verify, twice in a row | sensor responsive afterwards |
| Delete, and delete again | removed; second call is a no-op |
| Clear storage | count 0 |
| fprintd-enroll, fprintd-list, PAM | working |

Not tested: 0c4c, 0c5e, 0c7c and 0c90 (no hardware); suspend/resume; a stored finger other than the one being verified.

## What the sensor does (observed with raw bulk transfers)

- **Finger info (`40 ff 12 idx`)** answers 70 bytes: `40 00` plus a 68-byte user ID. Before any finger has been identified it answers `40 ff`. After an identify it returns the identified finger's info whatever `idx` is, so it cannot be used to list prints.
- **Abort (`40 ff 02`)** gets no reply on either IN endpoint, pending operation or not.
- **Identify (`40 ff 03`)** returns a number that is not always the number the print was committed under. A print committed as 1 on an empty sensor is identified as 0.
- **Delete (`40 ff 13`, `f0|(n+5)`, user ID)** succeeds only when both the committed number and the user ID match; otherwise `40 ff`, with no side effects. It works without a prior identify.
- **Enroll (`40 ff 01 n 8 stage 0`)**: with no prints stored, n = 0..9 waits for a finger and n >= 10 answers `40 dd`. With one print stored, n = 0 answers `40 ff` at once and n = 1 is accepted.
- A Windows Hello print stores a binary SID as its user ID (`01 05 00 00 00 00 00 05 15 00 00 00 ...`).

## Changes

Patch 1, `elanmoc2: Fix protocol handling for 04f3:0c00 and restore delete`:

- Read 70 bytes of finger info, accept and validate short replies.
- Send abort without waiting for a reply; synchronously on close.
- Unknown finger on verify/identify is a "no match", not `DATA_NOT_FOUND`.
- `0xfd` during enroll is a retry; fixes a use of the freed state machine.
- One result per verify/identify action; `FPI_MATCH_ERROR` for retries; no double free of the reported error.
- No receive deadline while waiting for a finger.
- Clear the in-flight command when a send fails or is cancelled.
- Fix a one-byte overflow in the user ID copy.
- When re-enrolling a finger, try each number for the delete instead of wiping the sensor; never delete prints not stored by libfprint.
- Match prints on the user ID only.
- Fall back to the next number if the sensor refuses the one chosen for a new print.
- Restore `dev_class->delete`.

Patch 2, `examples: Only list prints from devices that can list`: `verify` and `identify` now check `FP_DEVICE_FEATURE_STORAGE_LIST` before listing.

## Open points

- `tests/elanmoc2` is not updated. The script still asserts `STORAGE_LIST`, which the branch tip already dropped, and the capture predates the 70-byte read and the reply-less abort. It needs re-recording on hardware.
- The 70-byte finger info read is confirmed on 0c00 only. Short replies are accepted, but a device that sends exactly 64 bytes would stall that read until the timeout.
- Not run through `scripts/uncrustify.sh`.
