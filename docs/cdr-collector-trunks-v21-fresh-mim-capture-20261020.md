# CDR v21 fresh native MIM capture and next audit

All four extraction stages in 39441534722 passed. Native MIM capture 39443205735
also passed, at source 01b1874ac35f0c020bc315fa65f67645b3d15790.
The independent result is 17,674 resistors, 12,704 capacitors and eleven explicit
native MIM devices, covering 946 physical points in 111 conductors. This is eight
fewer exported parasitic capacitors than v20; capacitance magnitude and electrical
improvement cannot be inferred from element count.

The original mask and point binding tests and all five capture fault controls
remain intact. The exact release SHA-256 values and complete native capture and
model-binding reports are committed with this handoff.

The subsequent raw audit and model composition retain every original resistor
and capacitor topology/value conservation check, thirteen raw-wire faults, nine
intrinsic-device faults and nineteen composition faults. Source changes are
limited to candidate identity and the independently measured capacitor census
(12,712 to 12,704; total R+C 30,386 to 30,378). An exact source delta guards these
changes. Native MIM models must appear once, with actual terminal ownership.

This is capture evidence, not qualified PEX or electrical acceptance. The next
required step after audit/composition is the unchanged loaded early/late waveform
test and its fault controls. Mainchip 39436610858 and PLL 39423618115 remain live.

A redundant queued dispatch 39443299245 was cancelled before execution; the
successful push-triggered capture 39443205735 is the only accepted source.
All work and retained evidence are cloud-only.
