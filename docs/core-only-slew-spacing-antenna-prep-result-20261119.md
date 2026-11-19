# Slew-spacing antenna preparation passed — 2026-11-19

Run https://github.com/Melihakbulut221/nssoc/actions/runs/44477663047 succeeded at `ea2bf956f4fc240ca27b77e803e215068687ec1e`, attempt 1. Artifact 14506853261 SHA256 `057c9964796507d082a385c92076a2617f67cb05fe6b37556af4ede89dc3c5b1`; all 13 output hashes verified.

Native ODB `fd3890d4cdcee434e279277375a484922cc4e3a5b7ae6f00235d2eb45ed22845` contains exactly one added `sg13g2_antennanp`, `ANTENNA_2566`, connected to `nssoc_sta_n_56323`. Instances: 106650 to 106651. All original cell geometries/statuses/connections preserved. Both added power pins have positive-area same-net rail contacts; negative supply/contact controls pass. 103084 other non-power net records, including all 2113 clock records, are unchanged. Existing NDR assignments unchanged.

This proves insertion and local supply contact only. Route the one signal net with every other encoded wire FIXED, then restore ROUTED status with exact preservation checks. Require inherited NDR assignments and layer width/spacing definitions unchanged, native DRC 0, antenna 0 and independent geometry 0. Any failure rejects the candidate. Fresh RC/STA and updated 1398-diode cumulative export provenance will be required afterward; the added load has not yet been timing-qualified. Production signoff remains open.
