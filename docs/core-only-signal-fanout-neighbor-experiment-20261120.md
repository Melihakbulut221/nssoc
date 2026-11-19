# Signal fanout neighbor-route experiment — 2026-11-20

The rejected route has 158 unique net pairs / 680 geometric contacts. Every
pair contains exactly one of the original 618 selected nets and one previously
fixed neighbor. The complete authenticated count table identifies 127 distinct
neighbors. Route selection expands to 745 nets, from the original prepared ODB
2338707a927b80c95dbb087a332ea42f32e9c514c737bc25ae344d4e4da7a40c.
The rejected routed ODB is evidence only, not accepted physical input.

Two neighbors are explicitly CLOCK nets:
- clknet_7_115__leaf_u_ibex.clk
- clknet_leaf_41_u_ibex.clk

These two may change wire geometry; clock topology and all cell identities and
connections remain fixed. The remaining 2111 clock nets and 102783 nonpower
unselected DEF records must remain unchanged. Native checks enforce actual net
types, exact clocks permitted, NDR assignments and rules, terminal identity,
fixed wire encoding and restoration, geometry continuity and inter-net contacts.
No setup/hold result from the predecessor is reusable as candidate acceptance;
fresh propagated-clock STA is required after physical and antenna admission.
The two pre-existing clock fanout violations are a separate topology repair.

No antenna waiver is introduced. The route must pass zero antenna nets/pins;
if measured violations remain, repair those explicitly before extraction.
Keep 50 MHz / 20 ns, 5% derating and the approved scope excluding PCIe/Ethernet.
