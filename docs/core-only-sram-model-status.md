# Core-only SRAM source/model status

The pinned IHP PDK c4b8b4e5e7a05f375cca3815d51b3a37721fbf5c contains exactly the same 2048x64 SRAM GDS and CDL bytes as the earlier isolated-bitcell diagnostic43563445727. That diagnostic reports NoMatch and ERROR_OR_INCOMPLETE_DIAGNOSTIC; it is neither a passed macro LVS nor a complete chip comparison. Its top-name and merge-control adaptations must remain visible. Source identity alone does not rerun or validate its whole analysis. Evidence: docs/evidence/core-only-sram-source-inventory-20261118.json.

IHP issue239 remains open and PR1121 is not merged as checked on2026-11-18. The maintainer's response discusses a likely dimension bug; it does not provide a production waiver. Do not silently edit reference widths, ignore internal devices, or promote a blackbox comparison to full LVS. Links: https://github.com/IHP-GmbH/IHP-Open-PDK/issues/239 and https://github.com/IHP-GmbH/IHP-Open-PDK/pull/1121.

The three supplied SRAM Liberty sources declare25C/1.20V,125C/1.08V,and-55C/1.32V. The core fast stdcell corner is labelled-40C, while its macro file is-55C. This is a mixed-temperature analysis and requires explicit qualification; a filename mapping does not prove its conservatism. File existence and timing/power tables are not comprehensive characterization or silicon qualification. The evidence hashes upstream source bytes, not the external runtime filesystem used by earlier STA jobs.

The pinned PDK tree contains one OpenRCX rules file, libs.tech/librelane/IHP_rcx_patterns.rules. No distinct RCmin/RCmax files were found in that complete tree. The inherited extracted-flow audit accordingly labels its extraction nominal-only and unqualified for RCmin/max. A successful nominal SPEF/STA run cannot close that production gate by itself.
