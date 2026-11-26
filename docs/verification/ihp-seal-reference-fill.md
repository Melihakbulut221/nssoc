# Top-metal fill on IHP's original seal-ring reference

PDK c4b8b4e5e7a05f375cca3815d51b3a37721fbf5c, KLayout 0.30.7. Upstream input: libs.tech/klayout/tech/drc/testing/testcases/unit/sealring.gds, SHA-256 88c2cb006a1bc27cfe080f21d10149cb08172a4bb7d8801a077a5c09f94eeeb6. Single top sealring_pt1, DBU 0.001 µm. This is a rule-test fixture.

```sh
tech="$PDK_ROOT/$PDK/libs.tech/klayout/tech"
klayout -n sg13g2 -zz -r "$tech/scripts/filler.py" -rd output_file="$PWD/reference-top.gds" -rd no_activ -rd no_metal "$tech/drc/testing/testcases/unit/sealring.gds"
```

Measure each layer recursively with KLayout Region.new(top.begin_shapes_rec(index)).area and .holes.area. Multiply square DBU by 0.000001 to obtain µm².

| Measurement (µm²) | Original fixture | After native TopMetal fill |
|---|---:|---:|
| EdgeSeal 39/0 enclosed hole | 236133.507812 | 236133.507812 |
| TopMetal1 filler 126/22 | 0 | 86650 |
| TopMetal2 filler 134/22 | 0 | 86650 |

The earlier full-interface snapshot had zero area on all three measures. The upstream filler macro uses EdgeSeal.holes for both layers. The PDK generator scripts/sealring.py uses the SG13_dev sealring PCell, subtracts twice the PCell edgeBox from the supplied dimensions and places the instance in the input layout top with a micrometre offset. The BEOL 6_10_sealring.drc deck covers structures outside the ring, an unbroken Passiv enclosure, spacing to active structures, corner geometry and ring count. No placement dimensions were inferred for NSSOC. Closing density still requires a product-authorized die/pad/seal floorplan, all native fill stages and the full density/rule checks on that layout.
