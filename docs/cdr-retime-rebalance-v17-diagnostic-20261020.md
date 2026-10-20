# CDR retime divider experiment v17

This is a circuit sensitivity experiment on the frozen v16 metal network.
It is **not** a new extracted layout, accepted CDR, recovered-clock loop or
completed PHY. Any favorable result requires new native device geometry,
DRC/LVS, fresh complete extraction and another unchanged loaded screen.

## Evidence and hypothesis

The v16 early/late full-wave runs rejected the original sampling gates.
The native passive-network report 39341051275 identifies the actual C/D
filter and sampler resistors from geometry, terminal identities and circuit
connectivity. It preserves the prior failures and identifies substantial
collector-wire loading; no scalar RC approximation was used as a timing pass.

The proposed change addresses the two consecutive C/D input dividers.
For both polarities of C and D only:

| Native role | Old length | Candidate length | Width |
| --- | --- | --- | --- |
| retime series | 5.4 um | 1.8 um | 4 um |
| retime shunt | 12.6 um | 16.2 um | 4 um |
| sampler input bias | 2.4 um | 6 um | 4 um |

There are exactly 12 intrinsic changes. The filter series-plus-shunt drawn
length remains 18 um; this is not a claim of unchanged effective resistance,
current or common mode. The native nonlinear resistor/HBT models determine
those quantities. A/B input dividers, all MIM/HBT/MOS parameters, node
connectivity and all 17674 metal resistors / 12709 metal capacitors remain
exactly the original values. No R/C scaling, ideal bypass, different expected
bits, phase shift or relaxed acceptance threshold is permitted.

The larger candidate intrinsic dimensions are not represented in the old
metal extraction. Candidate reports and contracts explicitly mark that
geometry mismatch and keep adoption/physical/PHY acceptance false.

## Validation and decision

The original source-bound physical composition and binding controls run first.
The sensitivity helper selects devices using the SHA-pinned native-chain
receipt, checks each terminal against the 484-device contract, creates a
separate candidate SPICE/contract and reparses it. Five actual corruptions
must be rejected: a missed requested length, an unrelated-device change,
scaled metal R, wrong intrinsic terminal and wrong contract length.

The full 34.25 ns, 256-bit, original fixed-phase/load/current/device screen
then runs for nominal early/late plus clock-stopped and VI-bias-off controls.
All waveforms and failures remain cloud artifacts. A passing diagnostic
only justifies building and verifying the real candidate geometry; it does
not close CDR, PVT, PLL or PHY requirements. A rejection is evidence for
revising or discarding this circuit hypothesis, never a reason to relax gates.
