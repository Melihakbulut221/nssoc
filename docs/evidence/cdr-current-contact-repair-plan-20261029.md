# Current nominal contact measurements and bounded repair candidate

The first candidate to **screen for feasibility** is additive reinforcement of the existing lower master-tail (M_TE) TopMetal2 bridge and its TopVia2/TopMetal1 landings in the shared C/D sampler child. No new width, via count or corridor is selected here. The measurements locate an end-to-end access difference; they do not prove that horizontal TM2 dominates it or predict the voltage recovery.

This is a docs-only plan from [actual readback proof 24f7274d](https://github.com/Melihakbulut221/nssoc/commit/24f7274d2b4e5f3445f36e7afe433b7ee39fb16c). Run 40926701777 reproduced the exact five-device extrema from both current nominal captures and authenticated all 6,765 input members per case. The underlying simulation is run 40906725656/source e1914245, whose electrical rejection remains unchanged. No geometry, source, gate, simulation or acceptance flag changes.

| Case | Selector | Native row | Time (ns) | Signed VCE (V) | Deficit to 0.4 V (mV) | Selector E minus four tail D contacts (mV) |
|---|---:|---:|---:|---:|---:|---:|
| early | 61 | 74246 | 22.43859375 | 0.347129690 | 52.870 | 76.236–76.914 |
| early | 62 | 74246 | 22.43859375 | 0.348256148 | 51.744 | 75.940–76.619 |
| early | 115 | 74225 | 22.43296875 | 0.381489006 | 18.511 | 77.274–77.934 |
| early | 116 | 74225 | 22.43296875 | 0.382784685 | 17.215 | 76.948–77.608 |
| late | 61 | 68853 | 20.81328125 | 0.342984379 | 57.016 | 76.602–77.283 |
| late | 62 | 68853 | 20.81328125 | 0.344116705 | 55.883 | 76.301–76.982 |
| late | 115 | 60145 | 18.18578125 | 0.382613492 | 17.387 | 76.760–77.430 |
| late | 116 | 60145 | 18.18578125 | 0.383735272 | 16.265 | 76.439–77.108 |

At the early device61 witness, selector C/E are 0.863422707/0.516293017 V and Ic is 2.914094 mA. Upper sampler54/56 emitter-to-selector-C differences are 40.152/51.747 mV. At that same row, the two CN selector emitters are near 0.516 V, the two CP selector emitters near 0.492–0.494 V, and the four tail drains near 0.439–0.440 V. The current shared-child spatial order is CN contacts, CP contacts, then tail contacts.

These are distinct contacts on one extracted conductor, not ideal aliases. The JSON retains their simultaneous signed voltages, currents, native row/time and exact current device/net bindings. HBT Ie/Ib, internal wire-node voltages, resistor branch currents and complete dynamic KCL are unavailable. In particular, dividing the 76–78 mV contact difference by one selector Ic does **not** establish a TM2 resistance.

The geometry scope is precise:

- D M_TE: native cluster **28/$131**, component17, selectors61/62 and64/65 E plus MOS3–6 D.
- C M_TE: **124/$680**, component61, selectors115/116 and118/119 E plus MOS32–35 D.
- D/C M_SE collector partitions are **38/$149** and **134/$698**. They remain unchanged in the first candidate. The old C label136/$708 must not be reused.
- Gain60 E is **14/$66**, C is **22/$99**; both remain unchanged. Its maximum |VCE| is **1.575522964 V early / 1.574658191 V late**, leaving only 24.477/25.342 mV to 1.6 V. Separate metal ownership is not circuit isolation: gain60 C shares a conductor with upper sampler54 B.

The normalized child is 'pd_child_sampler_cd', 0.001 µm/DBU. Existing lower bridge box is **(370000,174430)–(1041525,177630) DBU**: 3.2 µm wide and 671.525 µm long. Its eight landing centers are at y=176030 and x=371000,439805,636555,686205,878815,925320,990875,1040525. The child origin translation is (0,−3970) DBU.

| Placement | Translation (DBU) | Existing lower bridge box (DBU) | Landing y (DBU) |
|---|---|---|---:|
| D / sd | (993600,272000) | (1363600,446430)–(2035125,449630) | 448030 |
| C / sc | (993600,1461520) | (1363600,1635950)–(2035125,1639150) | 1637550 |

The current graph has **two** TM2 polygons per M_TE partition; the original higher bridge remains a parallel path. Existing landing source parameters are TopMetal1→TopMetal2 with one TopVia2 row/column. The previous 26 child boxes widened M4/TM1 vertical columns only. Original 0.4 µm lower-metal pin escapes, their vias, the TM2 bridges and distributed capacitance may share or dominate the observed access difference.

Exact existing construction is in [tail access plan](https://github.com/Melihakbulut221/nssoc/blob/24f7274d2b4e5f3445f36e7afe433b7ee39fb16c/scripts/cdr_v59_tail_access_plan.py#L15) and [native union/ownership generator](https://github.com/Melihakbulut221/nssoc/blob/24f7274d2b4e5f3445f36e7afe433b7ee39fb16c/scripts/generate_cdr_v59_tail_access_wire.py#L131). These are reference sources, not authorization to replay historical admissions on a changed candidate. The current geometry is GDS **fb8a0aea…** and LVS **46f7b577…**, with 500 devices, 1,446 terminals, 113 components and 25 ports.

The actual RC report binds extraction tech **650b16fb…**, via Tcl **0dc8ec12…**, resistor Tcl **2a89b7aa…**, Magic runtime **e8f2d961…**, and exact extracted network **c53a4b2c…**. The JSON lists their complete paths/sizes/SHA256 values. It authenticates 24,341 exported wire resistors and 15,559 wire capacitors (24,356 R/15,566 C with intrinsic resistors and seven MIM devices). The reviewed direct report does **not** expose numerical TM2 sheet/contact/via coefficients or per-edge resistance values, so no generic process values or claimed dominant resistance are substituted. Point attachment/RF distribution, substrate R and full PEX remain unqualified.

The next bounded action is a reserved, cloud-only feasibility readback of exact current material, via shapes and relevant extracted resistance paths. A wider additive union or parallel bridge with adequate legal landings is eligible for consideration only after full-parent foreign-metal/via/enclosure/spacing checks. Preserve all original material, devices, resistor/bias/clock values, LP/LN, AVSS, public ports and every other partition. If no legal corridor exists, record that failure.

Any subsequently authorized candidate still needs fresh serialized reread, DRC/LVS, exact full identity/partition proof, RC/MIM and the original ten loaded cases. The sampler37.5 ps/comparator75 ps/UI125 ps/100 mV gates and HBT0.4–1.6 V bounds remain unchanged. Neither nominal contact readback qualifies cold gain, hot feedback, data/phase behavior or the full PHY.

The companion [JSON](./cdr-current-contact-repair-plan-20261029.json) contains the ten full focus-device scalar projections, selected shared-contact rows, source/input identities and explicit limitations. No native payload was acquired locally; no authored test, simulation or geometry operation ran for this plan.
