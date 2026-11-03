# Actual restored-route handoff to extracted timing

This stage restores the original full-chip route classes and exports a diode-inclusive physical netlist from the resulting ODB. The older route12 adapter remains unchanged: its zero-added-diode and153130-cell requirements describe a different design.

The initial native qualification input is completed run41440285882 at0990e2971dee0333598a59a033dfe4f1f1f4215b. It has154480 instances,143820 nets and1351 additions relative to the exact153129-instance input. This is the existing candidate with known physical violations, NOT the still-running full64 candidate41699812301 and NOT physical signoff. The same implementation must subsequently consume the sealed completed full64 output. No route is restarted by this job.

The cloud worker authenticates every original capsule member and pinned runtime; restores route classes through the previously qualified two FLOORPLAN imports; compares the complete resulting DEF to the independently computed class-only transformation; checks every original instance, all net identities and original1691 clock/fixed records. Logical diode supply pins must match the existing physical diode template. This logical PG check is explicitly not a geometric supply-continuity or transistor LVS proof.

The candidate netlist is written with OpenROAD write_verilog -include_pwr_gnd, read into a fresh library-only database, and linked again. All instances/masters, all instance pin nets, all ports and complete connected-net incidence must agree with the original physical database. There is no diode filter and no physical-cell exclusion. Unused declarations are enumerated explicitly. Mutations of actual diode signal/supply/master, diode omission and a boundary connection must be rejected. Unsupported writer/reader behavior fails the stage rather than silently omitting physical instances.

Official API references:
- https://github.com/The-OpenROAD-Project/OpenROAD/blob/master/src/dbSta/src/dbReadVerilog.tcl
- https://openroad.readthedocs.io/en/latest/main/src/README.html

Full native DRC and antenna checks run again after restoration, with before/after full snapshot equality proving that measurement did not change geometry. Their observed counts are preserved even if nonzero.

No success in this stage accepts physical supply connectivity, transistor LVS, extracted timing, or the full serial PHY. Required successors are full64 result admission using this implementation, actual diode PG geometry audit, fresh RC and original20/4/8/8ns three-corner setup/hold (with original derates and electrical checks). Native payloads stay in GitHub runners/releases; only source and derived summaries are coordinated locally in memory.
