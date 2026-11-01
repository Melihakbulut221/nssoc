# Current Via2/Metal3 loaded result — 2026-11-01

The physical candidate remains electrically rejected. [Actual run 41260582673](https://github.com/Melihakbulut221/nssoc/actions/runs/41260582673) completed its engine with return code 0 in 752.622 seconds. Native card validation, 124 native flags and all 1,151 saved vectors passed; the complete 113,475-row waveform has no decimation. There were no engine diagnostics or cleanup errors.

The original electrical gate then rejected the loaded circuit. The host's generic nonzero measurement-wrapper message is secondary to the preserved `REJECTED_WHOLE_MIM_PD500_LOADED` report. It must not be reported as an engine failure.

| Measurement | Current | Required |
|---|---:|---:|
| Signed phase output | 13.980168 mV | At least 30 mV |
| VI signed current | 42.611702 µA | At least 50 µA |
| T061 minimum active VCE | 0.340701606 V | At least 0.4 V |
| T062 minimum active VCE | 0.341918683 V | At least 0.4 V |
| T115 minimum active VCE | 0.376243907 V | At least 0.4 V |
| T116 minimum active VCE | 0.377444580 V | At least 0.4 V |

[Cloud comparison 41262469361](https://github.com/Melihakbulut221/nssoc/actions/runs/41262469361) passed five controls and compared the exact matching `nominal_late` baseline, run 41218657461. It verifies the same original conditions and retains all 124 HBT checks, four samplers, two XOR stages and every per-bit delay. Sampler C/D wrong-sign counts fell from 27/56 to 25/54; XOR X/Y stayed at 385/44. Phase output and VI current decreased slightly. Overall data, phase and device acceptance remain false.

The [631-file terminal proof](https://github.com/Melihakbulut221/nssoc/tree/53e39a2c43bfef518793da536a6bc423398d7262/docs/evidence/cdr-via2-m3-loaded-terminal-41260582673) and [15-file comparison proof](https://github.com/Melihakbulut221/nssoc/tree/085fe53ff8bc8e603385ffb4a8fb18ed1b9e4688/docs/evidence/cdr-via2-m3-loaded-comparison-41262469361) are imported under `docs/evidence`. Complete native outputs remain in release 430292142 and its artifact; all four archive parts uploaded successfully. The original `wave.raw` is 1,045,823,299 bytes with SHA-256 `13a98da362a15642de4e6742a9b8d73e2c68894795dc0caad6c542e5eb655612`.

Next work uses that existing waveform in the cloud to locate Vc/Vb/Ve/Ic and clock/data conditions at the four failures, and to correlate sampler/XOR errors. It must reproduce the original active mask and recorded gates before diagnosing a new analog change. The existing result does not justify an identical simulation rerun, altered stimulus or relaxed gate. Closed-loop CDR and full PHY acceptance remain open. All simulations and numerical analysis remain on GitHub.
