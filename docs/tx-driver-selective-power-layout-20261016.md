# Compact driver selective supply-routing candidate

Compact extracted driver38892907391 completes34ns without solver diagnostics and eliminates all wrong-sign samples. It still fails unchanged gates: output minimum96.1298mV (one sample below100mV), CMOS149.6636mV (one below150mV), final interface107.7576mV (549below150mV) and12HBT checks. All672MOS pass. CMOS CM1.85634–1.86098V remains lower than the byte-identical intrinsic control1.89459–1.89826V. This motivates a supply-resistance experiment, not a proven diagnosis or acceptance.

Keep every device, position, finite contact, signal width, original voltage, source bits, test phases and electrical limits. Only avdd/dvdd/avss Metal3 escapes increase1.2→1.6um and Metal4 risers2.0→3.2um. Signal/substrate paths, Metal5spines and actual2x2uppervias remain as in compact. Do not widen Metal5 beyond the existing7um pitch clearance. Generate actual GDS and repeat original560categoryDRC, raw/aggregate deep/flatLVS and seven corruption controls. Passing geometry must be followed by fresh junction/anchor/RC/composition and the unchanged loaded electrical study; never reuse compact260R300C by assumption.

The intrinsic source is unchanged; no ideal rail was inserted inside the extracted driver. Qualified substrate/poly/diffusion/point-attachment/RF/PVT and full serialPHY acceptance remain open.
