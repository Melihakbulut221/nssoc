# Routed-netlist native functional boot

Prepared, not dispatched or verified. The producer is detailed-route run 44263061910 at 921f49a0c7becd72e58177e19404b45e91575e63. Wait for terminal success and independent artifact review before dispatch. Pin reviewed producer artifact IDs and digests in the shared route admission before dispatching either extraction or this boot.

`scripts/cloud_core_only_routed_boot.py` restores the complete mapping/CTS/clock-split/repair/routing provenance chain, obtains the netlist from the routed step's own state, and copies those exact bytes into a separate simulation input directory. The original mapping is never overwritten. Immutable boot-ROM manifests and firmware come from the authenticated mapping build.

The previously qualified native boot harness is fetched from commit 31cb1846a8cf0eb683344e24c27a25438c22a75c, checked against explicit SHA-256 values and qualification commit 603c4d763128a3c238363c7d15e153eccff565e4, then placed in an isolated cloud output directory. Source-bound producer harness files remain unchanged. Native IHP models, Icarus >=13, no preload, four system SRAM macros, PCIe off, Ethernet absent, and the system MBIST monitor remain required. The runner fails on unsuccessful commands, missing results, failed boot checks, or altered inputs.

The branch workflow uses the same pinned OSS CAD suite as the original successful boot. No local execution. Artifacts include the routed simulation netlist, harness, results and logs. A pass is functional boot/MBIST evidence only: no SDF, exhaustive equivalence, setup/hold, transistor LVS, padframe, ESD or manufacturing acceptance is implied. Physical release gates remain open.
