# Official I/O GDS revision comparison — 2026-11-19

Run https://github.com/Melihakbulut221/nssoc/actions/runs/44417478537, attempt 1, head `9410ea30e75bbcdadeb60c906c96ab17e8e42077`. Artifact `14480840098`, SHA256 `7a83b75a1cbc76c96c3b62ec4d9eb0b248195a276f00d982c14a2d3b00d0fca7`, authenticated after completion. KLayout 0.30.9 compared recursive merged polygon regions and transformed text strings on 43 layers, with 0.001 um database units.

Old GDS: IHP `c4b8b4e5e7a05f375cca3815d51b3a37721fbf5c`, SHA256 `aafb713ba3cd547ca48e919ec68eb6a8ed0f09051fed0fad813d3fdb043a4fa5`.
New GDS: IHP `cc9afba57e0ec1b5ba77e6bbb638ba9dbe5866b8`, SHA256 `25ecbd87d8286d273fbdd3d24cf819d480fb479d6636bcd8cea721de75a57815`.
Both input sizes and Git blob identities matched the independently inspected GitHub metadata and remained unchanged during comparison.

19 cells compared; 14 have geometry or text differences. The other five are DCNDiode, DCPDiode, IOPadOut4mA, IOPadOut16mA and IOPadVss. The InOut4mA/16mA/30mA pads differ; the internal LevelDown bounding box also expands. Unchanged macro footprints do not establish equivalent interiors.

| Cell | Changed polygon layers | Changed text layers |
| --- | --- | --- |
| sg13g2_DCNDiode | none | none |
| sg13g2_DCPDiode | none | none |
| sg13g2_GateDecode | [1, 0], [6, 0], [8, 0], [8, 2] | none |
| sg13g2_IOPadAnalog | [10, 0], [128, 0] | [8, 25], [10, 25] |
| sg13g2_IOPadIOVdd | [1, 0], [6, 0], [14, 0], [128, 0], [133, 0] | none |
| sg13g2_IOPadIOVss | [134, 0] | none |
| sg13g2_IOPadIn | [1, 0], [5, 0], [5, 2], [6, 0], [8, 0], [8, 2], [10, 0], [14, 0], [19, 0], [31, 0], [40, 0], [44, 0], [51, 0], [128, 0] | [8, 25], [10, 25], [51, 0], [63, 0] |
| sg13g2_IOPadInOut16mA | [1, 0], [5, 0], [5, 2], [6, 0], [8, 0], [8, 2], [10, 0], [14, 0], [19, 0], [31, 0], [40, 0], [44, 0], [51, 0], [128, 0] | [8, 25], [10, 25], [51, 0], [63, 0] |
| sg13g2_IOPadInOut30mA | [1, 0], [5, 0], [5, 2], [6, 0], [8, 0], [8, 2], [10, 0], [14, 0], [19, 0], [31, 0], [40, 0], [44, 0], [51, 0], [128, 0] | [8, 25], [10, 25], [51, 0], [63, 0] |
| sg13g2_IOPadInOut4mA | [1, 0], [5, 0], [5, 2], [6, 0], [8, 0], [8, 2], [10, 0], [14, 0], [19, 0], [31, 0], [40, 0], [44, 0], [51, 0], [128, 0] | [8, 25], [10, 25], [51, 0], [63, 0] |
| sg13g2_IOPadOut16mA | none | none |
| sg13g2_IOPadOut30mA | [8, 2] | none |
| sg13g2_IOPadOut4mA | none | none |
| sg13g2_IOPadTriOut16mA | [1, 0], [6, 0], [8, 0], [8, 2] | none |
| sg13g2_IOPadTriOut30mA | [1, 0], [6, 0], [8, 0], [8, 2] | none |
| sg13g2_IOPadTriOut4mA | [1, 0], [6, 0], [8, 0], [8, 2] | none |
| sg13g2_IOPadVdd | [1, 0], [6, 0], [128, 0], [133, 0] | none |
| sg13g2_IOPadVss | none | none |
| sg13g2_LevelDown | [1, 0], [5, 0], [5, 2], [6, 0], [8, 0], [8, 2], [10, 0], [14, 0], [19, 0], [31, 0], [40, 0], [44, 0], [51, 0], [128, 0] | [8, 25], [10, 25], [51, 0], [63, 0] |

This is a geometry/text difference measurement, not LVS, extraction or signoff. It compares merged polygon material (independent of fracturing) and labels, not every GDS record/property/hierarchy. Do not place the new Liberty onto old GDS by assumption. Next: qualify the new matched GDS/CDL/SPICE views with native transistor LVS and DRC, migrate the pad macros coherently, then regenerate parent/whole-chip timing evidence. Preserve the core detailed-route run separately; it remains in progress at this report.
