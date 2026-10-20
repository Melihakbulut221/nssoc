# Routed native ECO result and electrical buffering continuation

Run[39392483151](https://github.com/Melihakbulut221/nssoc/actions/runs/39392483151)
completed fresh detailed routing, nominal OpenRCX and three cell-corner STA.
It retained all151051 candidate instances and added27 independently checked
antenna diodes, giving151078 actual routed instances. Detailed-route DRC,
critical disconnected pins and final antenna violations are all zero.
The fixed physical clock route and original cell/pin/NDR/port geometry pass
their independent guards. These checks are not transistor LVS or foundry signoff.

| Corner | Setup count | Hold count | Worst setup(ns) | Worst hold(ns) | Slew | Cap | Fanout |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| slow1.08V125C | 9638 | 3 | -13.346324 | -0.513009 | 3630 | 725 | 2149 |
| typical1.20V25C | 6195 | 10 | -5.113267 | -0.425175 | 444 | 737 | 2149 |
| fast1.32V-40C | 3150 | 19 | -2.211621 | -0.362199 | 91 | 757 | 2149 |

Against the prior routed baseline, worst setup improves from-15.803526ns
slow,-6.502469ns typical,-3.161320ns fast. Typical setup count improves7027→6195.
Hold and electrical violations remain, so final timing is not closed.

The previous setup pass intentionally skipped buffering and did sizing only.
This continuation first runs native repair_design with10% slew/cap repair
margins, then enables setup load splitting/buffering and sizing. Both use
80% maximum utilization; setup allows80iterations and8repairs/pass.
Hold retains the original0.1ns optimization margin and may not introduce
setup violations. These are optimizer controls, not acceptance relaxations.

The [OpenROAD resizer documentation](https://openroad.readthedocs.io/en/latest/main/src/rsz/README.html)
describes repair_design for slew/cap/fanout and wire-delay repair.
The exact pinned dcf36133a369abc8f3c5e5738cd4d82e4903c0e0 Tcl source was checked
for the actual supported flags. No newer command syntax is assumed.

The controller restores the exact new routed ODB/netlist/SDC/SPEF, nineteen
pinned PDK files and original three corners. Before any mutation it must
reproduce all six measured worst slacks within1ps, with original20/4/8/8ns
propagated clocks,5% derate,0.25ns uncertainty and20SRAMs. Router initialization
must preserve physical DEF and six literal timing reports.

Original instance retention, clock/SRAM geometry, clock pin nets, supply
routes, NDRs and external pins remain independently guarded. Only native
positive buf/dlygate cells may be added. Supplies connect actualVDD/VSScell
pins toVPWR/VGNDnets. Full Liberty/Yosys equation proof and an actual inverted
buffer negative control remain mandatory. Electrical/setup/hold checkpoints
are retained even if subsequent checks reject the candidate.

A successful optimization candidate still requires fresh routing, antenna
repair, OpenRCX, all three timing corners and the unchanged zero-violation
acceptance gates. No estimate is substituted for routed timing. Qualified
min/max PEX, transistor LVS, full serialPHY and manufacturing approval remain
outside this result. Everything runs and is archived in GitHub.

## Actual first-pass rejection and data-input protection repair

Run39403242252 reproduced the six saved worst slacks and began native
electrical repair. It then stopped atRSZ-3006 because the protected SRAM
u_eth.u_mac.tx_fifo.fifo_inst.u_sram.g_bank[0].u_mem/A_ADDR[5] prevented native
InsertBufferBeforeLoads onnet4517. This is an optimizer integration failure,
not timing closure. The failed logs and source baseline are retained.

Whole-instance dont-touch was stronger than the intended geometry constraint.
Before electrical repair, restore each instance's original flag while keeping
all protected clock nets dont-touch. Exclude every drive strength in each
actual clock-pin cell family, and each hard-macro family, from resizing.
Buffering a data input is thus permitted; resizing/moving SRAM or sequential
clock cells remains forbidden by independent post-repair geometry checks.
The original netlist equation proof, actual inversion control and fixed
physical clock proof are unchanged. No clock, SDC or acceptance gate changed.

If electrical repair itself errors again, save its unchecked ODB and netlist
before propagating the error; no partial repair is accepted automatically.
