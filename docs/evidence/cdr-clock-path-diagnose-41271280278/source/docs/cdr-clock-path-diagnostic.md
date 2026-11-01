# Existing-wave clock path decomposition

Diagnose the original rejected loaded run41260582673 without running another simulator or altering geometry. Cloud-only acquisition authenticates the entire original113-member native archive, materializes only the exact original waveform, and uses the unchanged original reader for all1151 vectors. Original124 HBT metrics, all six stage metrics/all1530 bit delays and original phase/VI are reproduced before diagnosis.

The new analysis pairs cp/cn terminal probes only on a shared physical emitter net. All32 clock steering devices/eight physical tails and all four physical pair combinations per tail are retained. For both clock edge directions and each of255 bits, preserve every local differential zero crossing within the nominal edge plus/minus0.45UI. Multiple or absent crossings stay explicit; never choose the most favorable crossing. The external clock must have one crossing in each window.

For each sampler, identify output-stage and preceding-stage clock tails through the native transistor connectivity. Keep all255 original per-bit settling values and signed margins at the unchanged0.3UI deadline. Settling minus local crossing is contextual measured correlation, not an isolated cell delay or proof of causality. No clock/deadline/phase/polarity is shifted to claim a pass.

Controls include the original seven extraction/reader/electrical reproduction tests plus six new tests for crossing interpolation, opposite directions, ambiguity preservation, no crossing, bounded windows, malformed axes and physical emitter-based pairing/refusal. All run on GitHub; no local native data.

The four-shunt candidate remains rejected. For future sizing, IHP's npn13G2 PCell constrains Nx to1..10; do not turn a larger unsupported single-cell multiplier into a physical-layout claim. Source: https://raw.githubusercontent.com/IHP-GmbH/IHP-Open-PDK/main/ihp-sg13g2/libs.tech/klayout/python/sg13g2_pycell_lib/ihp/npn13G2_code.py (defineParamSpecs). This inspection does not update the frozen project's PDK or acceptance thresholds.

Artifacts: cloud-clock-path-controls (source tests), cloud-clock-path-diagnostic (derived reproduction, topology/delay result and complete acquisition hashes). Native acquisition stays on the runner and is retained only in the explicitly named native-failure artifact if diagnosis fails. Full PHY, physical acceptance and final timing remain false.
