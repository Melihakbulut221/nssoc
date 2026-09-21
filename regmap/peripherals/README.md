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

GPTIMER now adds four global offsets and four window-relative offsets, for
13 blocks and 113 offsets. Its optional `window` defines `name`, `stride`,
`rtl_stride` and `registers`. The stride is a power-of-two byte count; globals
occupy the prefix below that stride. Window registers use byte offsets in
C/Python and word selectors in RTL. The timer index and watchdog status
address remain derived from the stride and the existing `NGEN` parameter.
Independent C assertions and unchanged formal properties guard the shipped
timer/watchdog ABI.

The upstream CAN controller's banked byte map remains pending. Bit fields,
access behavior and complete auxiliary-test deduplication also remain work
items in audit 3.8. Common access and console operations are now provided by
the [bare-metal HAL](../../hw/soc/tb/sw/lib/README.md).
Reserved/unimplemented offsets in negative tests
are deliberately independent. This tooling does not establish protocol or
physical compliance.
