# Native extracted timing metric capture

LibreLane 3.0.5 `librelane/steps/step.py`, DefaultOutputProcessor, converts `%OL_METRIC_F` to Decimal and `%OL_METRIC_I` to int. The prepared core extraction adapter previously rejected Decimal and could not serialize it with the default JSON encoder. This would fail after otherwise successful native STA. Accept native Decimal values while retaining finite-value, integer-count and same-corner checks; serialize with LibreLane's own GenericDictEncoder. Native updates are returned unchanged. This is format compatibility, not timing relaxation.

Cloud qualification uses the actual pinned runtime's output parser and actual CoreExtractedSTA.run_corner adapter, replacing only the inherited subprocess result. The positive example retains two setup violations and a negative slack. Negative controls cover NaN, infinity, booleans, strings, missing required metrics, negative/fractional counts and a foreign corner. This is parser/adapter qualification, not circuit execution or setup/hold closure. Native STA logs remain archived by the extraction producer.

Prepared branch codex/core-only-native-metrics inherits the routed-boot and extraction preparation. For actual extraction or boot, use their respective workflow contents; this branch workflow only qualifies guards/adapters/metrics. DRT producer 44263061910 remains live and is untouched.
