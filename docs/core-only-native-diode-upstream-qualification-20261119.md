# Official IHP diode reduced-fixture qualification — 2026-11-19

Run https://github.com/Melihakbulut221/nssoc/actions/runs/44414922639, attempt 1, commit `a140a4495c534e10b5a053c3ae828d5d40cbfe1f`, artifact `14478892561`, SHA256 `8ff04397928f6ec5b7603d20ba03ef81d415a25afaee8a875c16ee9291f4ea85`; all 18 output hashes verified independently.

The unchanged published ngspice47 binary (SHA256 `eaca52dad06845779fed4f50420a6a0cf4a32776e6a572432275f350002b87b8`) reproduces the old-model failure at 21.3261685 ns with 21,366 rows. With the complete unmodified IHP diode library at commit `013bb30bb7c8f9d3c85173378597ac992ef7a272` (SHA256 `e6211bd0318122fbeb707498ede893223c332098cbb21c441b28b9d8c365e83d`), the same reduced circuit completes 50 ns with 50,014 finite waveform rows at each of -40, 27 and 125 C, without abort. Circuit topology, drive and solver tolerances are unchanged. This is a real model revision, not numerical equivalence to the old model.

Next gate: the full transistor-level 4mA pad's six slow-corner current cases (data 0/1, turnoff/enabled/disabled) with only the diagnostic input copy of diodes.lib replaced. The original MOS, resistor, pad SPICE and OSDI inputs remain hash-bound. Local production PDK, Liberty and timing constraints are not modified. This reduced result does not close pad Liberty, extracted pad behavior, whole-chip timing or manufacturing signoff.
