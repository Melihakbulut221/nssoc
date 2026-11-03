# Cloud continuation — checkpoint v357

Updated: 2026-11-03T22:43:52.850617+00:00

## All five actual650 circuits assembled; first loaded startup failed

Run41732402949/sourceb3768d5f3201cf661b15bc85f431ba46be3eee48 completed with FAILURE. All N1/2/4/8/16 actual650 nonlinear compositions and their native source/terminal/probe bindings completed. The full N1 nominal_late simulation ran12.0759s and failed at3.125fs with only two waveform rows. Native returncode0 did not mean success: diagnostics rejected a missing spinit warning, temperature NaN, five singular matrix warnings and timestep collapse. Full electrical thresholds were not reached or passed. All outputs remain in release433293515; see the failure receipt.

Successor run41733225660/source9bba58288772dd2bee9dab142e391d0616737973 on codex/cdr-mos650-full-composition, release433297951, restores the original bench-local spinit/SPICE_SCRIPTS startup environment omitted by the first adapter, and tests the same full circuit with Sparse1.3 instead of KLU. Both changes are recorded; they are not a proven root cause or repair. It retains original models,256bits,34.25ns stop,0.3125ps maxstep,loads and all diagnostics/electrical gates. New derived-early artifact allows diagnostics to be read before large native publication finishes. Do not claim passing assembly implies transient, closed-loop or PHY acceptance.

Mainchip41699812301/source9430a57873e78d3c283b531da8e8e74da416f297 remains the independently monitored original full64 routing attempt. Full serialGen3x4, final routed mainchip and setup/hold remain open.

Observed 2026-11-03T22:43:52.850617+00:00:
- 41699812301: in_progress/None
- 41732402949: completed/failure
- 41733225660: in_progress/None


## History and execution
Previous actual route and failure handoff:
https://github.com/Melihakbulut221/nssoc/blob/1e61227646a982c88d5bcfd72a4b25ba05087485/CLOUD_RESUME.md
All earlier sources, complete reports and failed runs remain preserved.
All native CAD/geometry/runtime/electrical payloads stay cloud-only. The local
workspace is empty; source and derived-text API coordination uses RAM.
The8-hour monitor remains read-only with automatic_native_dispatch=false.
Poll existing exact handles; do not restart on observation timeouts.
Full serialPHY, completed mainchip routing and final setup/hold must all
pass real complete verification before the overall goal is complete.
