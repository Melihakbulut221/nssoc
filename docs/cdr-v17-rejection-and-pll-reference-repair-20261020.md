# CDR v17 rejection and PLL reference progress

The CDR divider-rebalance experiment is rejected and is not selected for
physical layout. Native early/late simulations both completed with no solver
diagnostics and passed device limits, but failed original sampling gates.
Both C/D outputs became worse on wrong-sign and below-100-mV counts:

| Case | Sampler | v16 wrong sign | v17 wrong sign | v16 below 100 mV | v17 below 100 mV |
| --- | --- | ---: | ---: | ---: | ---: |
| nominal_early | A | 77 | 73 | 129 | 129 |
| nominal_early | B | 129 | 129 | 129 | 129 |
| nominal_early | C | 189 | 218 | 206 | 230 |
| nominal_early | D | 339 | 365 | 345 | 379 |
| nominal_late | A | 97 | 85 | 129 | 129 |
| nominal_late | B | 0 | 0 | 128 | 128 |
| nominal_late | C | 188 | 224 | 210 | 234 |
| nominal_late | D | 310 | 349 | 330 | 360 |

The stopped-clock and disabled-V/I-bias controls were detected. All four
complete reports and release hashes are retained in docs/evidence. The
frozen-metal circuit experiment does not become a physical candidate simply
because device stress limits passed. Retain the actual v16 layout and use
the failed experiment to focus the next repair on loading and latch timing.

The first whole-PLL reference job 39347411640 stopped before terminal binding
at the exact 102-HBT hierarchy census. Native flat LVS still contains 102
HBTs; the initial hierarchy selector required an unprefixed cell name.
The revised selector permits parent namespace prefixes before the pinned
npn13G2 name, while retaining the exact 102-instance count, unique native
enclosure, per-terminal pin and conductor ownership checks. It also writes
the actual hierarchy census before asserting so further mismatches are
reviewable. This changes no geometry, reference-plane gate or acceptance
threshold. The failed report is retained and a new native cloud run is required.

TX loaded waves and main-chip routing remain separate live jobs. No full
serial PHY, final timing or qualified PEX completion is claimed.
