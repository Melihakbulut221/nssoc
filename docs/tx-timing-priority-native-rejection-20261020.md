# Timing-priority TX layout: original fullwave rejected

Run 39308903140, source 2ee3e11f6d0644e1751a407d8342b3197fcb2d25,
completed native simulation with exit zero and no solver diagnostics. It ran
12073.0146 seconds and retained the complete 77567-row, 3004-column waveform.
Native source/model hashes remained unchanged. This is an electrical rejection,
not a simulator crash or evidence of PHY acceptance.

The actual 1674-device model includes 116611 resistors and 77538 capacitors.
At the original 0.3/0.5/0.7 UI phases and unchanged 100 mV signal threshold,
120 of 768 samples have incorrect polarity; 144 are below threshold.
The phase counts are respectively 56/39/25 incorrect and 68/46/30 below threshold.
The minimum signed margin is -0.28733318 V.

All 512 MOS screens passed. Twenty-four of 604 HBTs failed; the minimum
post-start VCE is 0.35618420 V, below the original 0.4 V limit.
CMOS interfaces and level16 passed. Level8 has no sign errors but 171 samples
below its original 150 mV interface gate. Level4 has 252 sign errors and
2763 below-threshold samples; the final interface has 837 and 2188.

The shorter final data routes does not establish timing closure. The next
cloud path review restores this exact original waveform and must reproduce
every original gate before reporting stage-specific data margins, actual
failed HBT terminal voltages, and native resistor-connected clock bases.
Only the new geometry's capacitor count, source paths and receipt are adapted;
no sampling phase, expected bit, threshold or device limit is changed.

Full failure evidence is retained in the GitHub release and pinned receipt.
No native waveform, checkout or CAD output is stored locally.
