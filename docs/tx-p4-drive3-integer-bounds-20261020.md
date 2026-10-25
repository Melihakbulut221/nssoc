# Native DBU bounds for p4 replacement

Run 39446815154 failed during generation, at floating-coordinate X containment.
No native DRC or LVS was reached. Its report and archive are preserved. Because
the original assertion emitted no coordinates, a real footprint error versus a
floating representation error cannot be distinguished from that report.

The generator now compares the original and replaced instance's actual integer
database bounding boxes. It additionally checks that the original native box is
exactly the metadata box translated to the native origin. This retains strict
containment without a tolerance, shrinkage or relaxed DRC rule. A coordinate
witness is written before acceptance so any remaining failure is actionable.
All twelve port alignment checks and the original native physical gates remain.
