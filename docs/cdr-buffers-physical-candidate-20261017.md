# CDR data/select buffer physical candidates — 2026-10-17

These two missing leaves are required for the four-buffer retimed phase detector parent. They implement the exact `nssoc_cdr_data_buffer_v4` and `nssoc_cdr_select_buffer_v4` cells already loaded in native campaign 39061446683, not replacement behavioral sources. The source SPICE is pinned to SHA-256 `8b9ade6650c8d5153f3d872660b04d8cac1970220a6fc5fc233ec05489bb2d7c`.

Both cells contain four native IHP HBTs with Nx 1/2/2/4. Data has three 8um-wide rppd resistors of lengths 2/1.8/1.8um; select adds the actual 4.2um ground-divider resistor. Each primitive has its own substrate contact, with SUB distinct from AVSS. Public pins are dp/dn, qp/qn, AVDD, AVSS, SUB and IREF. Native PCell bodies and pin shapes are routed with actual metal and vias; no blackbox.

The GitHub-only matrix must prove all 560 DRC rules, deep and flat transistor LVS with exact 14/16 primitive/contact census, and rejection of wrong HBT finger count, missing HBT, physical output open, supply short and off-grid geometry. All source inputs and outputs are hashed. Failed results and full geometry are published. The original V/I leaf methods are unchanged.

At introduction these are unverified physical candidates. Even successful leaf DRC/LVS does not prove the retimed PD parent, its RC-loaded behavior, recovered-clock feedback, complete Gen3 x4 PHY or mainchip timing. Next: assemble actual sampler/buffer/XOR/V-I leaves and feed-forward resistor/MIM networks with the source pin map, then extract fresh parent RC and rerun the fixed native PD and full-loop gates.
