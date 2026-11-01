# PD650 data-buffer lag localized from complete native rows

The original circuit remains **electrically rejected**. Analysis success means the
failed measurements were reproduced and their location narrowed; it is not a PHY pass.

Producer: run41288195752/source d638e0e3cd15a0ee930212c27ab1f238b5085237,
release430445706. Raw SHA256 4d0227e3cdf45a1e670059882c513b11d254c5d142c5d50bf295e5ddfe2b861f.
The cloud reader authenticated every archive member, all1301 vectors and113475
unmodified rows. It uses the original pinned binary parser and reproduces every
original sampling count, signed margin, per-bit clock-to-valid and phase average.

Full-wave reproduction run41293861314/source46319d4691e2b06a193ebf47984b40256800fa41:
29 controls passed; complete22-file proof198ac19f2ffb0a2d853936ee31f7951c06d673b5,
`docs/evidence/pd650-wave-analysis-41293861314`.

Physical-node path analysis run41294574040/sourceabd8ec54a53e615dd9384a287f6690fd9130440f:
29 controls passed; complete23-file proof5d32ba3ace05084b64cc1c1766c8ff19fa84908d,
`docs/evidence/pd650-wave-analysis-41294574040`.

## Findings

A/B failures occur on transitions; A reaches100mV as late as42.656ps and B37.969ps
against the unchanged37.5ps requirement. C/D have later transitions and some late
margin collapse. Their118.906ps worst measurements include samples still below
100mV at the end of the original0.95UI window; this is not evidence that a clean
transition occurs at118.906ps.

X's positive active swing peaks at75.144mV, below the100mV requirement. Y's positive
peak is18.937mV. The phase average remains19.616mV against the original30mV gate.
All original transistor voltage/current gates pass in this one nominal run.

At0.9UI after the original rising edge, the following downstream wrong-sign cases
occur **even when their source sampler already has at least100mV signed margin**:

| Physical path | Source-valid samples | Downstream wrong-sign samples |
|---|---:|---:|
| A divider bases |255|0|
| A buffer collectors ADP/ADN |255|77|
| C divider bases |216|27|
| C buffer collectors CDP/CDN |216|43|
| D divider at X selector bases |254|69|
| D divider at Y selector bases |254|69|
| D buffer collectors S0P/S0N |254|89|
| D buffer collectors S1P/S1N |254|89|

At0.6UI all255 A/C/D source samples exceed100mV, but A/C buffer outputs have101/96
wrong-sign samples and both D buffers112. These are separately labelled diagnostic
counts; none replaces the original six sampling gates.

The physical device graph confirms R234-237 feed USP/USN from **retimed DQP/DQN**,
not raw B. Do not apply a speculative B-to-D rewire. A/C data paths use R227-230
and R238-241. The diagnostic binds the actual bases of Q123/Q125, Q128/Q130,
Q131/Q132 and Q149/Q150, plus their actual collector aliases, against native
composition/plane identities. No ideal interconnect aliases or reconstructed
Boolean outputs are inserted.

## Next circuit experiment

A bounded hypothesis is to halve both resistor-divider legs, preserving nominal
ratios: A/C1.8/10.8um becomes0.9/5.4um; D6/8.6um becomes3/4.3um, all widths1um.
The exact12 resistor IDs are recorded in the v232 checkpoint proposal.
This candidate is **not yet generated or simulated**. Preserve the complete old
model SHA and reverse-verify every changed token/descriptor; keep all200 MOS
units, all other model/RC bytes, original stimulus and every electrical gate.
Lower impedance can change loading/headroom, so an actual full simulation must
accept or reject the candidate. No successful outcome is assumed. Full updated
geometry/DRC/LVS/freshRC/PVT and closed-loop/serial integration still follow.

## Retained reader failures and cloud operation

Initial4516b4ce.../41293342915 was cancelled during checkout after inspection
found omitted cloud-sampler-load/ archive-prefix handling. Full13-file proof
71e233ec0651b3062bcd0aaf69a1c5b870f1fc48 is retained.
Sourcef015f8bb.../41293436380 authenticated the full archive then stopped because
the reader expected a diagnostic count instead of the actual empty list. Its
full17-file proof1777bacdebf3e371acd5a8ac0b485267f2b4cce3 is retained. The final
reader accepts only the actual empty list and rejects nonempty/mistyped values.

Only derived text/JSON is read by the coordinator; native archives, models and
raw waveforms remain on GitHub. Source/electrical/physical execution remains
cloud-only. Proof branches now point directly at their final [skip ci] commit,
avoiding redundant same-source general CI at temporary base refs. Three duplicate
proof-branch CI runs were cancelled; original same-source CI attempts are retained.
Their cancellation is not represented as a test pass.
