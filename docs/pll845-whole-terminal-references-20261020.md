# Whole PLL845 terminal reference binding

The existing whole-parent geometry run 39322420374 preserves all metal/via
polygons, 235 physical wire components and all 26 native MIM masks.
This stage restores that exact source and attempts to bind all 2737 terminal
identities from its flat native LVS database.

There are 819 intrinsic body/well terminals. They remain explicit intrinsic
nodes with no claimed substrate-spreading model. The remaining 1918 terminals
must have a geometry-proven metal reference or an explicitly proved shared
intrinsic diffusion node. A shared diffusion classification requires multiple
native MOS source/drain terminals, one contiguous native region, no public
pin and no metal shapes/components on the native net. It never creates an
invented wire anchor or resistance edge.

HBT C/B/E use distinct native PCell pin planes with the pinned PDK pin
convention, including electrically tied collector/base terminals. All 52 MIM
plate planes retain their previous source-bound native witnesses. MOS gates
bind through actual continuous poly and contacts; other access points must be
actual contact/metal geometry with the correct native owner. Multiple metal
components are never silently shorted through an unmodeled access region.

Missing annotations, ambiguous contacts, unsupported geometry or incomplete
component coverage reject the stage and retain an unresolved-terminal report.
Seven actual reference corruptions must fail: missing/duplicated terminals,
off-metal coordinates, wrong ownership, treating body as metal, swapped MIM
plates and swapped HBT collector/base planes.

Even success here only provides whole-parent reference planes for fresh
MIM-aware RC extraction. Poly/diffusion access and substrate spreading remain
unqualified; this is not an electrical, acquisition, PLL, x4 or PHY pass.
All native work and reports are produced on GitHub-hosted runners.
