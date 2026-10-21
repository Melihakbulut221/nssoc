# Actual8088 parallel power128 physical candidate

The completed original8074 loaded run39592603205 is rejected, not resumed.
Run39604983700 reproduced every original rejection from its complete34ns raw.
A2.5V external AVDD reaches only1.0962804139198925V at an actual driver
terminal (maximum drop1.4037195860801075V); local AVSS reaches0.2114524030157267V.
Every CMOS input fails the original1.8V common-mode minimum. These are measured
physical terminal planes. A power repair is justified, but does not establish
that the circuit, timing or output will pass afterward.

## Physical change

This candidate starts from the same actual8074 core and14-device output.
All8088 native devices, old conductors and165 external ports remain unchanged.
It adds separate128um-wide TopMetal1 AVDD/AVSS trunks to the left of the existing
geometry,3.2um Metal5 branches to all64 native driver power terminals, and
6um TopMetal2 bridges to the original public power distribution.
Native via stacks use four columns and one row. No ideal supply is inserted
at a local terminal, no primitive or model parameter changes, and no accepted
electrical bound is altered. Every added conductor is checked against foreign
metal with1.645um clearance, followed by serialized geometry XOR and the
original full560-category DRC, unsimplified deep/flat8088-device LVS, exact165
ports and all original native fault controls.

The power path is a new physical hypothesis, not an electrical signoff.
Even a passing native DRC/LVS requires fresh whole-parent anchors, intrinsic
extraction, wireRC, audited composition and original full loaded wave checks.
Original8074 and pre-power1288088 results and saved capsules remain immutable.
Do not apply old RC to changed geometry. EM, foundry-qualified PEX, full PHY,
mainchip routing and original-clock final timing remain open.

## Reproduction and continuation

Run .github/workflows/tx-output8088-power128-physical-cloud.yml on the pinned
source commit. The initial path push triggers this workflow. Both positive
and failed native outputs are retained in the tx-output8088-power128-physical
release group. Keep native live PLL/mainchip/old fault work running.

All work and artifacts are in GitHub. No local checkout or downloaded CAD
artifact is required; the local project directory is intentionally empty.
