# Data4 parent: original loaded full-wave gate

The native waveform workflow is bound to exact validation run39425717815 at271d7849a81ae07c89f18e96cf17e938deeab90e and fresh MIM capture summary928261bc7efd065100b19687d8ede3008dd1e086ae89ebee3296d89a981dd740. It requires both raw audit and composition to finish successfully and verifies their immutable summaries/parts and source chain before any electrical simulation.

The native controller is the v19 controller with only source/group/model identities changed. Its34.25ns /256-bit early and late cases, fixed clock phase offsets, original150fF sampler loads,50fF outputs, every HBT/MOS safety gate and1,108-column capture remain byte-identical. Clock-stopped and VI-bias-off rejection cases remain. There is no oracle, phase refit or load relaxation.

This tests whether physically reducing32 data/hold HBTs fromNx8 toNx4, with corresponding native layout and fresh RC, improves the previously rejected sampling. It does not establish closed-loop clock recovery, multi-PVT compliance, full serial x4 integration or final mainchip timing.
