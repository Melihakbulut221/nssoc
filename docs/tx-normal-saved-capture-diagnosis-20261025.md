# Completed normal TX: same-row diagnosis proposal

This source-only observer concerns completed, rejected run 40168554741 at 2e63863abb0309c245d89e2a3d4934fe40a2b2ed. It never resumes its process or launches SPICE. Both authorization flags are false and no workflow is registered. Its original 34 ns capture and electrical rejection remain authoritative. Authored controls have not been executed.

## What the existing result establishes

The exact 77,681-row/14,182-column capture has 14 wrong-sign and 30 under-100mV output samples at the unchanged 0.3/0.5/0.7 UI positions (256 bits, UI 125 ps, START 2 ns). The actual maximum step is 0.5 ps. All 76 failed HBTs violate only the post-START 0.4 V VCE minimum; no max-|VCE|, max-|VBE|, per-emitter Ic or MOS gate fails. CMOS interfaces fail common mode (minimum 1.7683196 V) despite sufficient differential margin. Level16 passes; level8 and level4 lose differential margin; the final interface has wrong-sign combinations. These are aggregate facts, not a causal order.

The exact independent 589-device native role catalogue maps 75 failures to 73 selectors and final macro f's two tails. Worst XD5676 is final selector bank a/sp, Nx6, C/B/E/S at w0003521/w0003522/w0003523/body000, native clusters 648/697/702/1. XD5644 is outside that tree catalogue: its actual C/B/E/S/Nx and Ic can still be measured from the exact contract, but its full output-block role must be independently established from the authenticated composition; no ID-based role guess is allowed.

## Concrete experiment using only saved bytes

First authenticate all seven ordered native parts (7,041,667,734 compressed bytes, combined SHA e0a126d17e8503a9b3217351c53aad480330fbae126126035c79541610e213f2). The existing full raw is 8,813,839,719 bytes, SHA 1731a021f5c2b8e779789e4b511e97f7a268cdd172ab52f598f0fd0f0ffa4be7. Do not load the archived native image or start any engine. Restore only safe exact members needed for analysis, stream/hash all original members and compare the immutable result inventory. Every contract, bench, log, OP and raw input remains individually pinned. Publication must keep full result files separately from a small index.

Compile only exact frozen pure measurement functions from the original source and rerun their complete review: zero OP, full native header/order/extent/finiteness/time-step validation, all 604 HBTs, all 5376 MOS devices, all five 6912-sample interface screens, and 768 output samples. Require complete JSON equality with the original report before any diagnostic output. Original interpolation is retained only for original oracle reproduction and explicitly labelled.

Then enumerate the 30 weak samples with exact bit index/phase and adjacent native row brackets. At both rows record simultaneous physical nine-combination margins/common mode at CMOS→level16→level8→level4→final, actual mux mp/mn and output op/on, all 76 affected HBT C/B/E/S/VCE/VBE/native Ic/Nx, measured branch-bias currents, selected-path public clocks and actual selector-base access drops. Nothing is sampled at a fitted or shifted time.

For each failed HBT, retain the actual native row of all five original extrema, all 19 devices in its proven macro at that row, and every contiguous below-0.4-V interval with entry/exit row bounds. For each affected original UI, enumerate native brackets crossing fixed 0/100/150mV differential thresholds for every actual parallel pair. This distinguishes a settled low-margin input, a late or wrong selected transition, clock-base movement and selector/tail headroom loss using simultaneous measured values. It does not prove causal direction or authorize a bias/geometry edit.

The original vector inventory contains 604 HBT Ic targets but no thermal/dtemp/HBT temperature-state observation. Thermal states must be reported unavailable. Native Ic is the originally saved model observable, not asserted to be full external macro-terminal current; no KCL proof, resistor-current inference or thermal reconstruction is introduced.

## Source and proof boundary

`scripts/tx_normal_saved_capture_diagnosis.py` implements immutable original-review replay plus the native-row analysis. The qualified 589-device catalogue is projected against every actual contract C/B/E/S/model/Nx before use. Its companion checker defines 18 rejection controls and hand-computed positives for endpoint/interior brackets, same-row VCE/VBE/current normalization, all nine parallel combinations, polarity, native crossing brackets and active-window segment indices. No authored code or test was run locally.

Before any hosted readback: independently review this source; execute synthetic and actual-input controls; implement/review the cloud-only seven-part restoration/source-identity/publication wrapper. Add real contract/catalog mutations (wrong C/B/E/S, Nx, role, sample phase, source bits, missing/extra member/vector, corrupted original report). The raw observation itself is still unexecuted. Native, electrical, all31, PLL, PHY and main-chip acceptance remain false.
