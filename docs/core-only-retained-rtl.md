# Retained RTL regression scope

COCOTB_RELEASE_PROFILE=core-only scripts/run_cocotb.sh runs the retained non-frozen component RTL suites using the existing strict command-status/fresh-XML collector. Default invocation remains the full repository regression. The fixed inventory covers every Makefile and test module in hw/tb and hw/soc/tb/cocotb; unknown, deleted, duplicate, overlapping or misclassified entries fail before simulation. No partial filter is allowed in the release profile.

PCIe and Ethernet files explicitly excluded by the approved product scope are reported OUT_OF_RELEASE, never passed or counted as skipped simulator tests. Frozen pilot gate/fault campaigns and native SRAM parity retain their existing separate qualification requirements. The Tiny Tapeout RTL suite and retained defect/strap modules remain selected. Existing legacy guarded PCIe packages are not repinned or modified.

This is retained component regression, not proof of full physical-release integration: those require the real core-only netlist boot/MBIST, mapped interface inventory, and later padframe/routed checks. Any reported skips, separate jobs or unavailable frozen artifacts remain visible and cannot be treated as completed production gates. Clock, layout, DRC/LVS and manufacturer acceptance are independent.
