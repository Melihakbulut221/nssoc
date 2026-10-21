# Exact postroute input preparation
The independent cloud job preserves the existing complete boot/protocol/RTL and
native geometry proof chain through current152762-cell fanout candidate.
It stops before any fresh-routing preparation or native DRT call.
The original20/4/8/8ns clocks,5percent derate, single-thread STA and three cell
corners remain. All resolved Liberty/LEF/SDC/RCX/PDK and candidate state files
are copied byte-for-byte with per-file SHA256 and an exact complete manifest.
Missing or nonportable inputs fail and are reported; no replacement library is
silently selected. Inherited timing metrics and SPEF are discarded.
This package is a prerequisite only. It cannot accept routing or timing.
After complete route and geometry proof, use the actual routed ODB for fresh
native antenna/disconnection, OpenRCX and original guarded three-corner STA.
Nominal RC remains unqualified for foundry RCmin/max signoff.
Current native DRT/PLL/TX jobs are unaffected.

Initial39627219647 failed before packaging because raw user config inherits
STA_CORNERS from the PDK. The failure is preserved. The corrected job restores
the exact resolved current-candidate native stage config from39494338440,
requires all raw user settings to match it, and packages both configurations.
No missing corner is filled with a guessed default and no timing gate changes.
