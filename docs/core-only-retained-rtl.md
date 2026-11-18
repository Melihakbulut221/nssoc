# Retained RTL regression scope

COCOTB_RELEASE_PROFILE=core-only scripts/run_cocotb.sh runs the retained non-frozen component RTL suites using the existing strict command-status/fresh-XML collector. Default invocation remains the full repository regression. The fixed inventory covers every Makefile and test module in hw/tb and hw/soc/tb/cocotb; unknown, deleted, duplicate, overlapping or misclassified entries fail before simulation. No partial filter is allowed in the release profile.

PCIe and Ethernet files explicitly excluded by the approved product scope are reported OUT_OF_RELEASE, never passed or counted as skipped simulator tests. Frozen pilot gate/fault campaigns and native SRAM parity retain their existing separate qualification requirements. The Tiny Tapeout RTL suite and retained defect/strap modules remain selected. Existing legacy guarded PCIe packages are not repinned or modified.

This is retained component regression, not proof of full physical-release integration: those require the real core-only netlist boot/MBIST, mapped interface inventory, and later padframe/routed checks. Any reported skips, separate jobs or unavailable frozen artifacts remain visible and cannot be treated as completed production gates. Clock, layout, DRC/LVS and manufacturer acceptance are independent.

## Verified cloud result, 18 November 2026

[Run44246945276](https://github.com/Melihakbulut221/nssoc/actions/runs/44246945276), sourcece3b42e6e475d264112612b4f685006c6e587920: native XML independently confirms **483 passed, 0 failed, 21 skipped**, runner **0 unclean suites**. The runner's22nd skip is the explicit separate native RAM-parity job. 88 suite Makefiles and90 modules are outside the approved PCIe/Ethernet scope; they are not passes. Artifact14403090390 SHA256 be60878bf9f4141d5c5e2166bec6765f11874687717d602c73be40e9c095a5d9 was independently verified.

All21 XML skips have named passing counterparts:15 SECDED/TMR cases in other parameter variants of the same run, six CAN/SpaceWire cases in full interface run44247358676. These are coverage bindings, not edits to native skip counts. See evidence/core-only-retained-rtl-20261118.json.

The separate native RAM-parity job134584352502 in run44239723467 passed six geometry/latency/hardening profiles; a deliberately corrupted macro failed its one test, as required. Artifact14399535279 SHA256 ddf71e20219f0ffb6f1c364097e93fe53a2448a6d1088884dc8274eaa6b2b793 and native XML/results were independently checked. All eight recorded tracked source/test/driver hashes match the current branch; vendor model hashes remain explicitly recorded. See evidence/core-only-memory-parity-binding-20261118.json. This establishes bus-parity behavior, not macro transistor LVS, Liberty, ROM initialization or mapped whole-chip boot. Frozen campaigns, physical/DFT/manufacturing gates are not closed by these component totals. The parent whole CI run still has unrelated failed and running jobs and is not a broad PASS.
