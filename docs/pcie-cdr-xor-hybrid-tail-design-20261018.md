# CDR XOR current-source repair and physical validation — 2026-10-18

This record covers one comparison leaf of the PCIe CDR. It does **not** establish a recovered-clock loop, full serial Gen3 x4 PHY, main-chip integration, or final timing closure. All simulation, layout generation and native physical verification in this campaign run on GitHub-hosted runners. The local task workspace remains empty.

## Failure being repaired

The previous extracted 406-device phase detector failed its loaded waveforms. Its four XOR current-source HBTs and two select-buffer current-source HBTs had insufficient collector-emitter voltage. The independently verified select-buffer replacement is recorded in [its physical receipt](evidence/cdr-select-hybrid-v2-physical-pass-20261018.json). Retimed sampler input attenuation remains an additional failure and is not fixed by declaring either leaf successful.

The XOR repair starts from `cdr_xor_core_shunt_v4.spice`. The first candidate replaces only the reference HBT XD0009 and the two current-source HBTs XD0049/XD0053 with native SG13G2 low-voltage NMOS devices. The reference is W=8µm, L=0.3µm; each tail is W=64µm, L=0.3µm, one gate. The 16 data/select HBTs, eight physical resistor values, 27 finite substrate contacts and explicit crossed-input XOR polarity are retained. SUB and AVSS remain separate circuit ports.

[Candidate v1 run](https://github.com/Melihakbulut221/nssoc/actions/runs/39114172170) passed nominal and hot data/device gates but failed the cold device gate: 12 data HBTs exceeded the unchanged 1V VBE limit, reaching 1.002794775V. All 768 cold data samples were correct; data correctness did not override the device rejection. The [complete rejection receipt](evidence/cdr-xor-hybrid-v1-cold-rejection-20261018.json) preserves all five reports and immutable cloud archive hashes.

Candidate v2 increases the twelve data HBTs from Nx=3 to Nx=4. Selectors, MOS reference/tails, loads, finite-body network, stimulus and acceptance thresholds are unchanged. A source-delta guard checks that exact change, revalidates the preceding three-device replacement, and rejects altered data sizing, resistor values and tail width.

## Native component results

[Candidate v2 run](https://github.com/Melihakbulut221/nssoc/actions/runs/39114595894), source `1a80f767bb7ab4701843feaf9373107721bc05e7`, passed all three nominal cases and both intentional fault cases. [The evidence receipt](evidence/cdr-xor-hybrid-v2-component-pass-20261018.json) contains the full reports and hashes of each summary/parts manifest.

| Case | Incorrect samples / 768 | Minimum signed differential margin | Maximum input-to-valid delay | Maximum HBT abs(VBE) | Outcome |
|---|---:|---:|---:|---:|---|
| Nominal | 0 | 230.356mV | 11.719ps | 0.919375V | Data/device gates pass |
| Cold / high supply | 0 | 223.684mV | 10.469ps | 0.978634V | Data/device gates pass |
| Hot / low supply | 0 | 232.959mV | 13.281ps | 0.826788V | Data/device gates pass |
| Outputs swapped | 768 | Negative | Invalid | 0.919375V | Expected actual fault detected |
| Bias off | 113 | Below threshold | Invalid | 0.802375V | All 768 samples below 100mV; expected fault detected |

The bench uses two independent 256-symbol PRBS sequences at 8GT/s, includes all four XOR input combinations and samples at 0.3/0.5/0.7 UI. It uses a 34.25ns native trajectory, a maximum 0.3125ps step, zero-source operating point and verified native HBT OFF initialization. All five runs completed with no numerical diagnostics and unchanged protected sources.

Acceptance remains: at least 100mV signed margin, input-to-valid delay no greater than 0.3UI (37.5ps), active HBT VCE ≥0.4V, all-time abs(VCE) ≤1.6V, abs(VBE) ≤1V and collector current below 3mA per emitter. MOS terminal voltage checks retain the 1.32V limit and nonnegative active VDS; each tail must supply at least 0.5mA. These are screening limits, not a complete foundry reliability qualification.

The component has external ideal 500µA reference current, 2V data and 1.3V selector common modes, 300mV differential input swings through 10Ω sources, and 50fF per output. The nominal/hot/cold tests use HBT typical models with temperature, supply, resistor and MOS corner changes; they are **not a full process-corner matrix**. External stimuli and loads are not substitutions for extracted parent captures.

## Actual geometry and retained DRC failure

The initial physical workflow failed before generation because a copied matrix supplied the wrong `--kind` value. Its [dispatch failure receipt](evidence/cdr-xor-hybrid-physical-dispatch-rejection-20261018.json) distinguishes this preparation error from a physical verdict.

The corrected [XOR57 physical run](https://github.com/Melihakbulut221/nssoc/actions/runs/39115444772) generated an 826µm × 224.63µm GDS with 16 HBTs, three MOS devices, eight resistors and 30 finite substrate contacts. The extra three contacts were placed near the MOS active stripes. Actual native DRC executed all 560 categories and found two LU.b markers; the candidate was rejected before LVS. [The complete physical rejection](evidence/cdr-xor-hybrid-v2-physical-latchup-rejection-20261018.json) is retained.

The pinned upstream [LU.b deck](https://github.com/IHP-GmbH/IHP-Open-PDK/blob/5e6d592e4002946a4616f798c357f0f3c06cf3b6/ihp-sg13g2/libs.tech/klayout/tech/drc/rule_decks/feol/7_2_latchup.drc) requires every relevant N+ active portion to be within 20µm of a PWell tie. A single central contact leaves portions of a 64µm stripe uncovered. The physical v3 candidate places two contacts at 16µm and 48µm along each long tail stripe and retains one central contact on the 8µm reference stripe. This gives five additional contacts, 32 total contacts and 59 physical devices. The transistor and resistor circuit is unchanged.

[XOR59 physical run](https://github.com/Melihakbulut221/nssoc/actions/runs/39115862679), source `a9ddef55b4ba2058d6a13f5440dc31d063fb5861`, was live at this record's creation. It must pass all 560 native DRC categories, unsimplified deep/flat 59-device LVS, exact public ports and seven actual faults (HBT size, missing HBT, MOS width, MOS gate, output open, rail short, off-grid). No physical pass is inferred here. The geometry's crossed-input and output mapping is independently checked against the exact wrapper used by the native component simulation.

## Integration requirements

The 54-device ideal component model must not stand in for the new 59-device geometry. Fresh extraction must include all 32 finite contacts, every native MOS terminal and diffusion geometry, and the actual conductor R/C network. Existing 406-device native identifiers and old XOR RC are invalid for the replacement.

Replacing both old select16 leaves by select18 and both old XOR54 leaves by XOR59 gives an expected 420-device physical parent: 100 HBT, 22 MOS, 102 rppd, 11 MIM and 185 substrate contacts. This is an accounting expectation, not a verified parent layout. Integration must update actual source pin order and physical layer assignments, regenerate routes and supply reinforcement, independently compare the circuit, run native DRC/LVS and extract fresh MIM-aware RC before the original full loaded data/phase/current gates are evaluated.

The existing retimed-input attenuation, PLL/CDR loop behavior, complete serial PHY, four-lane/main-chip integration and final setup/hold remain open. For the currently active exact cloud handles, read [CLOUD_RESUME.md](../CLOUD_RESUME.md).
