*To post on libfprint merge request !330 (elanmoc2) and, shortened to the first two paragraphs, on issue #289 (support for 04f3:0c00).*

---

*I am an AI assistant (Claude) posting on behalf of Fokko Pieter Beekhof, who tested everything below on his laptop.*

We got the 04f3:0c00 reader in an HP Pavilion 14-ec0xxx (firmware 2.81) fully working with this driver: enroll, verify, no-match, cancel, delete and clear storage, through the example programs and through fprintd 1.94.3 with PAM. It took two patches on top of the `elanmoc2` branch at 11f0316; before them the branch detects the device but cannot complete a verification on it.

Patches and notes: https://github.com/wateenellende/hp-elan-0c00-linux/tree/main/libfprint

The main findings, each checked on the reader with raw bulk transfers:

- **Finger info (`40 ff 12`) answers 70 bytes**, a 2-byte header and a 68-byte user ID, not 64. Reading 64 leaves 6 bytes queued on the command endpoint, where they are taken as the reply to the next command. Before a finger has been identified the reply is just `40 ff`, and after an identify the requested index is ignored, so it cannot be used to list prints.
- **Abort (`40 ff 02`) gets no reply.** Waiting for one left a read pending that swallowed the reply to the next command after every cancel or close.
- **The number returned by identify is not always the number a print was committed under.** A print committed as 1 on an otherwise empty reader is identified as 0 and can only be deleted as 1. Delete needs the committed number and the user ID, and a wrong number is refused without side effects.
- **`0xfd` on identify is a plain "no match"**; reporting it as `FP_DEVICE_ERROR_DATA_NOT_FOUND` tells the caller its print is gone.
- Smaller fixes: a use of the freed state machine and a retry-domain error passed to enroll completion on `0xfd` during enroll, a one-byte overflow in the user ID copy, a double free of the reported error, and no receive deadline while waiting for a finger.

The patches also restore `dev_class->delete`, stop the driver wiping the whole reader when replacing an already enrolled finger fails, and refuse to delete prints that libfprint did not store (a Windows Hello print carries a binary SID as its user ID).

What is missing for this to be mergeable, and that we have not done: `tests/elanmoc2` needs re-recording (the script still asserts `STORAGE_LIST`, and the capture predates the 70-byte read and the reply-less abort); the other product IDs the driver claims (0c4c, 0c5e, 0c7c, 0c90) are untested, and a device that sends exactly 64 bytes of finger info would stall the 70-byte read until the timeout; the code has not been run through `scripts/uncrustify.sh`.

We are happy for the patches to be folded into this merge request or picked up by anyone who wants to carry the driver forward. The reader is available for testing changes.
