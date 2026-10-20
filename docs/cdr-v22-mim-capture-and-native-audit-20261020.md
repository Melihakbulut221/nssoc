# CDR v22 MIM capture and raw audit — 2026-10-20

All four extraction stages in39455570367 passed. MIM capture39456445937 independently binds all946points,111conductors and eleven actual intrinsic MIM devices. The new measured count is17674metal resistors and12700metal capacitors; no old12704-capacitor model is reused. All five real MIM/connectivity corruptions are rejected.

The next workflow independently checks original raw wire charge/resistance conservation and all original13wire and9MIM faults, then composes484native devices without duplicating any MIM. All19composition faults remain mandatory. Exact source deltas change only artifact identities, the measured capacitor count and corresponding summed RC count30374. A count match alone cannot pass a raw audit.

No individual dynamic audit/composition receipt is committed before the run: each stage binds the same run's immutable release result. Capture and device-binding receipts are pinned to the already completed runs.

The CDR still requires the original full34.25ns256-bit early/late/clock-stopped/VI-off tests. All116HBT and46MOS remain subject to their original limits. Physical and RC checks are not electrical or fullPHY acceptance. All artifacts remain in GitHub.
