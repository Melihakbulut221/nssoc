# Six-buffer routed result — 2026-11-19

Run https://github.com/Melihakbulut221/nssoc/actions/runs/44545302944 succeeded at 99aea3abd3ac6622674556f6854995436d9c1d6b, attempt 1.
Artifact 14543516160 (`core-only-regression-antenna-route-44545302944`), SHA256 `44feb72eb6405fbafdf4e8c729ae81b87cdeb24e2f3d8c0ed89f8eb84399eecd`; all 50 output hashes were independently checked in memory.
Final ODB `bd28f784aa3cad49b72197de70c394727ab0e72608610febd4c4e16dfc4a28bc` (`restored-status.odb`).

## Observed physical results
- 106672 instances, 103096 total nets.
- Router DRC 0 after iteration 3; native antenna 0 violating nets / 0 pins.
- Independent native wire/via and LEF-terminal geometry: zero inter-net contacts, disconnected signal nets, unwired multi-terminal nets and terminals missing geometry.
- Native decoder and synthetic geometry controls passed; real route removal was detected.
- All 103093 unaffected nonpower net records and 2113 clock nets preserved. 102977 encoded routes were fixed during repair and restored afterward.
- Instance geometry, masters, terminals, special wires, ports and die preserved from the two-diode preparation.
- Ten DRT-0349 warnings remain recorded in the native report; zero errors. Do not equate this with foundry DRC or transistor LVS.

## Next measurement
Run `cloud_core_only_regression_antenna_extraction.py` on the exact artifact and ODB above. The wrapper admits six-buffer functional collapse, all ten diode reconnections, the rejected one-antenna predecessor, and the two-diode repair. Export fresh Verilog/DEF, validate 1410 cumulative added diodes plus all ten moved diodes (including original ANTENNA_491/500), then extract nominal RC and measure slow/typical/fast PVT. Keep 20 ns and 5 percent derating unchanged. No pre-ECO timing result establishes timing for this candidate.

The wrapper import/compilation and 43 negative diode-rebinding controls passed in https://github.com/Melihakbulut221/nssoc/actions/runs/44547441337. These are preparation tests only. Actual RC/STA is pending. Qualified RC min/max, complete SRAM characterization, transistor LVS/foundry checks, pad/core signoff, external package/PCB timing and manufacturing approval remain open.
