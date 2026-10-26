# CDR v59: ten complete native case results

Eight normal loaded cases are rejected. The two intentional faults are detected, which is a control result and does not qualify CDR operation. All ten cases retain `accepted=false`, `cdr_accepted=false`, `closed_loop=false` and `full_phy_accepted=false`.

This comparison authenticates all ten full native JSON assets (26,758,739 bytes) from [run 40219397958](https://github.com/Melihakbulut221/nssoc/actions/runs/40219397958), source `92a8253dd3410dd33bf34c1f7225991cf588d85d`. Exact asset IDs, URLs, byte sizes, SHA256 values, full failing-device metrics and data-screen aggregates are in [the evidence JSON](evidence/cdr-v59-ten-case-native-json-comparison-20261026.json). No archive or waveform was read and no analysis or simulation rerun.

| Case | Failed HBTs | Devices | Data | Phase average (mV) | VI current (µA) | VI output (mV) | VI |
|---|---:|---|---|---:|---:|---:|---|
| nominal_early | 4 | FAIL | FAIL | -11.009985 | -34.093506 | -11.457410 | FAIL |
| nominal_late | 4 | FAIL | FAIL | 14.071645 | 42.877557 | 12.137489 | FAIL |
| hot_early | 8 | FAIL | FAIL | -8.294017 | -21.652644 | -7.806626 | FAIL |
| hot_late | 8 | FAIL | FAIL | 9.242502 | 24.040806 | 7.275682 | FAIL |
| cold_early | 8 | FAIL | FAIL | -13.251884 | -45.835579 | -14.320516 | FAIL |
| cold_late | 8 | FAIL | FAIL | 18.759182 | 63.375412 | 16.768789 | PASS |
| constant_zero | 0 | PASS | FAIL | -0.744542 | -1.041262 | -3.361181 | FAIL |
| constant_one | 0 | PASS | PASS | -0.823473 | -0.996248 | -3.823024 | FAIL |
| clock_stopped | 0 | PASS | FAIL | -0.827154 | -0.982229 | -3.828822 | FAIL |
| vi_bias_off | 5 | FAIL | FAIL | 14.097001 | 0.136644 | -0.057700 | FAIL |

Phase and VI columns above retain the physical signed measurements. Early cases require the negative direction and late cases the positive direction. The six varying-data cases require a direction-adjusted phase average ≥30 mV and VI current ≥50 µA plus output ≥5 mV. Constants require |phase|≤10 mV, |VI current|≤5 µA and |VI output|≤2 mV. VI tails must remain ≥100 µA.

The six varying-data cases all miss the 30 mV phase gate. Only cold_late passes the VI gate. Both constants pass device safety and the constant phase gate; constant_one also passes the complete data screen but fails VI voltage neutrality at −3.823 mV. Constant_zero fails VI neutrality at −3.361 mV and separately has six below-100 mV samples in each comparator: minima 95.244/94.916 mV, with reported maximum clock-to-valid 118.906 ps versus the original 75 ps comparator limit.

| Case group | Active VCE minima below 0.4 V | Other HBT failure |
|---|---|---|
| Nominal early/late | XD61/62/115/116; worst 0.340550 V at XD61 in nominal_late | None |
| Hot early/late | XD61/62/71/72/87/88/115/116; worst 0.317404 V at XD61 in hot_late | None |
| Cold early/late | XD61/62/115/116; worst 0.355453 V at XD61 in cold_late | XD59/60/111/112 all-time absolute VCE maxima 1.663763–1.675586 V exceed 1.6 V |
| Constant zero/one | None | None |
| Clock stopped (intentional) | None | Detected through data/VI failure only |
| VI bias off (intentional) | XD61/62/115/116/170; XD170 minimum 0.290687 V | VI tail currents also miss the bias gate |

The original HBT screen requires active VCE≥0.4 V after 2 ns, all-time |VCE|≤1.6 V, all-time |VBE|≤1 V and all-time |Ic| per emitter <3 mA. The cold overvoltage maxima above are all-time measurements; these JSON extrema do not establish whether those peaks occurred after startup. No HBT VBE/current limit fails in these results. All 50 MOS terminal checks and seven native capacitor checks pass in all ten cases.

All ten captures report 1152 columns from 0 to 34.25 ns, with a requested maximum step of 0.3125 ps. Every run reports engine return code 0, no numerical diagnostics, 124 verified OFF flags, zero-source OP maximum 0 and all 5549 saved input hashes unchanged. The original KLU/TRAPEZOIDAL runtime and numerical tolerances are retained. Job start/end timestamps are preserved as job timing only; native engine elapsed time is not separately reported.

The original sampling screen uses 100 mV signed margins, sampler phases 0.3/0.6/0.9 UI with a 37.5 ps validity limit, and comparator phases 0.6/0.75/0.9 UI with a 75 ps limit. No phase fit or threshold relaxation is applied. Intentional-fault status uses the original `fault and not(data_ok and vi_ok)` predicate; its PASS must not be read as electrical safety or functional acceptance.

The repeated dynamic headroom failures, cold all-time overvoltage, phase deficiency and constant-input VI offset are distinct measured problems. Separate extrema do not prove a simultaneous-row mechanism or justify changing a particular device by themselves. The existing same-row nominal diagnosis supplies the next evidence needed for a bounded circuit correction.
