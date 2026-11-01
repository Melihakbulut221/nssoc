# Explicit intermediate Route828 checkpoint
The original source 2b8931b9c8988fc5dbf497a7b561db579e39f64c timed out after
14400.811 seconds in run 41270471645. Iteration26 finished with129 intermediate
router markers; iteration27 was interrupted. No post-route ODB was saved.

This supplemental adapter changes only the actual detailed_route iteration
bound from64 to8 for an explicitly intermediate first stage. It retains the
baseline environment checks, both original thread/resource limits, command
supervision, exact828-owner scope, all1351diodes, original clock/fixed
restoration, connectivity, antenna and final physical/timing acceptance gates.
The actual pre/post Tcl bytes and all four returned DEF/ODB outputs are pinned.
A return or checkpoint error remains a failure and any available partial output
is preserved. A checkpoint is not signoff, zero DRC or setup/hold closure.

All inherited sources, including the historical workflow, remain byte-identical.
The actual new shared workflow is separately bound by the supplemental manifest
and its own controls report. Twelve cloud-only source/lifecycle tests exercise
both the compiled inner adapter and the host namespace/projection; synthetic
control fixtures are never reported as native layout results. The inherited
source controls and all165 saved-diode controls remain mandatory.

A future continuation must authenticate a returned checkpoint and resume from
that checkpoint without repeating the first-stage stale-wire clear. This source
implements only stage1; it does not claim internal TritonRoute iteration-state
resumption. Final routing, extracted multi-corner setup/hold and full serial PHY
integration remain open. All native inputs/outputs stay on GitHub runners.
