# Phase55 actual child-load contract and reset design candidate — 2026-10-24

The exact phase55 native composition is available; its electrical phase/load behavior and deterministic reset are not qualified. This change prepares a separate source-only experiment and a separate physical-device reset hypothesis. It does not replace the 62 ideal clock legs or 25-ohm test accesses in the full TX test.

## Verified prerequisite

Native run [40086006467](https://github.com/Melihakbulut221/nssoc/actions/runs/40086006467), source `c7cb559701eb5b05194110ef3c9bf8bd43626db0`, passed both precise native record orders, original 13 raw controls plus nine actual-MIM controls per order, and 19 composition controls. The exact receipt is `docs/evidence/tx-phase-divider-mim-precision-pass-20261024.json`.

- Summary asset 671984522; SHA256 `f93c6fcd7d454657ddca46986320d336cde713c6f7c7eb9389b16c9505a84b95`.
- Complete parts asset 671984570; SHA256 `e501214075a8d1e76a4d087eb2e6c4528386501731ba8e64019e20844b5b4198`.
- Model `composition/phase55-wire.spice`; SHA256 `18c980350b1d3ea298e36462f3954155ac0022306645e42b38caacccbd8e08b6`.
- 55 devices, 168 terminals, 126 physical reference anchors, 24 wire components, 238 resistors and 410 capacitors. All four actual intrinsic MIM devices remain once.

## Real child-load diagnostic, awaiting measured input boundary

`scripts/tx_phase55_loaded_contract.py` prepares one exact composed divider with its MP/MN and QP/QN outputs each driving the real clock inputs of another identical composed divider. This uses 165 actual compact devices, 12 native MIMs, 714 wire resistors, 1230 wire capacitors and complete terminal/current probes for all 57 HBTs. Intermacro connections are explicit test boundaries; there is no newly routed parent. It uses neither an ideal output capacitor nor a guessed 25-ohm connection.

The original fixed timing is retained: 4 GHz differential input, 2 ns start, 34 ns stop, 256 125-ps observation intervals, 10-ps input transitions and maximum 0.3125-ps timestep. Trap settings remain tight. No initial state, UIC, nodeset, internal clock source or forced reset is introduced. The fixed positive mapping is MP→sa and QP→sb; no sign or origin is selected after observing results.

The source controls compare this timing with the unchanged original `run_cloud_tx_mux4.py` functions. Its 31 pairs comprise one 4-GHz, two 2-GHz, four 1-GHz, eight 500-MHz and sixteen 250-MHz clocks. The master is transparent on clock-low and the slave on clock-high. A correct divide-by-two pair should therefore have 2-GHz outputs and nominal 125-ps same-polarity master-to-slave spacing, plus actual device/path delay. This topology does not establish absolute startup phase. The original unequal 2.2×2/2×2-µm seed MIMs remain, but are not accepted as deterministic reset.

Input common mode and swing have **no production defaults**. They must be bound to the completed root observer run 40084454916 and the exact pair `div1_first_div2`: `v(xloop.w_t398_c)` / `v(xloop.w_t389_c)`. This pair is the real PLL first divide-by-two high-common-mode output. Its measured values are still pending when this source is written. The future controller must independently restore/hash the observer report and verify the exact field-to-scalar binding; the helper deliberately reports that binding as unverified. A syntactically valid boundary is not accepted provenance.

The isolated source still uses a fixed-frequency external test clock. It is not actual PLL replay or PLL connection. Before any native dispatch, the controller must additionally validate the qualified engine/models, exact model restoration, zero operating point, every native column and terminal, solver diagnostics and complete capture. The source-only control workflow does not contain a native electrical job. The all-HBT screen retains VCE≥0.4 V after startup, whole-trajectory |VCE|≤1.6 V, |VBE|≤1 V and |IC|/emitter≤3 mA.

The first-cell MP/QP assignment is not a recursive all31 wiring plan. For parent origin O and halfperiod H, the master/slave divide-by-two origins are O−H and O. At the next level the original stride4 clocks require origins START−2UI, START−UI, START and START+UI. The sa-driven master produces START−3UI; reaching the desired START+UI periodic phase requires a fixed polarity swap (one child halfperiod), together with a separately defined startup sequence. Other branches also need explicit ownership. A modulo-period match does not prove the original startup interval. All deeper phase routes and reset/release schedules must be fixed before testing, never fitted from a passing waveform.

A downstream divider is a real fanout load, but this bench does not yet contain the TX selector-level clock buffer or selector load. Phase55 outputs are a high-common-mode interface; the actual selector level must be implemented and measured, not connected by an assumed ideal translation. The eleven existing qualified clock leaves are DC-reference cells, not clock-distribution drivers.

## Separate physical reset/synchronization hypothesis

`clock_div2_reset_feedback_candidate_v1.spice` is an unqualified schematic candidate, with only native HBT, resistor and MIM devices and unchanged latch subcircuits. It contains:

1. A real two-flop CML request synchronizer with no initialized state.
2. The exact existing high-input limiter and MIM feed-forward network to reach the selector-control domain.
3. A real CML feedback selector. Reset selects native resistor-derived differential seed levels; run selects the actual inverse feedback.
4. The original two latch cores, tail reference and seed MIM geometries, changing only the master's data connection to that real selector.

Relative to the original tail schematic this adds 41 HBTs, 37 resistors and two MIMs (80 compact primitives). This is a schematic census only; new body contacts, device placement, native DRC/LVS and fresh RC have not been implemented. The old qualified 55-device RC model must never be reused for this modified topology.

The seed-divider dimensions are explicit unqualified design choices. DC transfer, supply corners, HBT headroom/current, metastability, synchronized release, added feedback delay and full-load phase margin all require new native validation. No reset operation is claimed.

Crucially, holding an upstream divider in reset stops its children's clocks. This feedback-only scheme cannot asynchronously set a closed master; simply cascading locally synchronized resets would deadlock or leave unknown child state. Full31 deterministic startup therefore still requires a physically implemented global reset/phase sequencer or qualified asynchronous latch preset, followed by an end-to-end phase-ownership test. The candidate is a bounded single-free-running-clock experiment, not a completed clock-tree reset.

## Exact next sequence

1. Independently review the source-only bench and controls.
2. Obtain the terminal PLL observer's exact common-mode/swing evidence; preserve its acquisition failure separately.
3. Implement the strict cloud restoration/capture controller and run the existing physical55 child-load diagnostic with that explicit external boundary.
4. If the existing phase cell passes, implement and qualify real selector-level buffers, routed parent fanout and an actual deterministic phase/reset mechanism. Any changed device topology requires fresh physical extraction.
5. Connect the real PLL, then all31 actual mux clocks, and run original full-TX bit/phase/load gates with no internal ideal sources.

No acceptance here extends to a complete clock tree, PLL acquisition, serial PCIe PHY, four lanes, main-chip routing or final timing.

## Source-review corrections

The independent source review found missing corruption-oracle checks for the reset level subcircuit's public port order and the selector's seed/load/bleeder resistors. The oracle now verifies those exact ports, all selector cards and their endpoints/geometries, with separate port, symmetric-seed, wrong-endpoint and bleeder-value faults. Path validation also now rejects actual newline, carriage return, quote and NUL characters. These are source-control coverage corrections; they do not provide native reset acceptance.

A second independent review found a real positive-preparation bug: finite ptap1 contact cards have five tokens, so indexing token5 on every compact card raised IndexError before the deck could be built. Preparation now classifies each card by its model-specific terminal count and exact parameter schema, preserving the 19 HBT/20R/4MIM/12-contact census. The cloud controls additionally restore the exact existing qualified model archive, verify its complete bytes/hash and terminal producer, exercise a positive three-macro preparation with an explicitly unverified fixture boundary, and reject six mixed-card corruptions. This control does not execute SPICE or validate the fixture amplitude as a PLL measurement. The earlier green source run40088526578 did not exercise that positive path and is not evidence of successful deck preparation.

## Terminal positive-preparation result

Cloud run40089341166 atb8dd0024230b81a8d918cd29e61fb433dc5e348f passed positive preparation using the exact qualified55-device model, including all12 five-token contact cards and57 HBT bindings. It rejected six mixed-card faults, five phase-observer faults,15 boundary/path faults and13 reset-topology faults. Generated fixture-deck SHA256: f8844e7be1b3f96820d3cfeb573797848cf33f417e94e3adecec71373d0d02ed. This is source preparation only: the fixture boundary is not a PLL measurement and no native simulator ran. Full receipt: docs/evidence/tx-phase-source-preparation-and31-mapping-pass-20261024.json.
