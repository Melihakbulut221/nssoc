# Fixed31-clock ownership and physical reset requirements — 2026-10-24

This is an analytic design contract, not a physical clock-tree result. The original TX source oracle is unchanged: `scripts/run_cloud_tx_mux4.py`, SHA256 `bb7f5c5ef736dd54c5ed560424d97d248894f4aa6fa6119f1e95c5f5c3df4b52`. The proof imports only its actual `tree_plan` and `pwl` function ASTs plus literal UI/START/BITS, and compares every transition and all 31×256 original sample centers. It executes no native simulator and supplies no measured PLL amplitude.

## Fixed physical ownership

The original stimulus requires one 4-GHz, two 2-GHz, four 1-GHz, eight 500-MHz and sixteen 250-MHz differential pairs. Fifteen divide-by-two instances can provide the thirty slower pairs. The external 4-GHz pair remains an explicit test boundary until the actual PLL output and its loading are qualified.

Let a parent have halfperiod H UI and original offset k, where H is1,2,4 or8 and k ranges0 through H−1. Its original origin is START+(k−(log2 H))UI. A native master/slave divide-by-two produces steady-state master/slave origins O−H UI and O.

The fixed ownership used here is:

- QP/QN drives the child at offset k+1 with unchanged polarity.
- Master output drives child offset (k+1−H) modulo2H.
- When k<H−1, child positive connects MN and child negative connects MP.
- For k=H−1, child positive connects MP and negative connects MN.

This yields eleven swapped master pairs, four direct master pairs and fifteen direct slave pairs. Swapping real differential wires implements polarity; an analog inverter is not invented. The complete cell/port mapping is emitted by `scripts/tx_phase31_source_mapping.py` and preserved as a cloud artifact.

The first two levels are:

| Parent | Master output owner | Master positive/negative pins | Slave output owner |
|---|---|---|---|
| s | sa | MP/MN | sb |
| sa | sp4_3 | MN/MP | sp4_1 |
| sb | sp4_0 | MP/MN | sp4_2 |

Simply repeating MP→lower offset and QP→upper offset would violate the original phase oracle. A periodic phase match also does not establish the finite startup sequence.

## Physical startup requirement exposed by the oracle

Every external original clock pair begins positive. Therefore the four direct-master cells require internal MP=1, QP=1 initially; the eleven swapped-master cells require MP=0, QP=1 initially. MN and QN must be their complements. These 0/1 values denote Boolean differential polarity only, never a0-V or1-V analog terminal assignment or a forced simulator state.

The existing CML slave is transparent when its parent is high. Without an independent physical preset/hold, MP=0 would immediately pull QP=0 and destroy the required initial state. An ordinary feedback-only reset or a uniform all-positive reset cannot satisfy this contract.

A sufficient abstract sequence is:

1. Physically hold the required independent master and slave states while the parent output is initially high.
2. Arm the cell from a real global reset distribution.
3. Release normal latch operation at the first actual parent falling edge after arming. The master can then evaluate inverse Q while the slave enters its hold phase.
4. Permit the following parent rising edge to transfer master state into the slave.

For a swapped-master cell, MP stays0 on that first falling edge, QP falls on the following rising edge, and MP rises on the second falling edge. Its swapped external master output therefore first falls at exactly the later phase required by the original source. For a direct-master cell MP first falls at the first parent falling edge.

The analytic model demonstrates the required event ordering with zero device delay. A real asynchronous preset and release sequencer have **not** been implemented or qualified. Reset removal/recovery, skew, metastability, finite propagation and all voltage/current/load limits remain native electrical work. A local falling-edge release circuit itself needs a deterministic physical global reset; it cannot inherit an assumed initialized flop.

This sequence avoids relying on clock cycles from a parent held forever in reset, but requires independently controlled master/slave presets. The earlier feedback-selector hypothesis does not provide those functions and cannot be promoted into a full31 reset implementation.

## Scope and controls

The cloud-only source proof checks every original transition list and7936 sample centers under those explicitly required abstract preset/release functions. Seven faults change master polarity, master preset, slave preset, release before the first fall, skip the first fall, never release, or swap output ownership. A passing result demonstrates the source relation only.

Nothing here changes the original clock waveform, bit oracle, frequency, 125-ps spacing, or acceptance threshold. No adaptive polarity, phase fitting, .ic/UIC or measured-swing substitution is used. The model does not produce a SPICE reset source or claim that abstract preset operations exist in the current55-device layout.

Next physical work is a real independent asynchronous latch-preset primitive and deterministic release circuit, followed by native DRC/LVS, fresh two-order RC, all-device safety, loaded phase ownership and actual routed parent validation. The exact existing phase55 child-load diagnostic has now passed exact-model source preparation but still awaits the measured PLL boundary and a reviewed native controller.

## Terminal analytic result

Cloud run40089557733 atc3daf9a88e3476bc6d477b4d6e6e9b1c85103155 passed every original transition list,7936 sample centers and all seven faults. The complete source proof and joblog hash are preserved in docs/evidence/tx-phase-source-preparation-and31-mapping-pass-20261024.json. Hardware/reset/PLL flags remain false.
