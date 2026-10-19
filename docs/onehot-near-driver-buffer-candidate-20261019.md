# Measured near-driver buffer candidate — 2026-10-19

The actual routed three-corner geometry diagnosis39241091888 identified39
weak data drivers with high capacitive loads on violating paths. This candidate
places one native positive sg13g2_buf_16 near each driver. It retains all148832
routed source cells, including the974 antenna diodes added during the last
route. The preceding147858 count described retained pre-route cells, not the
complete final database; the geometry-result document is corrected accordingly.

The edit splits only each selected output net into a short driver-to-buffer
net and the original buffered fanout net. No input equation, clock tree,
state element, macro, port or original placement is changed. Exact expected
net memberships are derived before mutation and compared afterward; PG/port/
NDR geometry is conserved. Only added buffers may be legalized. Original
driver-to-buffer pin Manhattan distance must be <=80um; site, row orientation
and native placement checks must pass. A placement failure rejects the
candidate rather than permitting a distant buffer to masquerade as local.

The cloud workflow exports the actual candidate netlist, runs the existing
native Liberty/macro equation checker and its controls, and requires an actual
new-buffer inversion to fail. All original clock periods, derating and corner
checks remain. This preparation proves only the stated native edit scope.
Fresh route, RC extraction, setup/hold, slew/capacitance, antenna, full-chip
LVS and complete PHY evidence remain necessary. No timing improvement is
claimed from estimated placement or physical proximity.

## Preparation result

[Run39242341481](https://github.com/Melihakbulut221/nssoc/actions/runs/39242341481)
passed on source6163ef917ff57f346f88b873dd5df0f019e7fe5b. All39 buffers were
legally placed; maximum actual driver-to-buffer Manhattan distance44.72um.
All148832 source cells, original placement and expected net topology were
preserved. Native positive-buffer count34348→34387; all retained equations/
state/macro inputs passed the existing scope-limited checker. Actual new-buffer
inversion failed as required. The proof excludes timing, SRAM interiors, CDC
and analog behavior.

The new route workflow restores this exact candidate and the complete prior
boot/RTL/placement/route ancestry. It retains the original nominal RC method,
three cell corners and all setup/hold/electrical/antenna checks. Only a fresh
result can establish whether the39 buffers improve timing. The candidate
contains148871 cells before any additional routing antenna repairs.
