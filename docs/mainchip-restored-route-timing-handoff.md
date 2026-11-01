# Restored diode-route handoff to final timing

Source review at 2026-11-01T12:29:29.344125+00:00, root 219ea87c8ee9441be8fea37c31feded35f661b73. This is an admission/integration finding, not an executed STA or RC result.

The existing route12 geometry controller requires153130 retained instances and ZERO added diodes (scripts/cloud_mainchip_route12_postroute_geometry.py:77). Its numerical worker pins the old resized netlist SHA2563c053c4cda51a001b926cce347b97de5c825cbff2082de550eeb9e31ff7fe5cd (scripts/cloud_mainchip_route12_postroute.py:136). The active saved-route restoration has1351 antenna diodes,608 original antenna owners plus220 counterpart routing owners and1691 protected clock/fixed owners. The old route12 admission is therefore not directly reusable for this new candidate.

Do not erase the old added_diode_count==0 assertion or substitute the old netlist to make the new route pass. First inspect actual native restoration41305082558 and authenticate its selected routed source,full archive,candidate/final-measured ODB,original-class restoration,exact connections,1691 protected records,two connectivity modes,all1351 attached diode pins and2702 PG contacts. Failure cleanup or pre-route fallback cannot supply a successful restored candidate.

A new admission boundary must prove the exact candidate ODB/DEF and a matching diode-inclusive logical/physical netlist. Preserve all original functional instances and memberships and distinguish the explicitly proven diode additions. Export/read back the current native database and prove that export does not alter it. The previous128-resize handoff remains provenance,not a substitute for current diode-inclusive connectivity.

After that boundary is actually qualified, reuse the original numerical RC/STA behavior with exact current state pins. The old worker already distinguishes native_physical_gates_met from all_reported_timing_and_electrical_gates_met; it can preserve failed measurements without claiming signoff. Do not weaken its original timing_gate,finite-metric checks,report completeness,propagated-clock proof,source integrity or physical decision.

Required cell corners remain nom_slow_1p08V_125C,nom_typ_1p20V_25C,nom_fast_1p32V_m40C. Original20/4/8/8ns clocks and5percent derates remain required. All setup/hold slack must be nonnegative and setup/hold/slew/capacitance/fanout violation counts zero. Use newly extracted SPEF for the actual restored database; do not carry over prior route SPEF or metrics. Nominal RC and three cell corners still do not establish qualified foundry RCmin/max,full-chip DRC/LVS,full serialPHY or production approval.

The complete source-file fingerprints and live-run observation are in docs/evidence/restored-route-timing-handoff-v241.json. No numerical program,source-control test,RC extraction or timing measurement was executed by this review.
