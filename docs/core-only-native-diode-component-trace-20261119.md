# Native diode constitutive component trace — 2026-11-19

Run https://github.com/Melihakbulut221/nssoc/actions/runs/44412751564, attempt 1, head `7e7664d2690f8181e333959ffa5b0f4ef068fe4f`, completed diagnostic capture, not repair. Artifact `14479475448`, SHA256 `c04258aa4e18710272afa0d56e5dca4790abc2b761462ff9a07f3fd81fde54c7`; all 32 output hashes independently verified. There are 457 component records and the unchanged 21.3261685 ns failed endpoint.

Nearest evaluations on either side of -0.10385606953280702 V:

| quantity | above boundary | below boundary |
| --- | ---: | ---: |
| VD (V) | -0.10385606953264315 | -0.10385606953472148 |
| DC current (A) | -1.1368542777127278e-13 | -3.7855933814271756e-10 |
| DC conductance (S) | 1.015092908011605e-12 | 2.265726249010148e-10 |
| depletion charge (C) | -3.184666645543411e-17 | -3.184666645605393e-17 |
| diffusion charge (C) | -7.968211632488509e-20 | -2.6533224010423077e-16 |
| depletion capacitance (F) | 2.982260941543909e-16 | 2.9822609415407983e-16 |
| diffusion capacitance (F) | 7.11478619225334e-19 | 1.5880475279312128e-16 |

The discontinuity is in the constitutive DC current and its diffusion charge, rather than the depletion-charge term or time integration alone. CONSTe is correctly 2.718281828459045. The actual lower-side branch has not yet been captured: it must not be called the reverse-current branch solely from VD < -3*vte, since breakdown selection also checks the temperature-adjusted breakdown voltage. Next trace explicitly captures the selected branch, adjusted breakdown voltage, temperature-dependent saturation currents, breakdown thermal voltage, transit time and temperature. No equations, PDK models or tolerances are changed; production runtime remains unchanged.
