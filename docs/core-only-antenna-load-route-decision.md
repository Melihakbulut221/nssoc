# Antenna load and detailed-route repair decision

Current 50MHz/20ns and5%derate remain unchanged. No electrical or antenna violation is waived.

Native inventory44316553449 authenticated171fanout violations:all native input-terminal counts matchSTA;all includeCORE_ANTENNACELL `sg13g2_antennanp`. There are1260ordinaryCORE and671antenna inputs across these nets. Every nonantenna sink count<=8. OneCLOCK net has6ordinary+11antenna inputs. Reported fanout remains a real configured constraint; this classification does not remove parasitic capacitance or prove safety.

Candidate44318129858 inserts348buf4 into170SIGNAL nets, retaining every original cell, antenna cell and placement. Clock net is untouched. Buffer contraction proves logical connectivity classes, not antenna protection on the newly split physical segments. Fresh detailed routing, antenna calculations, RCX and cornerSTA are required.

## Source-verified next route option

The pinned [OpenROAD Tcl implementation](https://github.com/The-OpenROAD-Project/OpenROAD/blob/dcf36133a369abc8f3c5e5738cd4d82e4903c0e0/src/grt/src/GlobalRouter.tcl) explicitly accepts `repair_antennas -jumper_only` and rejects combining it with `-diode_only`. The README lists fewer options than this implementation; do not infer absence of support from that abbreviated README.

[LibreLane3.0.5 DetailedRouting configuration](https://github.com/librelane/librelane/blob/3.0.5/librelane/steps/openroad.py) exposes `DRT_ANTENNA_REPAIR_JUMPER_ONLY`. Its [native DRT script](https://github.com/librelane/librelane/blob/3.0.5/librelane/scripts/openroad/drt.tcl) forwards `-jumper_only`, invokes `check_antennas`, and reruns detailed routing after jumper-only repair even when no diode was added.

For the next accepted routing trial, prepare a separate config copy with `DRT_ANTENNA_REPAIR_JUMPER_ONLY=true` and `DRT_ANTENNA_REPAIR_DIODE_ONLY=false`; prove all unrelated settings unchanged. Preserve existing antenna cells and all clock/timing constraints. Do not apply this to the running global-route job44319155353. This option avoids additional repair-diode insertion; it does not remove existing diodes or guarantee closure.

Admission still requires: native DRC0, antenna0 under available LEF rules, unchanged functional topology/PG/boundary geometry except explicitly audited changes, fresh actualSPEF and all corners, and recorded electrical residuals. If jumper-only fails antenna closure, retain failed reports and reject that result; do not suppress checks. Hidden macro GDS/qualified process antenna signoff and manufacturer approval remain separate.

The DRT script references `GRT_ANTENNA_REPAIR_MARGIN` while the configuration class also defines `DRT_ANTENNA_REPAIR_MARGIN`; verify the actual effective margin rather than assuming the similarly named setting is used. Do not lower margins to produce a pass.
