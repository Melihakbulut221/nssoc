# Native restored-route qualified physical connectivity

The original native wire-only reader stopped on 142 of the 828 changed nets because its conductor model omitted cell pin metal. Run 41314829887 verified all 1300 observed pins / 77 master pins against the actual frozen GDS drawing layers, LEF geometry and placed transforms. Run 41316154727 replayed all 1656 original graphs and passed the same connectivity predicate using only those independently verified pin rectangles. Neither run was a native adapter execution or complete chip acceptance.

This successor privately binds that unchanged qualified core to the original native connectivity reader. The reader still writes every original per-net wire-only observation before invoking the new physical-conductor model. The original predicate, source functions, scope checks, clocks, placement and route preservation remain unchanged. Candidate ODB bytes and both GDS qualification records are hash-bound. Changes to pin identity/shape/layer, new failures, missing diode pins, callback plan changes and candidate drift are rejected. Failed original results are retained explicitly.

Source controls retain the original 49 restoration tests and all 67 graph/GDS/model tests. Additional boundary controls execute the actual original native reader function body over all authenticated 828-net observations with simulated ODB accessors; this is source-boundary qualification, not an actual ODB engine run. The native job separately requires a successful same-source controls run and an independently reserved empty exact-source release. Actual execution checks the candidate ODB hash and uses real OpenDB accessors in the pinned original engine.

The native sequence restores original wire classes without rerouting, verifies the complete restored snapshot and 1691 protected nets, executes qualified physical connectivity, checks 2702 power contacts, then runs final DRC/antenna checks. The pipeline result identifies qualified physical audits explicitly. A completed invocation is not itself a zero-violation result: inspect the original verdict, full DRC/antenna census and bounded_cycle_qualified.

Fresh matching-netlist RC/STA, final setup/hold and full serial Gen3 x4 PHY remain separate uncompleted requirements. All physical_acceptance, timing_accepted and full_phy_accepted flags remain false. All CAD and acquisition are cloud-only; no local workspace or native payload is needed.

Frozen original source: 7a0776718ec37a106b7dfde0cbd477c6a2a5522f.
Restoration parent: 05d336a1b1b681c9d96b71d464c5ea430835e438.
Qualified core: 77247c06db249537a643fb2e6e9a256bdbcfe557.
