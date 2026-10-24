# Direct sizing of measured mainchip data buffers

The completed native50-buffer route39149110568 remains the exact source.
Its original20/4/8/8ns clocks and5percent derate remain unchanged. Source-measured
slow setup paths still contain small buffers with cap>=0.1pF and delay>=1ns.
This trial sizes at most50 observed positive buf1/buf2 cells to buf8, or buf16
for cap>=0.25pF. The existing data-path selector and its controls are unchanged.
Clock buffers, non-buffer logic, flip-flops and SRAM are not targeted.

OpenDB dbInst::swapMaster is used and every terminal membership is checked
immediately afterward. See the [official API](https://openroad.readthedocs.io/en/latest/doxygen_output/html/classodb_1_1dbInst-members.html).
Only selected instances may change master/location during legalization; all
other146728-source instances, every net membership, NDR, supply geometry and
ports are independently compared. Actual Liberty equations and original native
logic controls are required, plus a real inverted-driver negative control.

The old signal routes are removed because pin geometry changed. This is a
preparation experiment, not routing or timing acceptance. Fresh global/detailed
routing, antenna/DRC/connectivity, nominal RC and original three-corner setup,
hold, slew and capacitance checks are required. Any hold regression remains a
failure. No clock budget, uncertainty, derate or acceptance limit is relaxed.
