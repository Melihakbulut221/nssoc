# Actual strapped sampler parent integration

Sampler physical run39151562771 passed the unchanged560category DRC, deep/flat54device LVS, native LEF and14fault controls. It also passed independent native primitive layer equivalence against local-order v9 with3fault controls. Receipt: `docs/evidence/cdr-sampler-strapped-physical-pass-20261018.json`.

The new484device parent replaces only four sampler masters. Their circuit and native primitives remain unchanged. The other seven leaf types and all41source cards/16macro connections retain their exact pinned proofs. Existing twelve-leaf overlay routing still adds50supply risers and19buses. Four new sampler leaves already contain their own upper-metal routing; the parent independently checks all76actual sampler M6 supply strips and8actual M7 supply buses instead of overlaying duplicate metal. Native parent DRC, unsimplified deep/flat LVS and physical fault controls remain mandatory.

This is a physical candidate. Fresh independent leaf/parent drawing binding, wire RC extraction, MIM capture, compact-model binding and full original loaded sampling/current/device gates are required. The old loaded failures remain recorded. No full PHY, recovered clock, PCIe protocol, mainchip route or final timing acceptance is implied by sampler physical success.
