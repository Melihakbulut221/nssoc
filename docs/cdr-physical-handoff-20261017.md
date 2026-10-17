# CDR physical handoff — 2026-10-17

Native cloud run39067291672 verified both exact buffer leaves from source4160cc84c1678de94cbc324b7363ea57dfbf0c1c. Data and select pass all560 DRC categories, deep/flat14/16device LVS and five real/reference corruption checks each. Complete reports and archive manifests are retained in `docs/evidence/cdr-buffers-physical-pass-20261017.json`. This is leaf physical evidence, not extracted electrical or full-loop acceptance.

Next physical candidates implement the actual differential feed-forward RC networks from frozen `cdr_retimed_pd_vi_v1.spice`. Three types cover five parent instances: retime (A→C and B→D), data (A/C→comparison buffers) and select (retimed-edge→selector buffers). Each type contains four1um-wide rppd resistors, two MIM capacitors and six explicit substrate contacts. Series/shunt lengths are respectively5.4/12.6um,3.6/21.6um and6/8.6um; MIM sides3.6um,3.6um and4.8um. Parallel capacitor connection bypasses only the series resistor exactly as in the native schematic; it is not replaced with an ideal divider.

The new GitHub-only matrix must pass native560rule DRC, deep/flat12device LVS and reject changed resistor length, removed capacitor, physical output open, input-polarity short and off-grid metal. Repeated same-family instances are independently normalized from the full PD source and must have identical terminal/parameter maps. Existing source and previous failures remain unchanged.

Parent assembly still needs the exact sampler cells, four buffers, two verified XOR cells, five passive networks and V/I leaf, with real interconnect and fresh RC. Fixed-phase native PD tests, VCO feedback/acquisition and all final PHY/mainchip gates remain required.
