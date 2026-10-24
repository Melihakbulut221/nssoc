# Actual core/output physical integration candidate

The verified8074-device TX core and verified14-device output cell are assembled in one actual GDS hierarchy. No native material polygon may change; only documented net-label retirement and new parent metal/vias are allowed. All source GDS/reference hashes are verified in the cloud.

The core mp/mn conductors connect to output INP/INN with actual Metal5/TopMetal1/TopMetal2 and pinned native via stacks. AVSS and SUB are separate physical routes; output TVDD and IREF remain explicit external supply/bias boundaries. Native substrate BULK remains common while the core's separate CMOS wells remain intact. The reference contains8088 unsimplified devices and165 public ports; mp/mn are internal.

The candidate must pass the unchanged560-category native DRC and unsimplified deep/flat LVS. Real data-route open, body/supply short, wrong core MOS width, wrong output HBT Nx, swapped output inputs, internal-port alias and offgrid controls must reject their intended corruption. Obstacle checks are only a routing screen, not DRC or LVS acceptance.

A geometry pass requires fresh full-parent wire extraction and all-terminal RC composition, followed by the original loaded34ns/256-bit electrical tests. The existing8074 native simulations stay untouched. Clock modulation, clock/bias assembly, output reference feed, mainchip power/PHY integration and final timing remain open. This candidate is not full serial Gen3 x4 acceptance.
