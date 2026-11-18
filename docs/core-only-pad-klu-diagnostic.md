# Alternate native linear solver diagnosis

Official ngspice47+ manual, sections11.1.1 and12.6, inspected2026-11-18:
https://ngspice.sourceforge.io/docs/ngspice-html-manual/manual.xhtml
The documented option klu selects the alternative matrix solver. Native pinned ngspice47 version output confirms it was compiled with KLU. Previous six-case run used Sparse1.3.

This revision adds only option klu to the explicit startup file before circuit loading. Keep pinned native binary and OSDI/device sources, supplies,125C, ideal1.5V clamp, Gear2/maxord2,5ps, itl4=100 and all error tolerances. No forced initial state or altered device parameter. Require post-transient Matrix solver KLU and native Using KLU Direct Linear Solver evidence; a silently ignored option fails. All six cases and complete50ns capture gates remain mandatory.

Two synthetic fault-injection cases verify first-case failure propagation and rejection of incorrect native solver readback. Native success, if obtained, still requires time-step convergence and physical/model qualification. This is not a pad slew waiver or production approval. Predecessor44371726618 completed five controls but failed0-turnoff; artifact14459915702 SHA2561ca5633e5a79e792d6efe6148b4b787b5ac279dc28e5d10b34f47ce9d3da3a86.
