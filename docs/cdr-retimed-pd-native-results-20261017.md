# Actual retimed phase detector: native results

GitHub run39056756395/source3aa56a8e362dd952c0de7c081efe37882ca5d7ec completed all11cases. Full native summary reports and SHA256 receipts are retained in evidence/cdr-retimed-pd-pass-20261017.json, with release URLs for waveforms and logs. No local simulation or result archives are used.

The real connected circuit has four samplers, four buffers and two extracted XORs:114HBT/98rppd/10MIM/54contacts plus8040wireR/5282wireC in the XOR macros. The same original-bit identities and timing limits passed at nominal/hot/cold supply, temperature, resistor and capacitor conditions for both early and late input transitions. All use the HBTtyp model, not a complete HBT process/mismatch campaign. Both constant inputs passed the zero-phase bias bound. Actual swapped comparisons, wrong retiming edge and stopped clock were rejected by the original oracle. Zero-source startup,114nativeOFF flags, numerical diagnostics and all native device/capacitor checks were inspected.

| Case | Native average X-Y (V) | Result |
|---|---:|---|
| nominal_early | -0.155767670 | original data/device/phase gates pass |
| nominal_late | 0.149445943 | original data/device/phase gates pass |
| hot_early | -0.152746161 | original data/device/phase gates pass |
| hot_late | 0.145737688 | original data/device/phase gates pass |
| cold_early | -0.148307130 | original data/device/phase gates pass |
| cold_late | 0.142518350 | original data/device/phase gates pass |
| constant_zero | 0.000007162 | original data/device/phase gates pass |
| constant_one | 0.000007304 | original data/device/phase gates pass |
| swap_comparisons | -0.149445943 | actual fault detected |
| wrong_edge | 0.095360134 | actual fault detected |
| clock_stopped | 0.000069409 | actual fault detected |

This closes the tested connected retimed-detector behavior only. External8GHz clock and ideal external reference currents remain. The detector has not yet driven the real V/I stage and loop filter, acquired a recovered clock, undergone fresh interblock physical extraction or been replicated into a verified x4 PHY. The next integration must preserve these actual connections, load its output with the real converter, prove phase-correction polarity and run native closed-loop acquisition/jitter tests. The passing XOR extraction does not cover the new sampler/buffer interconnect.
