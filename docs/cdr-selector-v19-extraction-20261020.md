# Fresh complete extraction for the selector-Nx4 physical parent

Parent run 39394475994 passed both strict deep and flat unsimplified LVS:
116 HBT, 46 LV MOS, 102 poly resistors, 11 MIM capacitors and 209 substrate
contacts, totaling 484 native devices. The 560-category DRC had zero markers.
Nine original reference/physical fault cases rejected as expected.
All sixteen placements and eight actual leaf drawing sets were independently
checked. The new serialized GDS SHA256 is
247fd159b5a245c9dd8df13082cab62d4f185ea39102a62b9c4491ce230d999b.

The extraction pipeline is bound to this immutable physical report and GDS,
not the rejected prior flat LVS run. It reuses the unchanged native interface,
terminal, geometry, model-parameter and strict wire-RC methods from v18.
Only the source identity, output namespace and parent-replacement provenance
change. Source-delta checking binds these changes.

Native 158 interface planes across 51 logical nets, all 1394 transistor/device
terminals, model binding, recovered terminal annotations on identical native
drawings, complete metal/via connectivity and full fresh wire RC are checked.
Original 19 interface, 12 model-binding and 13 wire-RC corruption controls
remain. Each downstream cloud job consumes exact same-run summary/archive
digests. The native extraction must determine its actual numerical R/C values;
no old v18 RC values are used as v19 geometry evidence.

This pipeline precedes fresh MIM/contact composition and the original complete
loaded electrical early/late/fault tests. A green geometry/extraction workflow
does not establish full CDR, x4 serial PHY or mainchip timing acceptance.
