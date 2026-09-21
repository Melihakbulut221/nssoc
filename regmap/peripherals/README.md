# Peripheral register generation
<!-- SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut -->
<!-- SPDX-License-Identifier: Apache-2.0 -->

Each YAML file owns the word register offsets of one implemented SoC block.
`memmap.yaml` still owns the slot bases; the frozen pilot's `regmap.yaml` and
its RTL are independent and unchanged.

Run from the repository root using an environment with PyYAML:

```sh
python3 regmap/generate_peripherals.py
python3 regmap/generate_peripherals.py --check
python3 -m pytest -q sw/tests/test_peripheral_regmap.py
```

The generator updates existing RTL `localparam` declarations in place, emits
`hw/soc/tb/sw/soc_reg_offsets.h`, and emits
`sw/golden/peripheral_regs_gen.py`. The cocotb helper imports those Python
maps; firmware headers retain their existing public absolute-address aliases.
No new RTL include search path is needed. The local CI generator gate and
pytest both require fresh outputs.

A schema-1 file has `block`, `base`, `address_bits` and `registers` fields.
`block` must match the filename. Each register has its integer byte `offset`
and existing `rtl` declaration name. Offsets must be aligned, unique and
representable; duplicate YAML keys or RTL names, missing/duplicate decoder
bindings and orphan markers are errors. The NPUCFG block binds to `soc_npu.v`.
Generation changes only marked constants, not register behavior or fields.

The first migration covers 105 offsets across BOOT, BUSSTAT, CLINT, Ethernet,
GPIO, I2C, NPUCFG, QSPI, SCRUB, SPI, SpaceWire and UART. An independent digest
of the pre-migration offset map guards compatibility even if all generated
outputs change together. A deliberate ABI change needs an explicit review of
that guard and firmware compatibility.

GPTIMER's parameter-dependent timer/watchdog layout and the upstream CAN
controller's banked byte map remain outside this first migration. Bit fields,
access behavior, the common HAL and complete auxiliary-test deduplication also
remain work items in audit 3.8. Reserved/unimplemented offsets in negative tests
are deliberately independent. This tooling does not establish protocol or
physical compliance.
