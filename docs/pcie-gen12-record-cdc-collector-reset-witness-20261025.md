# Collector reset witness, 25 October 2026

Source-only candidate: no controls, compilation, simulation or retry has run.

Complete proof 40202709622 at 81ac935fe1fb1ce6dde4e70032f8aa37957dc4e9 passed 66 RTL tests, 33 mapped tests, six synthesis checks and 16 compiling mutations. The seventeenth mutation collector_reset_POR_only compiled but reached the unchanged harness's generic until() timeout at line 104 from the same-polarity reset scenario. The classifier correctly refused that origin. The final ignore_polarity mutation was not executed. Complete rejected result, hosted log and observed trace remain at checkpoint 521c5c99777000283521cf75847b70645f71d482; this is not complete CDC acceptance.

The composed wrapper explicitly resets its collector with cdc_running; either public reset asynchronously lowers it. The qualified raw32 receiver resets public boundary_valid_o and rd_o to zero. The unchanged independent serial oracle clears acquisition and RD on reset. Replacing only collector reset with por_ni leaves an acquired boundary while the rest resets. This source-derived prediction still requires hosted measurement.

The new subsection first retires two independently encoded COM-started records and requires actual public boundary/RD to match the acquired oracle state. For both initial polarities and both reset domains it holds reset with unchanged polarity, then requires both public fields zero at the existing 1,100 ps asserted-reset observation interval. This observes an asynchronous reset, not a new throughput deadline or protocol timer. The bounded JSON witness records simulation times, reset port, prior oracle/public state and expected/actual fields before either guard fails.

All original scenarios, shared harness, serial oracle, RTL, mutation definitions, toolchain, synthesis, resource limits and cleanup remain byte-identical. The subsection is prepended to the existing named test, preserving 66/33 counts. Priming failures, unknown values and the old generic timeout remain unqualified for this mutation.

Only collector_reset_POR_only gains the two literal-message plus exact-AST public guards. Existing XML error type, nonzero exit, actual final traceback file/line and source pins remain mandatory. Supplemental hosted controls use actual source sites, refuse changed predicate/port/operator/value/message/type/site and generic timeout, and refuse both new guards for all other mutations. The prior 63 groups remain unchanged.

The pinned targeted plan requires both RTL engines, mapped baseline and the compiled fault before a separate full-retry review. Its controller and target-specific trace admission are explicitly not implemented yet. Native flags are false, and no job, release or registration is dispatched. Full training ownership, LTSSM, lane/rate negotiation, physical CDC and full PHY remain open.

Exact sources at the failed engineering ref:
- Wrapper soc_pcie_gen12_recovered_records_v1.v SHA256 3c60eead90fe053c2615b76d44e1d5c74add6b3351a3cd85f76572ac3faabf20.
- Receiver soc_pcie_gen12_raw32_rx.v SHA256 96c6dea3aecca038dc8d5322d2c4a85d7847dbe24bc45a1b4a22d27301980566.
- Shared harness SHA256 c928cf3c61a2a9cb26d3203b99ddeef98661d5eebb48b74e8f2af295a6a62979.
- Reversible edits: scripts/pcie-gen12-record-cdc-collector-reset-witness-derivation.json.
- Hosted plan: docs/evidence/pcie-gen12-record-cdc-collector-reset-targeted-proof-plan-20261025.json.
