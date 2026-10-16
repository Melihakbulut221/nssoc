# Driver wire sensitivity and actual HBT headroom

Full original34ns/256bit/8GT/s localpins sensitivity run38924911243 completed
both diagnostic simulations. The original sources, three sample phases,
672MOS/62HBT limits and downstream extracted162-device tree were retained.
Neither case is physically realized or accepted.

| Case | Output minimum | CMOS minimum | Final minimum | Failed HBTs | Failed MOS |
| --- | ---: | ---: | ---: | ---: | ---: |
| Actual localpins wires |161.702mV|167.974mV|130.597mV|12|0|
| Half260wire resistances |206.174mV|181.549mV|151.513mV|10|0|
| Half295wire capacitances |240.748mV|255.748mV|213.934mV|8|0|
| Prior intrinsic driver control |241.974mV|270.999mV|215.897mV|0|0|

The original100/150mV signal limits pass in both sensitivity cases, but the
unchanged minimum0.4V HBT collector-emitter requirement fails. For example,
actual xd0125 minimum VCE is0.337218V, half-R0.348693V, half-C0.325687V;
the intrinsic control is0.422551V. Reducing capacitance substantially improves
the sampled signal margin while worsening this device's worst headroom.
It is therefore insufficient to optimize only the output eye or static resistance.

Read-only cloud workflow tx-driver-headroom-cloud restores each full original
waveform and contract from hash-bound archives, independently replays every
published engineering field exactly, and records actual worst native sample
times and C/B/E voltages for all62HBTs. It preserves actual physical-tree
binding01.json, all contiguous below-limit native sample runs, simultaneous
data/clock/rail values and original failure verdicts. A missing real current
probe must be rejected. No phase fitting, waveform trimming, relaxed device
limit, changed stimulus or rerun is used to obtain a better verdict.

These measurements must guide a real layout/bias change, followed by fresh
DRC/LVS/RC and the original full loaded/PVT checks. They cannot stand in for
a realizable layout, full32:1/four-lane SERDES, PLL/CDR or mainchip signoff.
