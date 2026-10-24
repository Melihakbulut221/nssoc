# Real TX clock phase and distribution development

The actual source-bound32:1 serializer needs31 differential selector clocks: one4GHz, two2GHz, four1GHz, eight500MHz and sixteen250MHz. Adjacent phases at each level differ by125ps. The existing tree_plan stores half-periods, not full periods. Source-bit launch and the original34ns/256-bit three-phase output gates remain unchanged.

The existing11 native reference leaves generate common-mode bias. They cannot replace the62 ideal differential modulation sources or their62 schematic25ohm access resistors. A single divider signal replicated across a level also cannot implement its different clock phases.

The first physical prerequisite exposes both actual master MP/MN and slave QP/QN from the frozen high-input native divider. The43 original primitives and12 finite substrate taps are unchanged. Only two real Metal5 master-net output accesses are added. The exact primitive graph is invertible to the original by a two-net port rename; independent native geometry checks require every previous material polygon and child cell to remain unchanged. Native560-category DRC, unsimplified deep/flat55-device LVS, all9 ports and five real/reference faults must pass.

This is a new phase-output cell candidate, not proof of quadrature under load. Next are full loaded native phase/order, headroom and precision tests, fresh extraction, selector common-mode/current drive and finite interconnect. Qualified divide-by-two slave behavior does not qualify the newly loaded master output. The required phase-tree topology and its deterministic startup/ordering must be verified before31-clock parent integration. An external PLL output may drive an isolated qualification bench; no internal ideal clock driver is allowed. Final acceptance requires the actual PLL, all31 routed/load-bound clocks, actualTX/CDR/x4 and chip integration.

All computation and evidence stay in GitHub. This branch does not change the production working branch or any running native process.


The fresh wire/anchor controller is prepared but has not run. It requires the exact corrected physical run40079962143 at60b6cc9b to succeed before restoring any native geometry. The native graph algorithm is a reversible derivation of the existing strict probe; it neither unions components by labels nor accepts unowned metal. The component count is measured from this GDS and then locked into the unchanged terminal-plane algorithm. The exact expected census is55 primitives,168 terminals,117 metal and51 body references,9 public ports; all seven original terminal corruption controls remain. This source is not RC or phase acceptance.

Deterministic startup remains a real missing stage: the native fixed MIM mismatch in the original divider is not a reset or a guarantee of polarity after warm reset or clock restart. No .ic, UIC, post-hoc phase fit, or software permutation may be used to claim the required125ps phase ownership. A physical reset/synchronization stage and loaded native startup/restart controls are required before a31-clock parent can be accepted.
