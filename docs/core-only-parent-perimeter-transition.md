# Parent perimeter repair transition

The four measured nets net73, net78, net83 and net89 have route lengths
5505.73, 5437.86, 5367.30 and 5328.00 micrometers respectively. Their original
buf4 endpoints sit below and above the core macro, while their wires detour
around the macro. Geometry inventory run 44347705567 / artifact 14448055053
was independently verified (12 outputs and protected repository sources).

Candidate run 44348516094 / head 03ac8f1ee433ba8099120ea5231ff85cf176acd2
passed native legalization and connectivity checks. Its artifact 14446553331
SHA256 is 82efb071200ea2dc8aa6a93672229c141b09e0d3c50b155d26ddb32ea5e273d7.
All outputs and protected repository sources were independently verified.
It inserts 56 buf4 cells along the left core perimeter. The 1975 original
instances, boundary pins and power geometry are preserved; contracting the
new buffers preserves original connectivity classes. New cells have explicit
power connections, stay outside the core, and remain within 100 um of their
planned locations.

The new routing stage authenticates this exact candidate, routes 2005 parent
nets, and checks native route DRC, visible geometry, coincident pad contacts
and exact cell/connection/net-type/power identity. Fresh RC extraction and
three-corner timing remain necessary to determine whether the four electrical
violations are fixed. This is not production acceptance or complete chip
timing. Core-output model, external I/O, CDC, RC min/max, foundry DRC/LVS and
manufacturer approval remain separate requirements. Clocks remain 20 ns with
5 percent derating; no timing exceptions are added.

## Staged extraction

The perimeter timing workflow is staged but must not be dispatched until route
44349370248 at c7b88e12d18ad6854cfbf7bb4e419adec13842ee is independently admitted.
Supply its verified artifact ID and SHA256 as workflow inputs. The runner checks
2031 instances, 56 inserted buffers, 2005 extracted nets, full endpoint coverage,
and strict source identity. It performs fresh nominal extraction and native STA
with slow, typical and fast libraries and the unchanged parent SDC.
Electrical reports distinguish all violations from those at the new perimeter
buffers and the eight original endpoint buffers. A successful job records
measurements; it does not assert final chip timing or production acceptance.
