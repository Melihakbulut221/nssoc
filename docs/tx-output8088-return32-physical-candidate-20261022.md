# Output AVSS physical return repair candidate

The exact original native-wire diagnostic39756511142 measured 30.270116 ohm from output-tail emitter A0789 to the actual AVSS port. The dominant edge R139947 (raw P_avss.n153 to P_avss) is29.8196 ohm and contributes98.5117% of unit-current network energy. The11,693-node/15,648-resistor AVSS component retains all parallel paths; KCL residual is below8e-12 A for this solve. All10 analytic and rejection controls passed. This is a passive DC diagnostic, not a new transient pass.

The new power128return32 candidate adds32um middle metal to the output AVSS handoff's four long spans. It retains every original6um return polygon, every native via,20um endpoint-access sections, all core128um trunks/32um feeds, output placement, native devices and165 public ports. SUB and signal paths are unchanged. Foreign-metal clearance is checked before committing any route; an obstruction rejects the candidate rather than silently narrowing it.

All previous native DRC, deep/flat8088-device LVS and fault gates remain. A new output-return-open fault cuts the full widened bottom span, ensuring an old parallel6um path cannot hide the injected break. The original PDK/deck and exact-port check hashes are pinned.

A physical pass must be followed by fresh native conductor/anchor binding, raw RC extraction, composition and the original complete8088-device loaded waveform. Neither model resistance editing nor a DC estimate is electrical acceptance. Current/full-serial PHY gates remain open.

Mainchip39738186533 saved its next exact routing state: completed iteration violations173046,97152,88437,21505. Iteration4 was80% through, reporting13722 interim violations. Continuation39756174188 resumes that saved process. These are routing counts, not final setup/hold or production DRC acceptance.

## Clearance rejection and corrected addition

Run39758169383 rejected generation before DRC/LVS: the centered32um output AVSS vertical addition violated the original1.645um foreign-clearance guard toward the unchanged SUB route by0.645um. The failing geometry/logs remain in its release.

Only the added32um strip on the output-side TopMetal1 vertical span is shifted2um away from SUB. Every old6um path polygon, all endpoints, via cuts, SUB and signal material remain unchanged. The width stays32um and the clearance guard remains1.645um; no rule waiver or narrower fallback is introduced. Native generation and all physical/fault gates must pass again.
