# Errata and superseded claims
<!-- SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut -->
<!-- SPDX-License-Identifier: CC-BY-4.0 -->

Updated 21 September 2026. This index points to the dated corrections that own
the evidence. It does not erase the original statements, turn a failed result
into a pass, or declare the product accepted. The current implementation
contract is [datasheet section 0.4](60-soc-datasheet.md); all remaining product
requirements stay in [the acceptance register](92-product-acceptance.md).

| Earlier statement or misleading inference | Applicable correction | Evidence / reproduction entry point |
|---|---|---|
| A zero-derate timing pass closes the required derated design | Withdrawn. The required derating and actual setup/hold/electrical failures remain binding. Global-route estimates do not replace final extracted acceptance. | [Derate correction](evidence/logicrom-derate-correction-20260920.json), [derate guard](evidence/native-derate-guard-20260920.json), [current acceptance](92-product-acceptance.md) |
| A zero-marker KLayout result proves the complete chip is clean | Deck, hierarchy and revision matter. Native Magic macro-interior errors and SRAM-interior LVS remain open even when another deck passes. | [DRC update](93-ihp-drc-update.md), [SRAM transistor LVS](evidence/sram-transistor-lvs-20260920.json), [native Magic record](evidence/halo-lift3-magic-20260921.json) |
| FPGA-style initialization is sufficient for native ASIC startup | Withdrawn. Native-cell simulation exposed unknown state. The design uses explicit reset/startup initialization and a compiled immutable loader; each image needs its own acceptance. | [Immutable ROM](95-immutable-boot-rom.md), [NPU startup result](evidence/npu-native-startup-20260921.json), [hosted native full-profile result](evidence/hosted-native-interfaces-20260921.json) |
| Abstract-codec scrub proof closes the whole core's register property | Incorrect scope. Real-codec contract/equivalence, abstract-codec scrub and whole-core RVFI are distinct obligations; M-extension and whole-core register closure remain open. | [Formal bring-up](63-riscv-formal-bringup.md), [engineering closure](87-engineering-closure.md), [completed local abstract tasks](evidence/formal-scrub-invocation-20260921.json) |
| A formal sweep with passing discovered outputs is complete | Every mandatory declared task must be invoked and have a fresh-source verdict. Missing tasks remain failures, never silent passes. | [Hosted inventory failure](evidence/hosted-formal-inventory-20260921.json), `python3 scripts/check_formal_sweep.py` on a fresh prepared checkout |
| SoC features are the old datasheet's UART-TX-only/no-interface/no-gating configuration | Superseded by current UART RX, optional SpaceWire/CAN, SPI/I2C, GMII Ethernet, clock gates, telemetry and shared HAL. RAM capacity and register-codec width also changed or were misstated. | [Current datasheet](60-soc-datasheet.md), [generated memory map](memmap-soc.md), [UART contract](97-uart-receive.md) |
| An Ethernet loopback proves an external PHY or arbitrary clock-domain integration | It proves the stated packet/CPU path under its recorded testbench clocks. The external PHY, asynchronous-clock qualification and final pad timing remain open. | [Ethernet integration and limits](90-gigabit-ethernet.md) |
| PCIe candidate research or a PIPE port constitutes Gen3 x4 hardware | No complete compatible controller/PHY is instantiated. The original requirement remains open. | [PCIe dependency assessment](91-pcie-gen3-feasibility.md) |
| The base build silently includes LGPL interface IP | Corrected through explicit base/full profiles, preserved licence decision and upstream notices. A base profile does not instantiate SpaceWire/CAN. | [Interface profile evidence](evidence/interface-profiles-20260921.json), [licence decision](14-licensing-decision.md) |
| Local CI runs every hosted hardware job | Incorrect. The local front door and separately invoked hosted hardware/native jobs have distinct commands, preparation and skip conditions. | [Second-audit item 1.4 and CI work](96-second-audit-closure.md), `.github/workflows/checks.yml` |
| Zero unresolved prose references proves every documentation link works | Incorrect. Explicit file links previously escaped the check. Assets/API pages are now published and emitted file targets checked. The first corrected builder also exposed a stale CI page-count gate; that failure is retained. | [File-target correction](evidence/document-site-links-20260921.json), [CI gate failure and correction](evidence/document-site-ci-gate-20260921.json), `bash scripts/ci_local.sh docs` |
| Original README claims disappear when the front page is shortened | The original body remains in HISTORY.md. The front page's measured status is generated from explicitly selected evidence hashes. | [History](../HISTORY.md), [status selection](status-sources.json), `python3 scripts/project_status.py` |

The detailed historical reconciliations remain [docs/64](64-document-reconciliation.md),
[datasheet section 14](60-soc-datasheet.md) and [the external-review record](86-the-external-review.md).
A correction should name the affected revision, retain the failed or superseded
evidence, give its replacement command/artifact and state what remains outside
that replacement's scope.
