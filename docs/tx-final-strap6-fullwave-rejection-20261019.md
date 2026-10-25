# Final local strap6 full native waveform rejection — 2026-10-19

[Nominal job117956363557](https://github.com/Melihakbulut221/nssoc/actions/runs/39221063981)
completed the native34ns/256-bit simulation in14866.64s, returncode0.
Source hashes remain unchanged,604 native HBT OFF flags were read back,
diagnostics are empty. The complete77557-row,3004-vector raw capture is
preserved in immutable cloud parts. This was an electrical rejection,
not a timeout or successful PHY result.

Original unchanged output gates:140/768 wrong-sign samples,
164/768 below100mV; minimum signed margin−0.28766222V.
At the original interface sampling points:

| Interface | Wrong sign | Below150mV | Minimum margin V | Result |
|---|---:|---:|---:|---|
| CMOS | 0 | 0 | 0.276936 | PASS |
| level16 | 0 | 0 | 0.274248 | PASS |
| level8 | 0 | 1044 | 0.077494 | FAIL |
| level4 | 450 | 2547 | −0.146765 | FAIL |
| final | 1152 | 2207 | −0.313307 | FAIL |

Each interface table row covers6912 samples.24HBT device checks failed;
all512MOS checks passed. All original signal/interface/device/diagnostic
limits remain unchanged. The physical strap4→6um change and its static
resistance improvement are insufficient to close loaded behavior.

The corresponding swap-leaf fault job117956363421 and both trunk256
full native jobs in39226121734 remain active at latest check; do not
cancel or restart healthy simulations. Inspect the trunk256 result before
choosing another final-rail geometry. Intermediate level8/level4 failures
must also be resolved using actual interface and device evidence.

Full serialPHY, recovered-clock operation, RF/substrate qualification and
mainchip setup/hold remain open. No waveform phase fitting, shortened
trajectory or relaxed device limit was used.
