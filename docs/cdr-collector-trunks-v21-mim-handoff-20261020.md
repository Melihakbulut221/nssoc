# CDR v21 fresh intrinsic-MIM handoff

The parent GDS passed native 560-category DRC (zero markers), full hierarchical
and flat 484-device transistor LVS, and the existing geometry fault controls in
run 39440691879. Extraction run 39441534722 is still the prerequisite; its plane
and wire-input stages have passed, while binding and RC are not yet accepted.

The new MIM job waits for that exact run, commit and workflow to succeed. It
retrieves and SHA-256 verifies all four stage publications and cross-binds their
physical source receipts before invoking native CAD. It does not restart a live
prerequisite, use v20 parasitic values, or treat a waiting job as success.

The controller adapts the v20 capture by artifact identity only. The exact source
delta is checked together with both the earlier capture guard and the new v21
extraction guard. All 946 native terminals, 111 physical conductors and eleven
actual intrinsic MIM devices must retain native ownership. Mask geometry,
terminal binding and all five deliberate MIM/short fault tests remain unchanged.
R/C counts must come from fresh extraction; the former counts are not acceptance
targets.

Capture alone is not raw-capacitance audit, qualified PEX, waveform acceptance,
closed-loop CDR, or complete PCIe PHY. After capture, audit the raw extraction,
compose against actual transistor terminals, and run both unchanged 34.25 ns
early/late loaded waveform gates plus clock-stopped and V/I-disabled controls.
The rejected v20 electrical results remain preserved.

All CAD, runtime downloads and evidence archives are confined to GitHub runners
and releases. Local workspace remains empty.
