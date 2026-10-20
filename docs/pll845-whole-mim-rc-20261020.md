# Whole PLL845 native RC capture — 2026-10-20

The entire frozen PLL GDS is the extraction scope: all parent and child metal/via geometry,235 actual conductors,26 native MIM masks,845 intrinsic device identities and2737 terminal identities. This replaces neither the actual layout nor its clocks with a surrogate. The earlier parent-only RC scope is insufficient.

The source is native terminal-reference run39350440897, immutable summary73e731a6f5f0b426170163a8ecd7f790e23364e6877747a32487fdeb1e97254d. All1877 logical metal/public-port points are re-probed in the original LVS and wire connectivity databases. Exact physical coincidences are deduplicated only if coordinates, layer and both owners agree; all logical labels remain mapped. No coordinate quantization or arbitrary same-net merge is allowed.

The input adapter compares every original metal/via/MIM drawing polygon with the extraction GDS. Metal5 probe points must remain outside the intrinsic MIM mask. The pinned Magic native runtime and previously proven explicit-MIM technology semantics retain all26 capacitors as model instances, not extra wire capacitance estimates.

Fresh capture must retain235 independent resistor components, all physical points and the complete26-capacitor terminal-owner/dimension multiset. Ambiguous parallel identical capacitors remain explicitly grouped until raw native-location auditing resolves identity; no unique identity is invented. Eight mutated-capture controls cover missing/changed/reversed MIMs, wrong model, cross-conductor short, missing physical port, negative R and negative C.

A successful capture alone does not close raw per-point R/C conservation, complete intrinsic model composition, substrate spreading, poly/diffusion/salicide access resistance, loaded/closed-loop electrical behavior or PEX qualification. Those gates remain false until independently proven. All work, artifacts, failures and source-bound reports run and stay in GitHub; the local NSSOC directory remains empty.

## Preserved-capture diagnosis

Native run39352067225 completed the actual extraction with exit0 in3.51s:3380 R,5104 C,235 physical conductors and1604 exact physical points representing1877 logical references. Capture validation rejected one of26 MIMs. Review39352510835 reused the same immutable raw files without rerunning CAD and isolated the only discrepancy: native width11.200000000000001um versus exported11.2um, on physical component pair7/38; length11um matches.

The candidate now derives each expected width/length from integer GDS mask coordinates, allowing at most one binary64 ULP when matching the native extractor's floating dimensions to that exact geometry. It does not round dimensions to an arbitrary tolerance. Both width/length orientations are considered only when the original native values uniquely select one. All26 source devices must reject a1nm native-dimension change and a1nm mask-dimension change. These52 controls mutate metadata; they do not claim to be new physical-GDS fault runs. The eight original capture corruption controls remain mandatory.

Both failed runs and their native outputs remain immutable. A new successful review, if achieved, will still require independent raw per-point R/C and native MIM-location auditing before composition.
