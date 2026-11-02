## Current continuation: full64 route source and isolated16-MOS trial dispatched for controls; complete PHY stage diagnosis preserved

Actual new-engine full-chip roundtrip41506262574 remains passed: all143820nets154480instances1691protected clocks and ODB/DEF/material snapshots identical; fullDRT92 and21antenna nets/27records remain OPEN. The9.054GB check peak is not routing memory reduction or timing acceptance.

Full64 source302f9c30a847acd659a8c451bdce83707fce5d70 is published on codex/mainchip-guide-full64-route. It explicitly uses the new ELF and authenticates the complete successful actual-chip qualification archive/fixture before routing. Original11phase bodies, original47clear/protection/restore, full64 schedule, original resources/supervision/snapshots and oldELF protection stay intact. Independent execute=false source controls41512344559 is dispatched once. Native full64 has NOT been dispatched. After successful same-source controls, authenticate all controls, dispatch execute=true with control_run41512344559 once, and reserve exact-source empty release cloud-results-RUN-1-mainchip-bulk-postdrt-antenna. Do not restart queued/live handles. Source snapshot including all transitive pins is preserved here.

PHY stage diagnosis41508059395/sourcee6c78d53d05c724c2b4adc83f86aebd47d44d9f7 SUCCESS. Authenticated derived artifact13172382269,1777693bytes SHAabc5ae184c3cfe1e477901bd50afd6f95726a7eb660028edd7e31834b5fcba7d. ALL eight derived members are permanently preserved, including complete13872333byte per-bit stage JSON and1198670byte native device diagnosis. Original complete113475x1152 raw wave remained cloud-only. Controls8 malformed waves+3 stage cases+3 actual24-list cases passed; all old scalar delays reproduced. This is diagnosis of rejected41501239838, not new successful transient.

At C bit8, sampled slave output is28.415mV at0.3UI,120.445mV at0.4UI,173.372mV at0.5UI,99.105mV at0.9UI. It first exceeds100mV and then loses hold margin; do not report118.90625ps as a successful transition time. Eight C bit windows reach that original bounded metric. Clock crossing lag1.5625..4.6875ps remains small relative to sampled data transition failure. A/B/D maxima42.96875/38.90625/49.21875ps still exceed37.5ps. Four master clock HBTs61/62/115/116 retain lowVce failures. Underlying24device trial remains rejected with no matching physical layout.

New isolated electrical proposal source d8289b3f57f23b66288cd7851b03ca81bc4954b6 on codex/cdr-slave-current-only-trial changes only16slave tail MOS widths36->48um plus consistent proposed diffusion, deriving again from original freshRC41439516945. All collector resistors retain2.6um length, all other484devices and parent interconnect RC unchanged. This isolates increased current from prior combined load reduction that coincided with C droop; improvement is a hypothesis. Actual16MOS geometry binding, exact model reversal, all frozen numerical methods, all100mV/37.5ps/voltage/current gates and150fF loads remain. Independent execute=false controls41512921089 is dispatched once; native not dispatched. After SUCCESS, dispatch execute=true once and reserve exact-source release cloud-results-RUN-1-cdr-slave-current-only-trial. A passed provisional circuit still needs matching schematic/GDS/DRC/LVS/freshPEX and repeated loaded simulation.

Source-only branches use skip-ci for frozen-ancestor general push tests; independent source controls and native experiments remain mandatory. Existing broadCI41505377046/41507901483 and their failures remain recorded. Monitor41501146100 FAILED observe/main-inventory guard: it is not a healthy monitor or successful native repair. Root inventory now includes both new handles; main synchronization remains to investigate, and automatic_native_dispatch remainsfalse.

Everything native/heavy is cloud-only; local workspace empty. Full serialGen3x4 PHY, accepted chip PCIe/Ethernet routing, final setup/hold and production acceptance remain OPEN.

Observed 2026-11-02T19:46:50.689885+00:00:
- 41512344559: queued/None
- 41512921089: queued/None
- 41508059395: completed/success
- 41505377046: queued/None
- 41507901483: in_progress/None
- 41501146100: completed/failure
