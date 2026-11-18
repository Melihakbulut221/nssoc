# Core-only continuation: rejected route and matched-pad LVS

## User constraint
Package, PCB, attached devices and external interface speeds have not been selected (user confirmation). External I/O production timing cannot be approved until these are specified. Continue internal physical work; do not invent external delays. PCIe and Ethernet remain excluded. Core target remains 50 MHz / 20 ns with 5 percent derating.

## Latest detailed route: rejected for antenna, not routing DRC
Run https://github.com/Melihakbulut221/nssoc/actions/runs/44402072903
Head 75131e1401c85e6cdc12d05819f401856162a93c, attempt 1, completed failure.
Artifact 14481780456, SHA256 3abb2224c073efa979a43238b0d3aa8782549a174d4ef6c7606ced1d086460ce. Archive digest and all 13 manifest output hashes reverified.
Native OpenROAD returned 0 and completed detailed routing. Router DRC: 0. Antenna: 234 nets / 265 pins. The strict zero-antenna assertion correctly rejected this candidate.
Routed ODB SHA256: 8f32184f94bd944c39e6a90417462535091164272a145110b7a716523d6a6ee1.
106083 instances; exact instances, terminal connectivity, special wires, ports and die preserved. Visible-geometry audit found no disconnected signal nets, missing terminal geometry or inter-net contacts. These are limited checks, not transistor LVS or foundry DRC.
Pre-route estimated setup/hold counts were zero in three corners; this does NOT prove routed timing. No fresh extraction/STA has been accepted for this candidate.
Next: inspect antenna.rpt and implement an additive or routing-based repair against this exact ODB; verify placement, connectivity, power contacts, DRC and antenna again, then fresh RC/STA. Do not restart the same full route unchanged or promote the earlier zero-antenna ODB as timing closure.

## Latest matched official pad LVS: real mismatch
Run https://github.com/Melihakbulut221/nssoc/actions/runs/44418807867
Head 2eabb75314cb5afa29937b975d9e587733f4b6b6, attempt 1, completed failure.
Artifact 14481211769, SHA256 a21985a8a9ec8a82e991e43534576a2ffd6985c540d5588d6e35a534a5379bd1. Archive digest and all 56 manifest output hashes reverified.
Official snapshot cc9afba57e0ec1b5ba77e6bbb638ba9dbe5866b8; sg13g2_IOPadInOut4mA fails both deep and flat native comparison. Native tool return code 0 is not an LVS pass: the deck explicitly reports netlists do not match and the audit rejects it. Flat recursive device counts: layout 46, schematic 59; this difference alone is not a root-cause diagnosis.
Next: inspect device/net cross-reference reports and tap/global substrate handling with strict controls. Keep tap extraction and strict ports enabled. Do not rewrite reference dimensions/connectivity to fit extracted geometry. Latest library's relaxed transition limit cannot be adopted independently of its matching physical views and validation.

## Still open
Antenna repair, final extracted setup/hold and electrical checks, full core/pad integration, full SRAM LVS and characterization, qualified RC corners, foundry DRC/LVS, package/board I/O timing, DFT/ESD/PDN and manufacturing approval remain open. No production-ready claim is made.
