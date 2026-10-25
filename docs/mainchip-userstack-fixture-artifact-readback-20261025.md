# Exact rejected GDB fixture artifact readback

The original hosted fixture run 40172782148 at 023fe9ce2b2226e3858c5436ebe48f929aed734d failed before sample zero and accepted no controls. GDB returned 1; its actual 155-byte stderr is preserved only in authenticated artifact 12590911691. The cause remains unknown until that text is recovered.

This source adds a mutually exclusive readback-only mode to the existing registered workflow. It authenticates the exact terminal run/job, artifact API digest and 13,840-byte ZIP, checks all 12 members, verifies the original rejected result and exact stderr hashes, and logs the complete small JSON plus verbatim bounded stderr. The ZIP is read only in GitHub-hosted RAM. Eight real synthetic ZIP corruptions must be rejected first. The fixture job is skipped in this mode; no debugger, chip restore, simulation or new fixture trajectory is run.

Source authorization is initially false pending independent review. The original fixture source, its 24 required controls, native controller and no-progress rejection remain unchanged. A successful readback establishes the contents of the prior failure only; it does not qualify the fixture or routing.
