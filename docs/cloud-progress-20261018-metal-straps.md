# Current cloud continuation — isolated TX passes physical checks; full waves running

All work remains CLOUD ONLY. Local task workspace stays empty. No local CAD,
checkout, test, PDK, archive or waveform. Source mutations use GitHub Git Data
API with non-forced HEAD checking; verification runs on GitHub-hosted runners.
The existing eight-hour monitor is already active and cloud-only. Prior local
instructions are superseded. Do not cancel or duplicate healthy live jobs.
Full serial Gen3x4 PHY, mainchip integration/signoff and final timing are OPEN.

## Exact current native jobs

* **39158584151**, source dd36669f1fad978cc5c26b4fa81210231511749e:
  `tx-v5-fast-stage-isolated-loaded-wave-cloud.yml`. Original34ns/256bit full32
  wire-mode nominal and swap_leaf_select negative control.604HBT/512MOS bounds,
  124input legs/372data bases,11actual clock reference macros, unchanged solver,
  sampling phases and bit oracle. External modulation, schematic CMOS/output
  frontends and ideal intermacro boundaries remain: not a full recovered-clock
  four-lane PHY. Inspect actual electrical gates, not job color alone.
* **39158947092**, source807c0c1e2b96da47c3567834247d81ff32616238:
  `onehot-resize-prepare-cloud.yml`, job117767945479. New mainchip sizing trial
  from exact routed ODB9fd2de4914a736dc666da66b866bbd1b1ae07547183044aa033628bc620bbe77.
  Select existing small positive data buffers on original negative slow paths
  with cap>=.1pF,stage delay>=1ns; at most50. Size to buf8/buf16 instead of
  adding buffer stages. Preserve every net, all other instances, PG/NDR/ports,
  original clock budgets and derate. Check native legalization/geometry,
  actual Liberty equations and an inverted-driver negative control. Old signal
  routes are deliberately invalidated; fresh routing/RC/all-corner STA is
  mandatory after a preparation pass. Original provenance dependencies must
  be restored before PNR. Do not call this timing closure.

## TX physical short repaired and verified

Failed fast-stage39154915645 retained. Hosted native review39156102268 found
four overlapping TM1 pairs: p8_0p/p8_2p, p8_0n/p8_2n, p8_5p/p8_7p, p8_5n/p8_7n.
Only p8_2p/n moved48um outward and p8_7p/n24um, onto two disjoint-span channels.
Six candidate rows, original cells/circuit/clocks remain. Candidate physical
**39156383821** at4d9516cc5f2ce25ed4123be9426aef6912ff4988 PASSED:
560category DRC0; unsimplified deep and flat1674-device LVS; original five
physical fault controls;31actual unchanged macros/60signal connections and
three independent primitive/placement corruption controls. Additional checker
verifies actual TM1 trunk coverage and no pairwise parent trunk overlap.

Fresh RC **39156812497**, source447f39e25ab13d5d7f01ecf386ebdb80ee4f494e:
1674devices,4774terminals,3262anchors,377wire conductors;116611R77514C.
All original graph, ownership, point/mutual capacitance conservation and13raw
corruption controls passed. Body spreading/RF extraction remains unqualified.
Composition **39157450167**, sourceaa94559c5be215eae142e4146d3fde6c35e6994d,
passed six model faults, actual terminal ownership/topology and two native
endpoint faults. Compact model SHAfded70a92169805d5de9bca52cf7827699fb9c85919d33b0059320410eea2545;
wire SHA5ba39517abf8f1d0d85bdb36501d6ddd5ab6c52b4fcb54d1af2fd0ee927f3509.

Compact comparison39158131527 failed on instance spelling after physical-ID
mapping, not an LVS/device discrepancy; failure is retained. Corrected proof
**39158386855**, sourcea2183aace50249c0d4a9d93375f081b66608248b, passed all1674
ordered device cards and fixed162public nodes using actual primitive model/local
nanometer bbox within each named macro. Original3faults plus physical identity
swap were rejected. New wave builder permits only the two new model hashes;
exact-delta guards retain original stimulus/solver/review/clock controls.

Receipts: `tx-v5-fast-stage-isolated-physical-pass-20261018.json`,
`tx-v5-fast-stage-isolated-extraction-pass-20261018.json`,
`tx-v5-fast-stage-isolated-composition-pass-20261018.json`,
`tx-v5-fast-stage-model-equivalence-pass-20261018.json` in docs/evidence.
Original return-repair39137607059 is terminal: nominal rejected, negative
swap_leaf_select succeeded in detecting the fault. Do not keep polling it.

## CDR diagnosis completed, still electrically rejected

Strapped-v6 loaded39154395989 remains rejected. Native path review39157108993
at8f518fac34e6f48ab061442c9ab4d160940fd6a9 reproduced every original sampler
count and116HBT minimum from preserved captures. Early wrong counts187/305/378/389,
45HBT failures; late305/130/376/396,47HBT failures. WorstVCE~.29126/.28751V.
Measured bqp load supply wire drop~.2257V and load-to-collector~.098-.099V
remain; the intrinsic load drop is~.0689V. These are separate actual waveform
measurements, not inferred DC drops. Native cp/cn incident wire capacitance is
~1.723/1.642pF. The straps did not close the circuit. Next physical repair must
address actual shared supply/local escape/signal wiring, with fresh native
physical/RC/full loaded checks. Preserve2.12um intrinsic loads and original
acceptance gates. Receipt `cdr-strapped-v6-load-wire-drop-20261018.json`.

## Mainchip fresh routed evidence and next steps

Completed route39149110568 remains DRC0/disconnected0 but antenna2 and timing
FAIL. Slow/typ/fast setup9673/7647/3811, hold8/11/27; setupWNS about
-19.586/-6.817/-3.288ns. Actual worst slow path includes high-load weak Ibex
buffers; fast setup includes replay_read_onehot buffer chain; worst hold starts
pcie_rx_valid_i. Read `onehot-resumed-path-review-20261018.json` for full first
paths/source hashes. Remaining antenna nets are Ibex rf_reg_q[2] in register14
and u_pcie.receive_ownership.packets[46][4], cumulative ratios385.44/247.47
against200. Original propagated20/4/8/8ns clocks,5percent derate,20SRAM remain.
After the new sizing preparation proof, route the candidate and remeasure all
three corners, antenna, DRC and connectivity. Keep failures/regressions visible.

This continuation made concrete physical/model progress. No external blocker
is established. No complete-goal or production-acceptance claim is justified.

Last authoritative run snapshot:
```json
{
  "39158584151": {
    "status": "in_progress",
    "conclusion": null,
    "source_head": "dd36669f1fad978cc5c26b4fa81210231511749e",
    "jobs": [
      {
        "id": 117766870186,
        "name": "controls",
        "status": "completed",
        "conclusion": "success"
      },
      {
        "id": 117766953321,
        "name": "native-full32 (wire, nominal, swap_leaf_select)",
        "status": "in_progress",
        "conclusion": null
      },
      {
        "id": 117766953332,
        "name": "native-full32 (wire, nominal, none)",
        "status": "in_progress",
        "conclusion": null
      }
    ]
  },
  "39158947092": {
    "status": "completed",
    "conclusion": "failure",
    "source_head": "807c0c1e2b96da47c3567834247d81ff32616238",
    "jobs": [
      {
        "id": 117767945479,
        "name": "native-physical",
        "status": "completed",
        "conclusion": "failure"
      }
    ]
  }
}
```
Observed UTC: 2026-10-18T19:32:05.678112+00:00
