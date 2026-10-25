# Actual sampler timing diagnosis after collector-access repair

Run39324658022 atd2939dfa58f9f480285df10c71876078118bbcd2 passed the diagnostic replay for both rejected nominal captures. All116original HBT checks and all4sampler sample/margin/clock-to-valid checks reproduce exactly. All physical parallel selector base combinations are retained, with no averaged representative.

## Wrong output signs at the original sample phases

| Case/stage | 0.3UI | 0.6UI | 0.9UI |
| --- | ---: | ---: | ---: |
| Early A |69|0|0|
| Early B |129|0|0|
| Early C |126|30|30|
| Early D |129|105|105|
| Late A |89|0|0|
| Late B |0|0|0|
| Late C |126|32|30|
| Late D |127|94|98|

Late B still has128samples below100mV at0.3UI. Its zero wrong-sign count is not a timing/margin pass. The0.3UI limit remains37.5ps at125ps/UI.

The actual parallel clock base pairs each contain258observed rising crossings in the active window. Their nearest-external-rising-edge median differences span approximately4.4–9.4ps across the four physical samplers. These are observed nearest-edge statistics, not ordinal-lock, jitter qualification or a causal timing correction. Each pair retains its full crossing list and physical device/terminal identities in the evidence.

A/B fail the early sample and pass their later sample phases. C/D retain wrong expected data at0.9UI; their problem cannot be classified merely as an early output threshold miss. No sampling window is shifted and no later phase replaces the original gate.

Next inspect the actual native master/slave graph and input-transfer path: distinguish the physical data and hold pairs, measure native clock-steering currents, master input/output and slave input/output at the original capture edges. Use these observations to choose a real data-path or latch repair; do not infer a passing repair from a clock delay statistic. Existing native waves contain every necessary HBT terminal/current vector and remain archived unchanged.

Both nominal complete CDR runs remain rejected. The collector-access change passed nominal device headroom, but full CDR/PLL, serial PHY and mainchip timing are unaccepted. TX39308903140 and mainchip39293720171 are independent long jobs. All work and artifacts remain in the cloud.
