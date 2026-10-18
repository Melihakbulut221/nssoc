# Sampler upper-metal strap candidate, 2026-10-18

The original local-v5 full loaded early/late tests remain rejected. Native waveform review39149970188 separated the voltage loss across each of16sampler intrinsic load resistors from supply wiring and load-to-collector wiring for32actual collector terminals. For early bqp/xd0047, mean losses are0.174580V supply wire,0.063322V intrinsic load,0.111515V collector wire. These are measured waveform means, not an effective resistance or a timing acceptance.

The v10 candidate retains all54native primitives and the same circuit. It adds actual TopMetal1 vertical straps and TopMetal2 horizontal straps to every net, with native via stacks. Wider escape-column pitch gives the upper-metal pads physical space. Every public port keeps an8um Metal5 lead so the original clock-open fault still cuts the complete path. The placement optimizer uses the new physical pitch; no compact-model parameter or extracted RC is scaled.

Hosted physical validation must pass the original560category main DRC, unsimplified deep/flat54device LVS,14negative controls, native LEF checks, and independent layer-by-layer primitive-geometry equivalence with3negative controls. A generated layout or a physical pass is not a loaded electrical pass. Parent integration, freshly extracted RC/MIM binding, full original256bit loaded waveform gates and PVT/full-loop verification are still required before electrical acceptance. FullPHY and mainchip timing remain open.

Four resistor-only screens39149512255 failed original electrical gates. Their initial Release publication also failed because dotted job-group names were invalid; cloud recovery preserves the original artifacts and hashes without rerunning simulation. This failure is not relabelled as success.
