# Resized route12: completed-route measurement handoff

The route12 candidate changes128 native buffer sizes with unchanged Boolean
connectivity and preserves153130 instances. It is not the prior unresized
route. Its new global ODB and guides are pinned by run39910632183.

The new mainchip-route12-postroute-cloud workflow requires an explicitly
completed, successful DRT descriptor and exact original input-package hashes.
It rejects live, saved-but-incomplete, failed, wrong-candidate and relaxed
clock/derate inputs. Both initial and continuation source branches have
synthetic controls. Push runs controls only; no unfinished route is consumed.

Native geometry compares the completed ODB with the actual new global ODB,
then checks all1691 source clock/fixed net records and attached cell geometry.
The128-resized netlist is restored from its proved release. No old SPEF,
routed metrics or stale unresized netlist becomes candidate evidence.

After geometry, the unchanged original flow checks antennas/disconnected
pins, extracts fresh nominal RC and runs slow/typical/fast timing at20/4/8/8ns
with5% derates. Setup, hold, slew, capacitance and fanout counts must all
meet the original gates. Failed measurements are retained as open findings.

This workflow measures the actual result; it does not repair antennas or
assert closure before evidence exists. Measured antenna failures require
a separate real repair/reroute and fresh checks. Nominal RC cannot establish
foundry min/max RC, full LVS/DRC, PVT qualification or full serial PHY.
