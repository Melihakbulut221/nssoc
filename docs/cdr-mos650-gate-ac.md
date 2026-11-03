# Actual native MOS gate impedance and missing physical poly resistance

Run41696724132/sourcea78102915a5a1ead89ff23331c26a149eebcaf0d on codex/cdr-mos650-gate-ac SUCCEEDED. The exact frozen native Ngspice engine simulated all4 distinct actual W/L/AS/AD/PS/PD tuples covering all200 physical MOS IDs, in both rfmode0 and rfmode1. There are17 finite complex measurements per case from1MHz to10GHz at0.8V gate and0.6V drain bias, with explicitpre_layout0. Returncode0, no numerical warnings/errors. Native simulation elapsed0.081410626s. Raw deck, measurements and complete model/runtime remain in release433087144.

The native showmod readback proves ordinary PSP103 models have rgo=0 and rshg=0; the RF PSPNQS103 alternatives have swnqs=5, rgo=40, rshg=3. This confirms the missing explicit compact gate-resistance terms in the model currently used; it does not imply zero real input impedance. RF mode also changes non-quasistatic behavior, so the difference between QS and RF impedance must not be interpreted as a directly measured physical resistor.

At1GHz (real part of complete input impedance, ohms):

| Physical W (um), L=0.3um | QS Re(Zin) | RF Re(Zin) |
| --- | ---: | ---: |
| 8 | 5.442743 | 74.088345 |
| 8.885 | 4.900604 | 71.998947 |
| 8.89 | 4.897847 | 71.988784 |
| 9 | 4.837984 | 71.769343 |

All50 physical poly/contact groups still require distributed gate-path modeling. The actual wrapper fixes ngcon=2, whereas chained physical groups have one top metal contact feeding multiple unit gates. Switching to RF mode without establishing contact geometry and overlap is not physical qualification.

The complete bound Magic extract technology reports pc contact values15000/20000/8000 across nominal/high/low R variants, but NO ordinary poly/allpoly sheet-resistance entry. The nres/active7000 entry is for recognized Rsil devices, not an existing normal-gate extraction rule. Do not silently treat normal poly as zero resistance or equate a resistor-device declaration with a calibrated gate extraction model.

Next physical work:
- Resolve ordinary gate versus access-poly sheet resistance and its process basis; preserve original foundry model files.
- Build the network from actual native IDs, contact polygons and full gate-poly paths. Do not collapse the long shared stem into an ideal node.
- Establish overlap explicitly. A useful next characterization is RF/NQS with separately disabled and native-read-back gate-resistance terms, retaining NQS; do not blindly subtract real input impedance or apply an unverified RF layout model.
- Verify discretization/model coverage, add poly coupling and intrinsic MIM consistently, then run the original complete loaded circuit gates and full serial link qualification.

Published IHP process specs identify Rsil as salicided n-doped gate poly with target7ohm/square, but using this value for these gates requires actual layer/process/model applicability checks:
https://ihp-open-pdk-docs.readthedocs.io/en/latest/process_specs/02_process_control_params.html

This result is a real native model characterization. Physical distributed gate RC, full650 model composition, full PHY and final chip timing remain unqualified.
