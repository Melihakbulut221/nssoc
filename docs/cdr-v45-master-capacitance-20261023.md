# CDR master capacitance and regeneration experiment

The four v44 load trials were rejected. The3.9um collector loads reduced early
C/D wrong-sign samples to0/2, but C/D still missed the original37.5ps deadline
(45.781ps each), and the signed phase mean remained approximately15mV against
the unchanged30mV gate. A also remained below its original100mV gate.

Further resistor enlargement consumes the measured hold-transistor headroom:
the minimum is approximately0.476V, only76mV above the original0.4V gate.
This experiment therefore keeps every v44l39 resistor and bias unchanged.

Two finite candidates reduce master device capacitance: C/D data HBT Nx4->3,
or C/D data plus hold HBT Nx4->3. These alter four or eight actual native devices.
We/Le, selectors, followers, A/B, slave stages and topology remain unchanged.
Both measured parent phases are pinned by asset SHA256. Their actual current
peaks, divided by the proposed three emitters, remain below the original3mA
limit. This arithmetic is only a screening justification: changed native
current, VBE, VCE, timing and phase must pass the full original native gates.

The graph controls reject missing/wrong devices, invalid geometry/identity,
wrong output binding and duplicate hold identities. Original source/parameter/
fault controls remain. All476devices, all1104columns, original256bits/34.25ns,
8GHz/10ohm external clock sources,150fF sampler loads and50fF XOR loads remain.
No ideal internal data or clock is inserted; no sample window or gate shifts.

Candidate geometry/fresh RC and full closed-loop/PVT/RF/PHY acceptance remain
open. A control pass or an improvement in C/D is not full-CDR acceptance.


## Completed full native results: both recipes rejected

Run39961095437 finished all four full113475-row/1104-column/34.25ns captures.
All native simulations exited0, sources were unchanged and original all-device
checks passed. All four failed the unchanged data and signed30mV phase gates.

Every C/D maximum clock-to-valid delay worsened relative to the matching
v44l39 phase. Reducing only master data area worsened C by0.938/0.625ps and D
by0.313/0.313ps (early/late). Reducing data and hold area worsened C by2.188/
1.875ps and D by1.250/0.938ps. The predicted capacitance reduction did not improve
the actual loaded circuit. Neither recipe is promoted or substituted for v44.

The next circuit work must address measured gain, bias/common-mode and
regeneration together. Further collector resistance consumes the approximately
76mV hold-device headroom; the parent C master track selectors have only about
19mV above the original0.4V VCE gate, so changing the input-divider gain alone
also requires a real bias/headroom analysis. No clock/source/load/gate
relaxation or further blind area reduction is justified by these results.

Exact summaries, native model/raw hashes and manifest digests:
docs/evidence/cdr-v45-master-capacitance-results-20261023.json.
