# Current650 full-circuit binding audit

Source inspection on2026-11-03. This is an integration audit, not an executed new loaded simulation.

## Preserve the original electrical experiment

The rejected full-loaded run41549033741 uses source6194e2fc2108f7b38c378d387761cf7e79771edf. Its scripts/cloud_cdr_wire_shortcuts_loaded.py first validates the old500-device,1446-terminal model and160 plane/51 logical-net binding. Only afterward does cdr_current_domain_loaded_adapter expand that baseline into650 model devices. Reusing this sequence for the current already650 native geometry would either reject the input or expand it incorrectly.

scripts/cloud_cdr_current_eight_drain_loaded.py bind_native validates explicit native terminal order and complete parameters before selecting data-pair collectors, separate hold-pair collectors, tail groups andVI devices. These electrical probe roles must survive migration. Preserve256 input bits,125ps UI,2ns start,34.25ns stop,0.3125ps maximum step,150fF loads and every original frozen phase/current/device/sampling acceptance limit. The previous rejected results remain failures.

The old bench explicitly uses an external8GHz clock; its own scope states it is not a recovered-clock loop. Passing that full loaded test is a prerequisite, not full serialPHY acceptance.

## Current physical sources and schemas

Current wire producer41712243960/sourcef3aece4ae3b048df220cb51277d74fcd026940ed has650 actual devices,2046 terminals,1428 distinct physical anchors,200 gate contacts and25 public ports. Complete derived artifact13268725447 was inspected in memory; no native geometry/model archive was downloaded locally.

- lvs_flat-identity.json pairs bind each current layout.id/model/parameters/terminal cluster to schematic identity and original_source.loaded_instance, origin_native_id and unit_index. All650 actual devices are already represented. reference_to_layout_terminal preserves terminal correspondence.
- terminal-anchors.json rows classify all2046 terminals:1203 actual metal point references,200 separate intrinsic gate electrodes requiring poly connection,643 intrinsic body/well references without substrate resistance. Its anchors include GC contacts and public P_name labels.
- unique-anchors.json retains actual coordinates, logical_labels and coincident witnesses. Equality of a schematic net name is not permission to short distinct physical anchors.
- device-locations.json independently records current primitive dimensions and hierarchy. Current layout MOS widths are8/8.885/8.89/9um with0.3um L, not the old32/36/53.335/64um source widths.
- The known model census is200sg13_lv_nmos,124npn13g2,98rppd,7cap_cmim,221ptap1.
- Physical gate contact reduction41725473326 is pending native qualification. Each projected intrinsic MOS must retain full physical dimensions with multiplicity1/N, not width scaling. Gate contacts bind through the authenticated current metal RC native ports.
- Current metalRC41713023974/source0e5b89ef37bd0664835ebe331af087946a9ab882 contains28619 resistors/18469 capacitors. Preserve all actual point attachments and13 native fault controls.

The intrinsic body/well abstraction and MIM overlap with metal capacitance remain unqualified. Do not silently ground every body node, add a duplicate intrinsic capacitance, or label a nominal composed model fullPEX. Full loaded admission must explicitly account for these open physical scopes.

## Required result after the reduction

Build a new composition and probe projection from current native identities and anchors, then run the unchanged full-loaded electrical experiment. Keep exact failed waveforms and reject on the original thresholds. Require nonlinear loaded convergence across projected-gate partition counts before relying on the reduction for jitter. Recovered-clock serial operation and actual four-lane integration remain separate required end-to-end evidence. Mainchip routing and all-corner STA remain required in parallel.
