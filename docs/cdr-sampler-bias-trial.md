# Provisional C/D sampler bias experiment

This experiment tests a circuit change against the full original nominal_late loaded-wave measurements. It is not a physically verified layout, new PEX, closed-loop CDR, or full PCIe PHY.

Actual full500 native LVS correspondence run41450661063/source22baa225789b8ec1c9ce98437196af1e48fc2918 maps SD_UP/SD_UN to native182/183 and SC_UP/SC_UN to220/221. These four rppd pull-up resistors connect AVDD to C/D input-gain collector nodes. A/B samplers use a different input network and are not modified.

Hypothesis: reducing these four resistor lengths from1.8um to1.5um (width8um retained) raises data-pair input common-mode and may improve the clock-selector Vce headroom. It may also reduce differential gain; no improvement is assumed. The four clock-selected HBTs failed0.4V Vce in parent loaded41441047354 and timing/phase/current gates also failed.

The cloud worker authenticates the complete original freshRC41439516945 producer, runtime and numerical closure before deriving separate trial model/composition files. All500 device IDs and1446terminals retain their original connection. Only four l tokens/parameter values change; whole-model byte reversal and whole-contract reversal prove all other496 device parameters, wires and parasitic cards remain unchanged. The parent files remain untouched. Full native mapping artifact is authenticated and retained.

The inherited wire RC and primitive placement/geometry are NOT a matched extraction for the modified resistor dimensions. Output provenance explicitly records fixed-parent-interconnect approximation, matching_layout_verified=false and fresh_RC_for_modified_devices=false. A numerical pass cannot promote physical or fullPHY acceptance. Any successful electrical idea must regenerate schematic and GDS, pass DRC/LVS, regenerate canonical material and freshRC, and rerun the unchanged loaded tests before integration.

All original29 numerical definitions,5 executable blocks,9 source files,13 actual binding rejection controls,2 equivalent-unit controls,34.25ns transient,full wave vectors,stimuli,loads and measurement gates remain unchanged. Complete successful or failed native work is preserved in an independently reserved release. No native payload is downloaded or executed locally.

The workflow defaults to source controls only. Native execution requires explicit execute=true, same-source source-controls success and the independently reserved exact-source release. Original prior failed candidate remains rejected.
