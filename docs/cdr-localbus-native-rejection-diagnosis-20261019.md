# Local-bus CDR rejection: native sampling and headroom diagnosis

The existing full256bit early/late captures39252773409 remain rejected.
Early sampler wrong/low-margin counts: a77/129,b129/129,c196/240,d323/339.
Late: a91/129,b0/128,c194/236,d310/329. The original100mV and37.5ps
clock-to-valid gates remain unchanged. No sampling window shift is allowed.

Exactly two HBTs violate minimumVCE0.4V: native129 and147. Early minima
are0.394714V and0.398763V; late0.395763V and0.399028V. Native plane
identity maps their base nets to adp and cdp in the two XOR comparators,
not the four sampler macros. Source binding preserves their Nx4 parameters.
This association alone is not a causal diagnosis or a successful fix.

A read-only cloud review now restores both original raw captures, actual
composition and native planes by pinned hashes. It reproduces every original
sampler sample and all116HBT voltage/current limits, then reports:
fixed-phase master/slave input and output measurements; actual clock-base
crossings; supply-terminal drops; native collector-to-base wire drops;
separate intrinsic-load and metal drops at32 sampler collectors; and the
two failed XOR HBTs at their actual worstVCE instants.
Shortest resistor paths are explicitly upper bounds, not effectiveR or delay.
No simulation, device, wire, threshold or failed result changes.

Use the measured review to choose the next physical/circuit change; preserve
the full early/late rejection and fault receipts. The fullPHY, recovered-clock
loop and mainchip timing remain open. TX minimax fullwaves39268446646 and
mainchip route39243328773 are independent live cloud work; do not restart them.
