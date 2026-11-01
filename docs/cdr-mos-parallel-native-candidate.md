# Parallel MOS domain correction — native candidate, not accepted PHY

Cloud-only continuation from checkpoint v226. The earlier W36->54um single-finger drive experiment remains superseded and was never dispatched.

## Exact physical/model finding

Audit41286195941/source0d7fe070aacb4f65809aa3edf832aa72435795b9 joined all50 MOS definitions to the complete canonical500-device physical locations. Device identities, four ordered native nets/clusters, W/L/AS/AD/PS/PD, rfmode and distinct PCell paths agree. Each of the50 extracted gate records has one polygon whose area equals its bounding rectangle. This uses authenticated existing extraction, not a newly generated layout or extraction.

All50 current ng=1 definitions are retained as evidence;42 exceed the used model's declared0.15–10um width range. Complete archived wrapper declarations now explicitly confirm w=w, nf=ng, mult=m, including the nonzero-junction-area branch. Therefore missing forwarding of ng is NOT the defect in the pinned wrapper. Increasing ng without real corresponding geometry remains invalid. [IHP issue164](https://github.com/IHP-GmbH/IHP-Open-PDK/issues/164) records the historical forwarding problem and its2025 correction; the exact archived model, not the historical implementation, controls this design.

Five selector controls and12 physical/plan corruptions passed. Native archive109 members were all verified; model files and archives were handled only on the GitHub runner. Full20-file proof731f70c41959f98e7066722b6376e830c7babcae is retained under docs/evidence/mos-model-domain-audit-41286195941.

## Native candidate actually generated

Run41286495589/source2f56f851e39db7be5bca9b14964219cded2cf89a completed native-card generation. The independently reserved release430435299/tagcloud-results-41286495589-1-mos-parallel-candidate contains all four outputs. No simulation engine was executed.

- model.spice:1988758bytes, SHA2567787330b1bd617a1da93ca6cce0c1b4b3d874a4299cde70733f32fd9fc0b4150.
- candidate-expansion.json:629340bytes, SHA2568660b23c3280ce2b1baee8e76f06bc7f95a64e9e9844777f058e08d0e8c716b2.
- source-composition.json:970050bytes, SHA25650061ebd710a318e9c6f3753d19cd51522c09e936868d3b50da187df475d66d1.
- native-generation.json:19269bytes, SHA256e1a37ffe21d5ce223f77da86edae1b7342abc89c0ea01333e4473039a8e37f46.

The actual mixed20 native model1967632bytes/SHA2564b5c155517c81990e528190b6ebd0405a876184da57224233fd1f05ae25d658b was expanded from50 MOS cards to200 explicit ng1/m1 cards,650 total devices. Each original total W and L and each exact D/G/S/B node is preserved. All450 other device cards and all existing RC/model bytes remain identical, proven by reversing every declared replacement. Original source composition remains unchanged; a separate650-device expansion descriptor records source-to-candidate identities.

The proposed independent units use a declared5nm width design grid and0.34um source/drain extension. Per-unit widths stay within0.15–10um. Independent junction areas and perimeters are explicitly generated; aggregate perimeter changes, so this is not electrically equivalent merely because total width is conserved. This grid/extension and placement/contact/routing implementation still need actual PDK geometry qualification. The model-domain checks alone do not prove that layout.

Eight renderer controls passed: one complete500-to650 positive binding and seven corruptions (duplicate/missing original device, wrong terminal/width, extra token, missing other device, colliding expanded identity). On the actual native model, all50 original parameter/card bindings and all650 resulting unique identities were checked.

## Next electrical and physical work

The existing frozen bind_native function intentionally expects500 total/50MOS and the original width census. It cannot be reused unchanged to pretend this650-device model has been simulated. Preserve its baseline validation and original13 binding controls, then add a separately qualified expansion binding that authenticates every origin/unit, all unchanged HBT/cap/resistor/tap records and every retained wire RC card.

The new measurement path must observe all200 MOS currents and preserve every original124HBT,7MIM, six sampler/XOR stages, phase/VI, startup/active stress, source/load and time predicates. Keep original aliases, data-pair collector selection,16 MOS tail-group topology and42 original tail origins while mapping every explicit unit into its original group. Do not merely relax500/50 constants or hide extra units from measurement. Derive the complete expanded vector set on cloud; an expected increase of150 current vectors is only a planning inference until proven. Qualify source controls, independently reserve an empty exact-source simulation release, then dispatch one actual native transient. None has yet been dispatched for this candidate.

Existing distributed RC is retained in this intrinsic candidate. Any electrical success still requires independent reference, actual geometry generation and routing, full DRC/LVS, fresh extraction and all-origin/unit RC rebinding, PVT/closed-loop checks, serial PHY integration and final chip timing. No PHY/physical/final timing acceptance is claimed.

## Subsequent continuation v229

Generation-only checkpointv227 was followed by qualified expansion binding and actual preparation attempt41287653458, which failed before simulator execution because baseline/candidate globals were mixed. The isolated correction is qualified by41288015065; new native attempt41288195752/source d638e0e3cd15a0ee930212c27ab1f238b5085237 is active. No electrical acceptance yet. See [expanded-MOS loaded simulation](cdr-mos-parallel-loaded-simulation.md).
