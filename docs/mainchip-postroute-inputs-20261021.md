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

Run39628968402 demonstrated that per-step config omits flow/STA settings
and resolves pdk_dir macro/CDL paths, so literal raw-to-step comparison fails.
The corrected source is the original run39436610858 full run/resolved.json.
The independently reconstructed raw config must exactly equal that run's
trial-config.json; both files and the filtered step config are hash verified.
No setting is inferred from absence and no corner/gate is removed.

## Exact PDK and runtime dependencies

Run 39631393774 reproduced the original user configuration and restored the complete resolved flow configuration, then failed before native analysis because its preparation-only path had not invoked the PDK setup normally performed by the LibreLane CLI. Its failure and complete missing-file inventory remain in the immutable Release and the new rejection receipt.

The replacement uses the pinned AppImage's Ciel API with the exact original revision c4b8b4e5e7a05f375cca3815d51b3a37721fbf5c and default/sg13g2_stdcell libraries. All five upstream release archives are independently checked for byte length and SHA256; every installed member must equal the corresponding archive member. No SRAM or library overlay is introduced. The tool-owned base.sdc is copied from its original AppImage path, retains its hash and original namespace, and is recorded separately from project files. DESIGN_DIR remains recorded metadata; no old route is created.

This is an input preparation repair, not a routed geometry, antenna, RC, timing or full-PHY acceptance. Original clocks, corners, uncertainty, derating, candidate geometry and functional proofs remain mandatory.
