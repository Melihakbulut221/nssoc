# Whole PLL845 native RC capture — 2026-10-20

The entire frozen PLL GDS is the extraction scope: all parent and child metal/via geometry,235 actual conductors,26 native MIM masks,845 intrinsic device identities and2737 terminal identities. This replaces neither the actual layout nor its clocks with a surrogate. The earlier parent-only RC scope is insufficient.

The source is native terminal-reference run39350440897, immutable summary73e731a6f5f0b426170163a8ecd7f790e23364e6877747a32487fdeb1e97254d. All1877 logical metal/public-port points are re-probed in the original LVS and wire connectivity databases. Exact physical coincidences are deduplicated only if coordinates, layer and both owners agree; all logical labels remain mapped. No coordinate quantization or arbitrary same-net merge is allowed.

The input adapter compares every original metal/via/MIM drawing polygon with the extraction GDS. Metal5 probe points must remain outside the intrinsic MIM mask. The pinned Magic native runtime and previously proven explicit-MIM technology semantics retain all26 capacitors as model instances, not extra wire capacitance estimates.

Fresh capture must retain235 independent resistor components, all physical points and the complete26-capacitor terminal-owner/dimension multiset. Ambiguous parallel identical capacitors remain explicitly grouped until raw native-location auditing resolves identity; no unique identity is invented. Eight mutated-capture controls cover missing/changed/reversed MIMs, wrong model, cross-conductor short, missing physical port, negative R and negative C.

A successful capture alone does not close raw per-point R/C conservation, complete intrinsic model composition, substrate spreading, poly/diffusion/salicide access resistance, loaded/closed-loop electrical behavior or PEX qualification. Those gates remain false until independently proven. All work, artifacts, failures and source-bound reports run and stay in GitHub; the local NSSOC directory remains empty.
