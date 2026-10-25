# Placement-based candidate repair after routed-tree failure

Run 39663969344 reproduced the exact six source routed slacks, resized 20 cells
during electrical repair, and reached nine setup resizes before native RSZ-0074:
three reachable loads instead of eight. It did not close timing. The earlier
SIGSEGV and this distinct failure remain immutable Release evidence.

The next attempt retains exact ODB/netlist/SDC/SPEF and all baseline guards.
Only after baseline and unchanged-geometry router initialization does it call
estimate_parasitics -placement, selecting the native Steiner candidate model.
It records six estimated optimizer reports separately. Native clocks,
uncertainty, derates, all endpoints, geometry checks, fixed clock routing,
functional equation proof and rejection controls are unchanged. No final timing
acceptance can be obtained from these estimates. A successful candidate needs
fresh routing, extraction and all-corner setup/hold/electrical validation.

The native version is now included in result JSON and the public job log.
A Tcl setup error retains the partial ODB/netlist before rethrowing the error.

Upstream documentation:
https://openroad.readthedocs.io/en/latest/main/src/est/README.html

Nearby dated upstream revision 161f32b282692970c2fb0424fcd597fa3ef67707,
src/rsz/src/BufferedNet.cc, selects Steiner trees for placement estimates and
global-route trees for global/detailed-routing estimates. This explains the
proposed strategy; it is not asserted to be the exact binary revision.
Actual native execution and independent gates are still required.

All edits and durable evidence are on GitHub. No local CAD or archive is used.
