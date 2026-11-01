# PD650 HBT buffer and XOR load repair

This is an exploratory physical parameter candidate,not full PHY acceptance. Its native parent is the twelve-divider PD650 model SHA256 0a2ce363d3f8159a290f8642fe3a26c7ac1997ca4d8b934e4530fb4823974ef3 from41295928971. Original500-device source and the unchanged200MOS expansion are authenticated before deriving this candidate.

## Evidence and repair

Corrected full-row reader41298781054/sourceeb9b2602db8d971e405310142ab88d3fc652d308 reproduces all six original rejected measurements and29.329406mV phase. It passed33 reader controls. Complete evidence 502461e773ddb66c63bf64222c37beea6dcd3a4b at docs/evidence/pd650-wave-analysis-41298781054. Earlier reader41298254630 had a loop-variable phase-report error and remains rejected; the corrected read verifies the integral again at publication.

At0.9UI with source differential at least100mV,wrong-sign buffer samples remain A65/255,C39/214,D-X85/254,D-Y87/254. A divider is already correct in all255 such samples,while its output remains wrong in65. Physical device snapshots show steering currents and residual output voltage lag. The D divider itself also remains late. The hypothesis is that reducing input device area in the actual cascaded buffer/XOR path will reduce loading; this is not a measured capacitance reduction or a promised pass.

The exact40 HBTs are discovered and pinned from the actual native clusters:8 buffer input HBTs123,125,128,130,131,132,149,150 use Nx2->1;24 XOR data HBTs use Nx4->1;8 XOR selector HBTs137,139,142,143,155,157,160,161 use Nx6->2. The latter32 devices are IDs133..148 and151..166. No devices or wires are removed; all C/B/E/S nodes and all other model bytes are preserved and reverse-checked. Both500-device binder state and650-device actual model carry the same Nx changes.

[IHP documents Nx as the emitter multiplier](https://ihp-open-pdk-docs.readthedocs.io/en/latest/contents/device_libraries/hbts.html). This device parameter is a physical geometry change. The existing per-emitter current limit remains strict and uses the changed bound Nx,not stale original emitter counts. Source controls explicitly check all40 bound counts. Current,voltage,tail-current,data,phase and timing predicates are unchanged.

## Qualification and physical follow-up

All inherited original and75 divider-corruption controls run unchanged,plus243 HBT mutation refusals and all40 bound-emitter checks. They use synthetic fixtures and cannot prove electrical success. Native execution requires a separate successful same-source controls run and independently reserved/read-back empty exact-source release. All simulation,raw data and publication remain on GitHub.

The actual native screening must retain every failed gate. All124 HBTs,200MOS,98 resistors,7MIM and221 taps remain. The old distributed wire RC is retained only to isolate this screening change. Any useful candidate still requires regenerated geometry,complete DRC/LVS,new qualified RC,all required corners/phase offsets and full PLL/CDR/SERDES and chip timing integration.
