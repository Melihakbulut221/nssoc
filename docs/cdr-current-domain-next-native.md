# Rejected sampler comparison and current-model correction

All four complete34.25ns wave records were reauthenticated from exact run/source/artifact digests. Every case is electrically rejected; no row is an accepted PHY or a matching new layout. The118.90625ps metric indicates a failed validity window, not successfully settled data.

| Variant | Run | Phase mV | VI uA | A/B/C/D maximum metric ps | A/B/C/D wrong signs |
|---|---:|---:|---:|---|---|
| parent | 41441047354 | 14.325205 | 43.051234 | 45.78125 / 41.71875 / 51.09375 / 54.53125 | 0 / 0 / 2 / 34 |
| combined | 41501239838 | 12.974092 | 39.691842 | 42.96875 / 38.90625 / 118.90625 / 49.21875 | 0 / 0 / 0 / 0 |
| current_only | 41514109475 | 15.796080 | 46.852669 | 45.78125 / 41.71875 / 51.40625 / 53.28125 | 0 / 0 / 8 / 46 |
| load_only | 41521089374 | 11.576923 | 35.922831 | 42.96875 / 38.90625 / 118.90625 / 50.15625 | 0 / 0 / 0 / 0 |

Required phase>=30mV,VI>=50uA and maximum clock-to-valid<=37.5ps remain unchanged. Load-only removes wrong signs but loses C hold margin and reduces phase/VI. Current-only worsens C/D wrong signs and adds an HBT activeVce failure. Combined drive/load also fails. Do not choose a visually improved partial metric as acceptance.

The actual load-only runtime census matches all three MOS library hashes in native domain audit41286495589. Full current500-device mapping contains50 MOS,42 wider than the stated0.15..10um model range, allng=1. Widths are8um(8 devices),32um(2),36um(32),53.335um(4),64um(4). Earlier standalone stress/physical gates did not close this model-domain gap. This is recorded in docs/evidence/cdr-current-domain-model-proof.json.

Current proposal source9324e2da283540c6d4f1a1bec18641ccec30fefa on codex/cdr-current-domain-partition preserves original current freshRC41439516945 and all98 resistors, partitions50 MOS to200 independent model-range units, retains all450 non-MOS primitives and parent wireRC. Source controls41526131863 passed every partition and24 refusal cases, including an11um/7um pair retaining total36um and correct junction formulae that must fail at the exact domain predicate. All controls are synthetic source fixtures; no new650-device native binding, waveform, geometry or extraction has run.

Next actual implementation must use the current500 parent binder and current native cluster/net identity, not the historical mixed20-resistor candidate or old geometry map. Retain original13 binding faults, all12 expansion faults,200 MOS current channels and1301 complete observation vectors. Adapt only required counts, not any clock/stimulus/load or electrical predicate. Then generate actual independent PCells/contact/tap/routing geometry, full650-device deep+flat LVS/DRC, fresh wire/MIM and repeated full waves. Model-range width alone does not close PVT, layout effects,closed-loopCDR/PLL,completeGen3x4 or mainchip timing.

Mainchip41513663302 is still the original live full64 route. Its final measure() checks full DRC/antenna and unchanged route snapshot, and explicitly leaves original-global-class restoration, diodePG and fullLVS acceptance false. Before finalSTA, authenticate the actual completed capsule, audit/restore required classes and diodePG, generate the exact physical candidate and completeLVS/DRC as applicable, then use matching qualified extractedRC and SRAM/cell libraries for all required setup/hold corners. No such timing result is implied by a route-job success.
