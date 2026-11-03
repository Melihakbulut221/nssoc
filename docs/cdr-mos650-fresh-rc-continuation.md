# Mandatory next step: actual650 native identity and fresh RC

Do not reuse the500-device canonical view or distributed RC to claim electrical qualification of the650-device physical layout.

Source pointers inspected: scripts/cloud_cdr_wire_shortcuts_canonical.py and scripts/cdr_via2_m3_canonical_core.py at130611547f554c126d67ff31a4dd9ee3e1812388. Existing code is intentionally for500 unchanged devices: CENSUS50MOS,1446terminals,953metal-terminal references/493intrinsic-body dispositions,978anchors; old/new identity compare assumes bijection and unchanged primitive drawing. Its parent-geometry/pin-recovery path cannot simply admit650 by changing counts.

Required actual native path:
1. Admit only the exact new physical650 candidate after its full560DRC/both650LVS/all13faults pass. Bind real GDS,independent schematic,LVSdb and full native archive.
2. Derive actual650 native identities and complete original schematic correspondences. Preserve450other devices, map each original50MOS to its exact group among200units using actual hierarchy/unit placements, original owners, widths and lengths. Parallel indistinguishable units require stable actual geometry correspondence, not arbitrary copied identifiers.
3. Recover/check terminal positions on actual new unit geometry. Old 'identical primitive drawing' recovery is inapplicable to replaced wide cells. Derive complete wire connectivity and every conductor partition from the new GDS; keep all25ports and full13conductor-layer coverage. Compare expected topology and allowed actual replacement material, not only bounding boxes or counts.
4. Mathematical expected terminal count2046=200*4+124*4+98*3+7*2+221*2. If same disposition definitions apply, expected metal references1403/intrinsic-body643 and logicalanchors1428 including25ports. These are expectations to VERIFY with native extraction, never observations to inject. Wire-net count must be derived.
5. Preserve meaningful refusals for missing/duplicated units, wrong W/L or totalwidth, swapped terminal ownership, wrong geometry/path, missing ports and partition drift. Original physical failures and current electrical rejection remain.
6. Re-extract the full distributed RC from actual650 geometry with fresh anchors/material. Do not reuse26344R/16878C from500layout; do not claim qualifiedPEX merely because numerical pipeline passes.
7. Bind original34.25ns full650 loaded test to the actual650 RC. Existing preparation expands50wide MOS to200units on500layout; it must not expand already200units again. Map actual new native IDs to original semantic devices and every saved vector, retaining original electrical thresholds, binding/parameter/range checks and failed baselines. All device/current/phase/sampling gates remain mandatory.

Remaining electrical baseline41549033741 is REJECTED:61/62Vce,phase/current and sampling failures remain even though115/116Vce improved. This migration is necessary to establish correct physical-electrical correspondence, not proof of Gen3x4 or final chip timing.
