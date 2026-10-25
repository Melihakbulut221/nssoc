# Route and independently remeasure the actual native-resizer ECO

The successful candidate is run 39390580378 at c793becc651afe70e201ab2c83da19228da87d69.
Its immutable summary SHA256 is
71d8606613f7196bdda5eeb4fa9b0a8d78ca4d338e1816ea1543927cc5079106.
The actual result contains 151051 instances, including 29 new positive delay cells.
Do not confuse this result with the earlier rejected run that reported four buffers.
All original instances remain, and the original source has 151022 instances.

Before routing, the controller repeats the complete existing boot/RTL/CTS/route
provenance and restores this candidate by exact report, archive and ODB/netlist
hashes. It checks six source baseline slacks, geometry/supply/fixed-clock proof,
actual Boolean equation proof and inversion negative control. It restores the
exact saved SDC; stale DEF, power netlist, SDF, SPEF and inherited metrics are
cleared before invoking the native flow.

The proven fixed-clock DRT/antenna handling, connectivity checks, nominal native
OpenRCX integrity audit and propagated-clock three-corner STA scripts are unchanged
and source-hash-bound. Original 20/4/8/8 ns budgets, 5 percent derate and twenty
SRAM instances remain. The routed topology checker now binds the actual candidate
ODB and 151051-instance census instead of the obsolete 150419 value. It otherwise
retains the same checks for all original masters, placements, pins, nets, NDRs,
ports and diode-only additions, with four fault controls. Fixed physical clock
geometry is independently checked again after detailed routing.

Optimization estimates do not count as route/timing success. Actual final antenna,
DRC, disconnected-pin, setup, hold, slew, capacitance and fanout results are
reported after native extraction. Passing this workflow proves only its measured
scope; nominal RC plus three cell corners is not qualified manufacturing PEX,
full-chip transistor LVS, full serial PHY or production signoff.
