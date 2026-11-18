# Parent context verified; preserve the inverter geometry

Run 44421507064, head e80657647436e54e038e68aca3d6e4427f31dbc6. Artifact 14481099771, SHA256 6b03750de90e95ec57c6665137e8b7bbb7b573e095609a73dc54e80354b0d3ac. All five output hashes and unchanged-source flag verified.

The inverter instance in GateDecode has transform r0 6000,0 at 0.001 um DBU. Left active fragment area is 1323000 DBU squared (1.323 um squared). The entire fragment is inside nwell but outside the isolated inverter's P implant. In the actual GateDecode parent, neighbor P implant covers all 1323000 DBU squared; uncovered area is zero. The recursive parent implant spans (-75,5760;7275,11090). This explains why isolated and contextual extraction differ; it does not establish full LVS. Do not modify this child geometry to fix its isolated-cell apparent input/VDD short.

The original full-pad deep database already has separate i and vdd nets and matches the inverter MOS devices. Direct inspection of its native database gives:

| Cell / parameter | Layout | Reference |
|---|---:|---:|
| inverter tap A (um squared) | 0.624 | 0.6241 |
| inverter tap P (um) | 4.76 | 3160000 |
| NAND2 tap A (um squared) | 0.657 | 0.6561 |
| NAND2 tap P (um) | 4.98 | 3.24 |

The reference inverter value originates from P=3.16 without a unit; correcting only the unit would still leave 3.16 versus 4.76. Layout substrate appears as a fifth inverter pin connected into the parent, while reference SUB! remains a local internal net. This needs an explicit, justified substrate/interface convention, not an assumed supply short.

Upstream issue https://github.com/IHP-GmbH/IHP-Open-PDK/issues/1295 remains open and already provides a public GateDecode reproducer with connectivity/pins matching but strict tap area/perimeter checks failing after documented preparation. It states commercial-tool verification exists, so these open-source-flow differences do not by themselves prove the physical library wrong. Issue https://github.com/IHP-GmbH/IHP-Open-PDK/issues/1281 also remains open and documents the tap-reader dialect and missing-unit defects. No new message was posted upstream.

Next: inspect the existing upstream GateDecode reproducer and relevant earlier project evidence before repeating substrate/dimension experiments. Do not waive taps or invent area/perimeter values. Core antenna repair run 44420129432 is separately active and still requires terminal report admission and fresh extracted timing.
