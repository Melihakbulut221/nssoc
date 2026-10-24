# CDR v24 loaded waveform rejection and next physical diagnosis

Run: [39497247685](https://github.com/Melihakbulut221/nssoc/actions/runs/39497247685).
The actual 476-device parent and fresh 17654R/12682C model were simulated for the complete original 256-bit capture. All four cases finished with native return code zero and no simulator diagnostics. This is not CDR or PHY acceptance.

Both nominal cases pass the original device checks after shrinking the 32 clock-selector HBTs from Nx4 to Nx2. Both still fail the original 100 mV sampled margin, 37.5 ps clock-to-valid and phase/current requirements. The negative controls detect disabled VI bias and stopped clock; their successful detection is not nominal acceptance.

| Case | Sampler | Minimum margin (mV) | Wrong samples | Below 100 mV | Maximum clock-to-valid (ps) |
|---|---|---:|---:|---:|---:|
| nominal_early | A | 51.940249 | 0 | 111 | 42.968750 |
| nominal_early | B | -4.784183 | 42 | 129 | 45.468750 |
| nominal_early | C | -23.556781 | 22 | 128 | 51.093750 |
| nominal_early | D | -132.334682 | 97 | 129 | 66.718750 |
| nominal_late | A | 41.854024 | 0 | 129 | 43.906250 |
| nominal_late | B | 85.249384 | 0 | 64 | 38.906250 |
| nominal_late | C | -12.490725 | 18 | 128 | 49.531250 |
| nominal_late | D | -86.901452 | 74 | 128 | 57.343750 |

Early phase average is -11.706064 mV and late phase average is +16.769487 mV; the original nominal targets require the corresponding sign and at least 30 mV magnitude. VI mean currents are -36.520413 uA and +49.247574 uA and do not pass the original signed-current requirement.

Next: reconstruct the real master/slave latch graph and every physical parallel clock-selector bank from these exact captures. Reproduce all 120 HBT checks and all four original sampler checks before analyzing internal data transfer and track/hold currents. The diagnosis retains original external timing, loads, sample windows and acceptance thresholds; no resimulation, shifted clock or regenerated internal data.

The source-delta manifest binds this diagnosis to the prior v23 implementation. Allowed changes are immutable v24 report/capture identities, output names, and the actual Nx2 selector census and zero nominal HBT violations. Previous failed v23 data remain unchanged.

Full-loop CDR, actual recovered clock, PVT/RF/body qualification, serial Gen3 x4 integration and final mainchip setup/hold remain open.
