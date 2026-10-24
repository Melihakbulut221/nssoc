# Native wire20 extraction passed; exact model composition next

[Extraction 39405777617](https://github.com/Melihakbulut221/nssoc/actions/runs/39405777617) passed using the actual 2.0 µm candidate GDS `b8ee72861b772cea2ea42746710dec3075c85fb2999c7204e55b9f1536585ab4`. Actual native ownership gives 1674 devices, 4774 terminals and 377 wire components. The newly generated network contains 116611 resistors and 77538 capacitors. Equal element counts to wire24 do not imply equal values: the new raw wire netlist is independently captured and hashed.

All 13 original raw-corruption controls passed. Per-point ground capacitance, mutual attachment/value, collapsed capacitance and native resistor topology/value checks passed. The preserved 8655 native short warnings were checked as terminals on the same physical conductor, not ignored cross-conductor faults. Body/substrate spreading and RF-distribution qualification remain open.

The new composition workflow consumes only the immutable wire20 archive, native device values and actual terminal ownership. It preserves all six real malformed-model controls, all 124 interface legs/372 data-base bindings and both interface faults. Neither old wire24 RC nor ideal intermacro connections may replace the fresh network. The original loaded waveform and device acceptance gates remain required afterward.

Mainchip fanout route39406681799 runs independently. All execution and evidence storage remain in GitHub.
