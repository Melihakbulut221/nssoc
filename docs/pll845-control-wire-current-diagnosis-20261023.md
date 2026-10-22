# PLL845 existing-capture control-wire current diagnosis — 2026-10-23

The complete 1 us native acquisition remains rejected: final feedback 110.440673637 MHz versus 100 MHz, phase span 9.190319177 ns versus 50 ps. No acquisition threshold, window, circuit, solver or waveform changes.

The immutable composition and prepared reader show VCTRL native cluster 480 connects both pump switches, four VCO control PMOS gates, the 140/47 um bias resistors and 8 x 8 um MIM. The VCO control connection is present. The old raw file has voltage-source branch currents but no individual MOS channel-current probes. UP/DOWN duty alone is not pump current.

Actual output metal branches R3380/R3379 are each 53.7174 ohms; both endpoint voltages are present in the original 5106-column record. The cloud diagnostic binds all 845-device records, native terminal mapping, original header and rejected reader report before computing modeled metal current from the original voltage difference and actual wire resistance. All nine VCTRL device boundaries and local wire shunt capacitances remain explicit. Reported current enters the interior wire network; it is not intrinsic MOS channel current.

All original 3,201,410 samples and 5106 columns undergo the unchanged full capture validator. A separate exact binary64 column copy is retained in cloud storage for diagnosis; the original 130,771,392,219-byte raw archive remains immutable. Acquisition and cycle results must exactly match the completed reader. Native SPICE and the already completed 6167 voltage envelopes are not rerun.

Charge integration uses the original adaptive grid. Windows report actual included endpoint samples without interpolation. Interior wire-capacitor charge change, integrated boundary current, their residual and coarsened quadrature difference are reported. The latter is a numerical indicator, not a certified error bound. Workflow success means the diagnostic completed and reproduced the original rejection; it does not establish PLL/PHY, device-safety or qualified-PEX acceptance.

Controls reject changed model resistance, wrong native owner, missing terminal, missing/duplicate columns and changed public mapping. An irregular-grid integral and sign are checked independently; nonfinite, missing and nonmonotonic inputs reject. All tests and full-record analysis run on GitHub-hosted Actions; the local source/CAD workspace remains empty.


## Actual coupling-capacitance correction
Cloud controls39872681373 rejected the initial assumption that every control-network capacitance terminates on wire_cref. The actual model also contains cross-net capacitances to supplies, clock, feedback, UP/DOWN, internal nodes and the two explicitly grounded sub/avss ports. These are retained with both actual endpoint voltages. Interior total charge includes every capacitance crossing the interior boundary with correct orientation; capacitance entirely within the interior cancels algebraically. The two ground ports follow the immutable bench's exact zero connection, not a substituted signal waveform. No native gate or circuit was changed.
