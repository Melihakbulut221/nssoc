# CDR v2 intrinsic model binding correction

Run 39081203572 rejected the new MIM-aware capture with `Baseline native MIM identity/order/value changed`. The driver restored v2 geometry correctly, but imported the original `audit_cdr_mim_intrinsic.py`, which reads `cdr-retimed-binding-pass-20261018.json` (v1). The reordered physical children have new native device identities. This failed report and its exact archive hashes remain recorded.

The v2 helper changes only the receipt path to the independently verified v2 binding. The driver explicitly checks that this binding run and summary digest equal the binding used by the capture. The original helper and v1 evidence remain unchanged. The expected eleven device identities, plate ordering, exact dimensions, raw record checks, resistor/capacitor conservation and all 22 corruption controls are preserved. No native RC value, device dimension or acceptance threshold is changed.
