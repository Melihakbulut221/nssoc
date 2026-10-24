# Physical TX group2/3/4 clock change: nominal full-wave result

Run [39372036289](https://github.com/Melihakbulut221/nssoc/actions/runs/39372036289),
nominal no-fault job 118461938478, completed the original 34 ns waveform with
native return code zero and no solver diagnostic. It is **electrically rejected**.

The simulation retains the complete 1674-device, 116611R/77538C TX core,
eleven actual clock macros, all 604 HBT and 512 MOS device checks, 256 source bits
and unchanged 0.3/0.5/0.7 UI sampling. The raw capture has 77,574 rows and
3,004 columns; every original row is preserved in the cloud archive.

The 18 previously failing selectors in clock groups2/3/4 now pass the original
device checks. Six HBT failures remain: final selectors xd0109–xd0112 and
tails xd0114/xd0115. Minimum active VCE is 0.35646 V for the worst selector and
0.37999 V for the worst tail against the unchanged 0.4 V gate.
All 512 MOS checks pass. This does not establish PVT or full-PHY safety.

| Original signal gate | Result |
| --- | --- |
| Wrong-sign output samples | 83 / 768 |
| Output samples below100mV | 104 / 768 |
| Worst signed output margin | -0.28655 V |
| CMOS input interface | Pass |
| Level16 interface | Pass |
| Level8 interface | 45 samples below150mV |
| Level4 interface | 153 wrong-sign;2268 below150mV |
| Final input interface | 567 wrong-sign;1768 below150mV |

Each aggregated interface result covers6912 samples. These stage-interface
counts must not be confused with the768 final output samples. Reducing device
headroom failures has not fixed the bit errors.

The existing live comparison39376417214 includes the separately verified
physical final differential clock bridge. It must finish without being
restarted. Success is not inferred from the group2/3/4 improvement.

A new cloud read-only path review replays this exact complete capture and
requires byte-for-byte equivalent original review results before examining
actual terminal margins and the six remaining HBT voltages. It neither
resimulates nor changes source bits, sampling phase, latency or thresholds.
The pinned receipt preserves the failed result and complete archive manifest.
