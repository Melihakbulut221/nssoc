# Actual HV finger routing prerequisite

The original TX input driver requires four `sg13_hv_nmos w=10u l=.45u ng=10` devices. The measured native PCell has ten 1um gate fingers and eleven alternating source/drain columns. This experiment routes all ten gates, six source columns and five drain columns with actual native contacts and vias, and adds one explicit finite substrate contact. Original active and gate geometry stays unchanged.

Two independent transistor references are required. Raw extraction must match ten 1um devices plus the substrate-contact device with simplification and combination disabled. Native combination must also match the original 10um/ng10 reference plus contact, in both deep and flat modes. The expanded ten-device reference is only a geometry check; it never substitutes for the original simulation model or its junction parameters. Native device counts must be 11 before combination and 2 after combination. No implicit net connections, blackboxes, tap suppression or waived devices are added.

Actual missing-last-gate-contact, open-drain-route, drain/source-short, wrong-reference-width and off-grid geometry controls must be rejected. All 560 native main DRC categories are required. Completed failed comparisons remain available even if another gate fails. The deck and native tool revisions are the existing locked revisions.

This is a physical building block for the complete input driver. It does not close buf16 integration, four resistor routes, body spreading, RC extraction, electrical timing, full serializer routing, CDR, four lanes or mainchip acceptance. All work and artifacts remain on GitHub; local checkout stays empty.


## First native failure and geometry repair

Run 38864608050 retained all failed raw/aggregate comparisons and physical controls. Both device counts were correct, but the extracted body had become the source net; three Cnt.g1 markers occurred at the first source contacts. Cloud evidence readers 38865073101 and 38865577476 inspected the original archive rather than rerunning CAD. The latter exposed actual instance transforms: `nmosHV` was mirrored at the origin and `ptap1` was also at the origin, causing the implant overlap. The PCell source and original transistor geometry were not the cause.

The producer had called `pya.DTrans(30,30)` and `pya.DTrans(45,20)` with integers, selecting the rotation/mirror overload. It now explicitly converts both coordinates to floats and verifies the transformed unit rectangle for every placement before inserting the instance. Actual transforms are recorded. The LVS reference, finger widths/counts, finite tap reference, native decks and faults remain unchanged. The DRC reader also now receives its required `run.log` name; original DRC markers were retained even when the first report parser classified the missing-log problem as ERROR.

A new full native run is required before accepting this repair. Source/reference/implant edits that merely make the failed topology match are not used.
