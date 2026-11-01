# Original class join for routing obstacles — 2026-11-01

[Actual cloud join 41261629239](https://github.com/Melihakbulut221/nssoc/actions/runs/41261629239) succeeded after nine source controls passed in run 41261494138. It consumes the complete compact reduction from run 41254369577 and the exact original 143,212-entry class map and insertion plan.

Of 373 observed endpoint nets, 148 are original mutable nets, 220 are original `ROUTED` nets temporarily converted to `FIXED`, three are protected and two are power/ground. The 220 temporary counterparts contribute 448 ordinary same-layer, positive-area witnesses across 423 selected markers. All 434 selected markers, 162 other records and 946 witnesses retain their original ordinals and multiplicity.

The [25-file actual proof](https://github.com/Melihakbulut221/nssoc/tree/00f2e8ed3056103f239eae1b4804c7ef70cfc0eb/docs/evidence/mainchip-counterpart-scope-terminal-41261629239) and [14-file control proof](https://github.com/Melihakbulut221/nssoc/tree/63f3f4f0996fdfbd43cc9bc915de9881c953df9f/docs/evidence/mainchip-counterpart-scope-terminal-41261494138) are imported under `docs/evidence`.

The original `fixed_plan` freezes every ordinary net outside the 608 mutable nets. The distinct 1,691 protected clock/fixed nets are a subset of that frozen set. This join resolves the classification ambiguity; it does not prove the cause of the original iteration-10 shorts, whose mutable wire geometry was not retained.

The earlier actual fixed audit completed with return code 0 and a complete terminal record. Its 26,885-byte native source has SHA-256 `afbc5b22116f2f0649a087ae1e8147235921cf2477e78ed78675301093454854`, identical at original routing source `ddc1cbddf68096c5e976bf9acda5c5fb0168c5b9` and reducer source `8511f25d897d03e27a05222f5a731abd13534376`. That audit checks exact serialized DEF, instances, identities and encoded classes. Review its exact producer/input binding and reuse this evidence where sufficient before deciding whether another native snapshot projection is required.

No net has been unfrozen or rerouted by this analysis. A targeted repair must explicitly admit any additional nets, retain all protected nets and power/ground, preserve unrelated connectivity and placement, and repeat actual routing, DRC, antenna and timing gates. Do not repeat the 689 MB observer reduction or classify all 222 previously unclassified endpoints as signal candidates. All data processing remains in GitHub.
