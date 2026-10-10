# Changelog
<!-- SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut -->
<!-- SPDX-License-Identifier: CC-BY-4.0 -->

## Unreleased — development through 21 September 2026

This is a change index, not a product release. Paper tags preserve publication
snapshots. See [HISTORY.md](HISTORY.md) and the [errata index](docs/ERRATA.md)
for retained measurements and corrections.

- Added explicit base/full interface profiles. SpaceWire and classic CAN are
  optional LGPL dependencies; SPI, I2C and the Gigabit GMII MAC have recorded
  RTL/CPU checks. PCIe Gen3 x4 remains unresolved.
- Added UART 8N1 receive, interrupt and WFI checks; shared bare-metal HAL;
  transport-independent pilot driver; thirteen generated register maps.
- Added hardware CI, source-bound formal inventory, native SRAM parity,
  mapped UART tests, exact whole-SoC lint inventories and required regression
  tasks that the earlier Makefile omitted.
- Added pinned digital/physical tool installers and project-local tool defaults.
  Physical bootstrap and final timing/LVS acceptance remain incomplete.
- Added checked documentation assets/API pages, an actual-output CI gate,
  generated status/licence inventories and a reconciled current datasheet.
- Added contribution/security guidance, issue/PR templates, Python development
  checks and golden-model annotations. Fixed undefined diagnostic names in
  three netlist-guard failure paths.

The [first review/product register](docs/92-product-acceptance.md) and
[second audit register](docs/96-second-audit-closure.md) define the remaining
work and link measured results. No feature above implies silicon, radiation,
external-PHY, package or complete physical qualification.
