# Routed128buffer candidate: clock/data regression investigation

The completed native route39331918238 has0routing DRC errors,0critical disconnected pins and16antenna nets. Setup counts are9660/7027/3107 and hold counts3/17/95 at slow/typical/fast cell corners with fresh nominal RC. All original20/4/8/8ns clocks and5percent derate remain. The candidate is not accepted.

Read-only review39362291106 found a shared PCIe capture-clock branch in representative newly failing fast hold paths: clkbuf_3_5_0_pcie_clk_i/X to clkbuf_6_46_0_pcie_clk_i/A contributes0.684392ns net delay and1.292744ns receiving slew. The same branch appears in the advertiser refresh paths. This is evidence to investigate, not proof that changing the clock branch will safely repair timing.

The new hosted comparison reads all available old/new min path reports and separates data arrival and required-time changes at identical endpoints. It ranks capture branches by measured delay change and affected negative endpoints, and retains reported setup slack on those same endpoints in all3corners. No report sample is represented as an exhaustive endpoint census.

Before inserting hold delay into many data paths, inspect actual clock route geometry and extracted parasitics for common changed branches. Any proposed clock repair must preserve constraints and be remeasured for setup and hold after native route/RC; improving hold by making capture earlier can hurt setup.

OpenROAD's documented incremental global routing can update dirty nets after edits, but availability and exact behavior must be checked against the pinned runtime before implementation: [global routing documentation](https://github.com/The-OpenROAD-Project/OpenROAD/blob/master/src/grt/README.md). The running design is not changed by consulting this documentation.

Full PCIe serial PHY, loaded PLL/CDR/TX qualification, comprehensive LVS/DRC/antenna and final timing remain separate open requirements.

## Native clock versus data attribution

Cloud run [39364077862](https://github.com/Melihakbulut221/nssoc/actions/runs/39364077862)
completed the same-endpoint native report comparison after rejecting and correcting
unrecognized actual SRAM clock ports and CTS delay-buffer stages. Native slack
equations and source hashes remain checked. Full frozen report and provenance:
docs/evidence/onehot-clock-regression-pass-20261020.json.

At the fast corner, 75 of 95 negative reported minimum paths share the output of
clkbuf_3_5_0_pcie_clk_i. Compared with the actual previous 33-buffer route, its
connections to clock branches 6_44, 6_45, 6_46 and 6_47 gained respectively
0.513008, 0.515861, 0.525570 and 0.527561 ns of measured net delay.
These paths include asynchronous removal checks; they are not all register
data hold paths. The report sample contains 31 previously nonnegative endpoints
that became negative; unmatched or unsampled endpoints cannot be counted as
newly failing.

This is evidence of clock-route regression, not proof that advancing capture
clocks alone is safe: several of the same endpoints already fail setup in the
current design. Next compare actual ODB geometry and exported nominal wire RC,
then validate a physical repair with fresh routing, extraction and all corners.
No clock period, external delay, derating, exception or acceptance threshold
has been changed. The 128-buffer layout remains rejected for final timing.

## Actual paired geometry and nominal wire RC

[Cloud run 39365314065](https://github.com/Melihakbulut221/nssoc/actions/runs/39365314065)
passed the read-only paired native geometry and SPEF checks. Source ODBs and SPEFs
are immutable and all selected native pin identities/directions, graph
connectivity and serialized capacitance sums are checked. Literal SPEF-escaped
flip-flop names are decoded without omitting terminals.

The offending clknet_3_5_0_pcie_clk_i retained its original pin locations and NDR,
but total native wire length grew from 1142.070 to 2996.810 um.
Its exported nominal wire capacitance grew from 0.222630 to 0.612160 pF.
The lowest series-resistance path to branch 6_46 rose from 1067.1716 to
2404.3016 ohm. This path resistance is an upper bound on effective resistance,
not an STA delay or qualified RC extraction.

A physical candidate now restores the actual original shorter clock route
within the latest routed chip. It must retain exact via definitions, every
unrelated DEF byte and native exported logic. Fixing this physical wire for
legalization does not change any timing constraint. DRC, connectivity, fresh RC
and all-corner STA remain mandatory after import; this preparation cannot
establish timing closure.

The first transfer attempt 39365732494 was rejected because its DEF reader
assumed unindented net declarations. The native exporter uses leading spaces
([OpenDB DEF writer](https://github.com/The-OpenROAD-Project/OpenROAD/blob/master/src/odb/src/defout/defout_impl.cpp)).
Recognizing that whitespace leaves the raw non-target DEF hash comparison intact.

The transfer runs 39366144342 and 39366605396 exposed a real import-mode error:
OpenDB incremental DEF reading does not register NETS callbacks. It therefore
cannot import the proposed wire. The existing-net FLOORPLAN mode does register
them ([native reader source](https://github.com/The-OpenROAD-Project/OpenROAD/blob/master/src/odb/src/defin/definReader.cpp)).
The patch contains only this one NETS record; all other DEF content must still
match byte-for-byte and both native wire metadata and wire decoder must say
FIXED. The first native run of the corrected import must prove this behavior;
the documentation alone is not validation.

## Actual physical transfer passed; legalization and fresh STA started

[Native transfer 39367665103](https://github.com/Melihakbulut221/nssoc/actions/runs/39367665103)
passed with both real fault controls. The latest routed chip now has a candidate
containing the original 1142.070 um clock route. All unrelated DEF content is
byte-identical and native baseline/candidate Verilog exports are identical.
Actual via definitions, native pin positions, NDR identity and every fixed-route
token match. Only the order of the unordered DEF connection list is normalized;
physical route tokens are not normalized or approximated.

[Physical legalization and timing run 39368178274](https://github.com/Melihakbulut221/nssoc/actions/runs/39368178274)
uses source 38c785bfbba6bbd55a70f311a66aee99c36f9c89.
It revalidates the original boot/RTL/logic/placement/route ancestry before native
DRT, then checks antenna/disconnected pins and performs fresh nominal RC and
the original slow/typical/fast cell-corner STA. It uses existing real global
guides and independently verifies that native DRT retains the exact fixed clock
route. Source-delta checks restrict changes to the prior proven controller.

The imported candidate is not DRC-clean or timing-closed merely because transfer
passed. No physical or timing acceptance is asserted until those results exist.
