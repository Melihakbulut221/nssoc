# Frozen pilot physical configurations
<!-- SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut -->
<!-- SPDX-License-Identifier: CC-BY-4.0 -->

The [pilot freeze contract](../../docs/34-pilot-freeze.md) controls these files.
This index adds documentation; it does not move, regenerate or edit a frozen
configuration. Whole-SoC physical work uses [hw/soc/pnr](../soc/pnr/README.md).

| Location | Purpose |
|---|---|
| `pilot_ihp/config.signoff-6x2.json` | Hash-pinned pilot signoff input identified by `pilot_ihp/mkconfig.py`; acceptance is limited to its recorded pilot image |
| `../../tt/src/config.json` | Separate Tiny Tapeout submission configuration |
| `pilot_ihp/config.tr*.json` | Retained timing experiments, including delay, TDP, margin and post-route variants; not interchangeable with the submitted configuration |
| `pilot_sky130/config*.json` | Historical cross-PDK experiments; some require the ignored Tiny Tapeout support checkout and its DEF template |
| `sram_pilot/` | SRAM integration experiments, not the current complete SoC |
| `aer_fifo/` | Standalone FIFO physical trials and their checker evidence |

An old or unreferenced experiment is retained because historical measurements
and the freeze may refer to its exact bytes. None is promoted to a new product
signoff by its filename. Restore the matching dependencies and recorded input
hashes before replaying it.
