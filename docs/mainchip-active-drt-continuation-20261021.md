# Continue the exact active detailed router across workflow runs

The initial active-routing capture in run39502505171 is preserved. Its cross-runner job must finish successfully with observable new native progress before this new workflow can consume the resulting process. Push events run structural controls only; a native continuation requires an explicit immutable descriptor.

The descriptor contains run, attempt1, group mainchip-active-drt-cross, source_head, controller_sha256, summary_sha256 and parts_sha256. The source run must be completed/successful and the report must prove a saved active process, a single entrypoint, restored process, cross-runner progress, the exact OpenROAD ELF and no completed route. Wrong hashes, source/workflow/controller identity, missing process, live/rejected source and completed route are rejected. Fifteen synthetic negative controls test descriptor validation; they are not native checkpoint proof.

The continuation controller is an exact source-delta adaptation of the existing frozen controller. Only cross-run source selection, explicit legacy/new controller compatibility, distinct-run guard, bounded segment duration and low-disk early checkpoint policy change. Native image, generated Tcl, original routing parameters, saved log/work prefixes and CRIU checkpoint content remain independently verified. The same native process continues; no old initial capsule or cold restart is substituted.

Choose only the most recent successful checkpoint after confirming no newer continuation is live. Never dispatch another run merely because observation timed out. A segment can request600–7200 seconds of work and preserves native state afterward; a low-disk signal requests an earlier dump. Every raw failure remains published.

A completed native DRT still requires original fixed-clock geometry, instance/topology, antenna, disconnected pin, fresh RC and original20/4/8/8ns three-corner setup/hold gates. It does not complete the analog serial PHY or chip signoff.
