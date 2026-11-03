# Cloud continuation — checkpoint v358

Updated: 2026-11-03T22:52:50.528447+00:00

## Full nonlinear N1 and N2 comparison runs

N1 run41733225660/source9bba58288772dd2bee9dab142e391d0616737973/release433297951 remains independently live. No waveform success is claimed. Its native job126255793850 is in the full assembly/256bit loaded simulation step. Keep its exact handle and preserve any eventual diagnostics, failed electrical results or publication errors.

N2 run41734419971/source81555c8ba8357f2874fab2c5bb0c3378305e3501 on codex/cdr-mos650-full-composition-n2/release433304261 has been dispatched as the required next nonlinear partition comparison. It uses the same actual650 geometry, current MIM-aware metal, physical gate-port model, intrinsic model variant, Sparse1.3 engine, original startup environment,256bit sources,34.25ns stop,0.3125ps maxstep,loads and unchanged acceptance gates. Every physical MOS has two equal-dimension projected copies of multiplicity0.5; total physical multiplicity stays1. Both outcomes and later refinements must be measured, not inferred from workflow status.

The N2 branch additionally preserves large native archives in ordered byte parts capped at1800000000 bytes if necessary. archive-parts.json records original joined hash, complete part order/lengths/hashes. Every part and concatenation is independently reread before deleting only the redundant unsplit archive. Smaller archives remain unchanged. Source controls exercise boundaries, reversed ordering and truncation; these are transport checks, not electrical acceptance.

Mainchip41699812301/source9430a57873e78d3c283b531da8e8e74da416f297 remains live. Root soc_top.v is still67444 bytes/SHA256b782a7fbe7b9ad5abb0db67bd132907d71e1ef43c9451b9befa2f356b77d4847: external link/training and byte packet inputs remain. Passing this route will not close complete serial PHY integration. Full recovered-clock Gen3x4 and final serial-integrated chip setup/hold remain unqualified.

Observed 2026-11-03T22:52:50.528447+00:00:
- 41699812301: in_progress/None
- 41733225660: in_progress/None
- 41734419971: in_progress/None


## History and execution
Previous actual route and failure handoff:
https://github.com/Melihakbulut221/nssoc/blob/ec9f2c5331844e0d16180f9b605ee74efe018dda/CLOUD_RESUME.md
All earlier sources, complete reports and failed runs remain preserved.
All native CAD/geometry/runtime/electrical payloads stay cloud-only. The local
workspace is empty; source and derived-text API coordination uses RAM.
The8-hour monitor remains read-only with automatic_native_dispatch=false.
Poll existing exact handles; do not restart on observation timeouts.
Full serialPHY, completed mainchip routing and final setup/hold must all
pass real complete verification before the overall goal is complete.
