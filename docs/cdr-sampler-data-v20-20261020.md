# CDR v20 data/hold capacitance candidate

The v19 full-wave diagnosis (run 39413957690) reproduced all 116 HBT safety
checks and all four sampler checks from both failed 256-bit native captures.
At +0.3 UI, A/B slave inputs have the expected sign and at least 100 mV,
but their loaded outputs are late. C/D master inputs remain below the internal
100 mV diagnostic marker in all 255 inspected observations. These are
observations, not a causal proof or revised acceptance criteria.

This candidate reduces the eight data and cross-coupled hold HBTs per sampler
from Nx8 to Nx4. The eight clock selectors remain Nx4. All MOS tails, load
and input resistors, substrate contacts, bias and external test loads remain
unchanged. Reducing transistor capacitance is a hypothesis; current density,
gain, headroom and loaded sampling must still pass their original limits.

Fresh native PCells are compared with the physically verified v19 leaf:
only those eight primitive parameter/drawing changes are authorized; the
other 46 drawings must be exact. The original 560-category DRC, unsimplified
deep/flat 54-device LVS, LEF checks and 17 corruption controls remain; an
additional wrong-data-Nx control is required. The generic source checker also
retains the exact protected v19 ancestry.

A leaf physical pass alone will not qualify the candidate. The complete
parent must integrate all four real leaf instances, run native DRC/deep-flat
LVS, receive fresh complete terminal/metal/MIM extraction, and pass the
unchanged early/late full loaded electrical tests. No v19 RC reuse is allowed
as v20 physical evidence. External-clock CDR testing still does not establish
closed-loop serial Gen3 x4 PHY or mainchip timing acceptance.

Everything executes on GitHub-hosted runners; reports and failures stay in
cloud releases. The local project remains empty.
