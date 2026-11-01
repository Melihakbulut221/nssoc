# Coupled sampler load/headroom: actual result

The actual native run [41272254964](https://github.com/Melihakbulut221/nssoc/actions/runs/41272254964), source `8a07e8f773d931f9cb7f4ac72e5520b68bb133be`, completed its simulation normally (return code 0, 863.308 seconds). The original electrical screen **rejected** this candidate. This is a circuit experiment using baseline wire RC; it is not a regenerated or accepted physical implementation.

Eight sampler collector pullups changed from L2.6 to L1.5 um at W32 um; four shunts from L5 to L7.4 um at W4 um. All other intrinsic device and wire RC fields remain unchanged. The source controls passed 13 circuit mutation and 5 archive rejection cases. No original gate, stimulus, load or measurement code was relaxed.

The independently pinned full comparison [41273897568](https://github.com/Melihakbulut221/nssoc/actions/runs/41273897568), source `7c0c9766544dfe673421c42a48b18b600c565323`, repeated 10 corruption controls and checked all 124 HBT devices and all 1530 per-bit delays. It succeeded as an evidence comparison, not as a PHY qualification.

| Stage | Baseline maximum delay ps | Candidate maximum delay ps | Candidate minimum signed margin mV | Candidate original gate |
|---|---:|---:|---:|---|
| A | 46.094 | 41.406 | 65.515 | fail |
| B | 41.719 | 37.031 | 105.732 | pass |
| C | 118.906 | 118.906 | 38.454 | fail |
| D | 57.031 | 49.219 | 28.381 | fail |
| X | 118.906 | 118.906 | -111.997 | fail |
| Y | 118.906 | 118.906 | -5.690 | fail |

Sampler gate remains 100 mV / 37.5 ps; XOR 100 mV / 75 ps. A/B/C/D had no wrong-sign samples in this candidate, but C/D still failed amplitude and delay. X/Y retained wrong-sign samples. B's passing result does not qualify the whole circuit.

Baseline HBT failures were min VCE at XD0061/62/115/116. Candidate failures are max VCE at XD0059/60/111/112 and min VCE at XD0061. MOS, MIM and tail-current predicates passed. The phase mean fell from 13.980 to 10.026 mV; VI current from 42.612 to 31.984 uA, still below the 50 uA minimum. VI voltage 9.031 mV **passes** its separate 5 mV minimum.

Do not propagate this rejected intrinsic candidate into an accepted layout. Next circuit work must address the measured headroom/common-mode and loaded settling together, preserving every original gate. Any subsequent passing intrinsic screen still needs changed PCells, full native DRC/LVS, fresh extracted RC, corners and closed-loop verification.

## Physical instance map

Read-only run [41273410851](https://github.com/Melihakbulut221/nssoc/actions/runs/41273410851) authenticated all 500 device records and 4928 physical instances, and uniquely mapped the 12 proposed changes. Nine controls passed. The prior run 41273236353 failed only on the native model spelling `npn13G2` versus composition `npn13g2`; the correction accepts that single explicit alias and rejects `npn13G2l`. Both runs are retained.

Some collector resistor PCells are shared with untargeted devices. A future layout edit must create private cells for the selected instances; a global shared-cell modification would change unrelated circuitry. The map contains complete paths, terminal partitions, enclosures and untargeted users. It did not acquire native geometry locally, generate a new layout, or assert physical acceptance.

All native archives, models and waveforms remain in GitHub artifacts/releases. Local project and project temporary directories remain empty.
