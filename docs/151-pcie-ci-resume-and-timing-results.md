# 151 — PCIe simulation recovery and completed timing attempts
<!-- SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut -->
<!-- SPDX-License-Identifier: CC-BY-4.0 -->

## Local repair — 7 October 2026

All eleven RTL suites that failed in [checks run 37446811365](https://github.com/Melihakbulut221/nssoc/actions/runs/37446811365) now pass locally using Icarus 12.0: **63 port scenarios, zero failures and zero skips**. The [evidence inventory](../hw/soc/pcie-evidence/20261007-ci-resume/inventory.json) records exact tested sources, original sources, simulator logs and XML counts. The complete GitHub workflow still needs its new run; these results cover the eleven affected suites.

Five RX-events Makefiles omitted their instantiated consumer, owned receiver, framer, ingress and descrambler dependencies. Their default source lists now include the same modules used by the existing dedicated checkers. A caller can still override the list for a deliberate mutation.

The other six suites timed out in the V5/V6 DLLP consumer or its wrappers. A procedural index into the shared body-context array made Icarus subscribe a combinational block to its own output. Intermediate blocking assignments then kept scheduling delta cycles. The gather now uses a static, earlier-lane-only mux chain before the existing update block. Last matching earlier owner retains priority; case equality preserves the old procedural `if` behavior when a match is unknown. No pipeline register, latency or interface changes were added.

The initial focused regression passed 28 checks and failed four host-side mutation selectors because they still named the removed procedural loop. Those failures remain in the packet. The four selectors were updated to inject the same missing-forward, immediate-only and reversed-priority faults into the mux chain; all four now provoke the required functional rejection. **All 32 current regression predicates are accounted for.** This includes the existing 2,560-vector arbitrary-prestate comparison, public-port comparisons and deliberate faults; it is finite verification, not a complete formal proof.

## Results recovered after restart

The old processes finished before the new boot. Their terminal records supersede earlier running checkpoints; no old PID was reused.

| Experiment | Completed measurement | Remaining limit |
| --- | --- | --- |
| Main-chip post-global-route repair | Setup endpoints 1,334 → 952; hold endpoints 6,200 → 15; slew 512 → 39; capacitance 168 → 9 | Setup WNS −1.711429 ns and hold WNS −0.799323 ns; global-route estimate only |
| PCIe RX18 detailed route and nominal RC | Slow setup −0.286829 ns; hold +0.026676 ns | Setup still fails; RC is not qualified for signoff |

The [post-route-stage record](../hw/soc/pcie-evidence/20261007-ci-resume/npu-postgrt-result.json) retains missing SRAM timing models and constraint limitations in its original scope. The [RX18 continuation record](../hw/soc/pcie-evidence/20261007-ci-resume/rx18-continuation-result.json) retains its exact stage and release bindings. Neither candidate is declared accepted for the complete product. The RTL changes above also require fresh physical validation before any prior layout result could apply to them.

The full-metal supply extraction in [run 37418263739](https://github.com/Melihakbulut221/nssoc/actions/runs/37418263739) was cancelled while extracting connectivity. Its preserved [partial record](../hw/soc/pcie-evidence/20261007-ci-resume/supply-artifact/extraction/result.json) is not an LVS pass. Complete PHY operation, qualified SRAM/RC, final chip timing, I/O transistor LVS and manufacturing approval remain open.
