# Provisional core physical boundary export

This experiment uses authenticated clock-refine run44259265143, not the still-running detailed-route producer. It invokes unmodified LibreLane3.0.5 OpenROAD.WriteViews to export abstract LEF, powered and ordinary netlists, DEF and ODB. No placement/routing or timing repair command is added.

A native OpenDB readback compares exported LEF macro dimensions, all terminal names, directions, signal types and exact pin rectangle sets to the input ODB. The signal set must match every bit of the current269-bit core contract; supply pins are listed separately. Input hashes must remain unchanged. The exported powered netlist is retained for subsequent supply-boundary integration review; its supply wiring is not approved merely because export succeeds.

A pass is provisional boundary compatibility evidence only. Re-export and rebind to completed detailed routing before integration or release. No final GDS, extracted timing, CDC, routed padframe, transistor LVS, ESD or manufacturing acceptance is claimed. The main detailed-route job is untouched.
