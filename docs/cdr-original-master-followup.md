# Original-master controlled native experiments

The24-resistor master/buffer candidate passed its original nominal device predicates but failed all data stages. Relative to the earlier12-resistor candidate it changed both buffer impedance and master loads, so the observed regression cannot be assigned to one change alone.

Both follow-up variants start from the authenticated original500-device model. They retain original master loads XD177/178/195/196/207/208/215/216 atL2.6um/W32. Four buffer pullups XD182/183/220/221 useL1.0um/W8 instead of1.8um; four shunts XD184/185/222/223 useL3.4um/W4 instead of5um. Eight output/slave loads XD175/176/191/194/202/205/212/214 differ:

| Variant | Output load L um (W32 retained) | Source | Controls | Actual native |
| --- | ---: | --- | --- | --- |
| q15 | 1.5 | e85179e6900c2be9d931a8b30549c99f47c7617d | 41276766920 | 41277054717 |
| q20 | 2.0 | edc7c8d04659f73d024c45bbfa4936b977c90c32 | 41276785721 | 41277056212 |

Each changes exactly16 length tokens, with the entire remaining model, wireRC,1151vectors,10ohm sources,150fF sampler/50fF XOR loads and original frozen prepare/measure bodies unchanged. Both source controls passed17circuit and5archive refusals. The same original13native binding controls remain required. q15 versus24candidate isolates master restoration; q20 versusq15 isolates output-load length. These are hypotheses, not results.

Exact-source empty output releases430382305 and430382311 were independently created/read back before host admission. Their tags are cloud-results-41277054717-1-cdr-sampler-load and cloud-results-41277056212-1-cdr-sampler-load. Preserve all terminal results, including electrical failures, without changing gates.

Each candidate has a16-target result comparator with13corruption refusals. The candidate report descriptor remains null until the full authenticated actual terminal report is available. Sources: codex/cdr-original-master-q15-comparison atf2b4d0c474a36466a6d3115dfbeb5028fed3a7f9 and codex/cdr-original-master-q20-comparison atb744e0b827bdcd7ab2e731928a990bb1ab8a93a8. No simulator rerun or native payload is needed for derived report comparison.

## Physical follow-up requirements

The previous24-target map includes masters now deliberately unchanged. Therefore shared output/master resistor cells require private targeted instances. Do not mutate shared definitions blindly.

Existing physical source inspection identified reusable real-PCell regeneration, original material matching, PLUS/MINUS pin matching, owned M1 endpoint bridges, foreign-metal clearance and serialized original-cell/hierarchy preservation. However, the old generate_cdr500_resistor_v59.py targets legacyv58 and a7.4-to5um shunt change; it cannot run unchanged on current canonicalv59. Preserve current via2/M3 repairs. Derive current native net ownership from the current canonical LVSDB and independently patch genuine authored parent/leaf schematic references. Never derive an LVS reference by copying extracted netlist. Re-establish all500semantic device bindings after extraction because native IDs may reorder.

No geometry has changed for either candidate. Even an electrical screen pass still requires actual layout, nativeDRC/LVS, freshRC, corners, closed-loop/fullserialPHY and mainchip timing verification.

All simulation, controls, comparisons, geometry and numerical analysis run onGitHub. Native archives/models/SPICE/GDS/ODB/rawwave data stay cloud-only. Local source/API-derived text coordination is temporary RAM only; project workspace and temporary file areas remain empty.
