# Slew regression parasitic evidence and next route candidate — 2026-11-19

Run 44471064250, head 865c20a035280ecdf1703a221286ace626ab0f80, attempt 1 succeeded. Artifact 14503484962 SHA256 eb985b168d9377615092a3a58b9175b5856e62dd40b37ae09c1fdfc022b92d9c; all 128 outputs verified. Baseline and slew source SPEFs are 506a2e1c77670c6d69a944def37eb2ac36944502693b0251aa1b68abdad9044a and 5cb8407b9bf2cf7431eb8005ce9778704e0e4f43ad2ba014644470b48987a174. Units are 1 pF / 1 ohm.

The three newly violating output nets retain identical resolved resistance records but larger declared total wire capacitance:

| Net (prefix nssoc_sta_n_) | Baseline pF | Slew pF |
|---|---:|---:|
| 55232 | 0.184612 | 0.213061 |
| 54157 | 0.158286 | 0.178252 |
| 58480 | 0.0776768 | 0.100419 |

Exact newly added coupling entries include 55164:14 to 55232:40 = 0.0391402 pF, 55164:14 to 58480:12 = 0.0385722 pF, 55165:106 to 55232:50 = 0.00713919 pF, 54157:117 to 56323:12 = 0.0219656 pF, and net4410:53 to 54157:117 = 0.00982843 pF. All four aggressor nets (55164,55165,56323,net4410) belong to the 18-net route candidate. Other nodes on these nets also contribute. This supports increased routed coupling as the next correction target; it is not proof that all input-slew effects are absent.

Input SPEF blocks net3463,net3900,net4881,54156,55230,55231,58475 are byte-identical after name resolution. Other 57755 input nets have tiny capacitance differences, with identical resistance records. An exploratory summary used the second coupling endpoint as a partner, producing apparent self-partners. Do not use that summary as physical partner attribution: exact two-endpoint entries above were independently compared and are the evidence.

Next candidate: keep the three NOR resizes and clean preparation, same 18-net allowed reroute set and fixed clocks. Apply spacing-only nondefault routing rules to the four proven aggressors, verify rule assignments and widths with the pinned native OpenROAD, then route and require unchanged other nets, independent geometry, antenna and DRC. Fresh RC must prove coupling reduction and all-corner electrical/timing behavior. No limit relaxation, buffer invention, or production promotion is authorized by this result.

Pinned OpenROAD dcf36133a369abc8f3c5e5738cd4d82e4903c0e0 contains examples for create_ndr -spacing { metal1:metal5 *3 } and assign_ndr -ndr NDR -net clk in [src/odb/test/ndr.tcl](https://github.com/The-OpenROAD-Project/OpenROAD/blob/dcf36133a369abc8f3c5e5738cd4d82e4903c0e0/src/odb/test/ndr.tcl). Native rule and routing validation remains required before claiming spacing is realized. No NDR route has been dispatched yet. Nominal setup/hold remains zero in run44468611583; electrical and full production signoff remain open.
