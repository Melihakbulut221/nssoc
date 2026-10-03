<!-- SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut -->
<!-- SPDX-License-Identifier: CC-BY-4.0 -->
# Historical synthesis reference

`apb_timeout_disabled_293d9a5.v` is the byte-identical APB bridge from
commit `293d9a5e7da6bbaa2e1d671001a0aad7f8f557fb`, before timeout support.
Its SHA256 is `6b9b092d3e82bf5df4fff9b1a5389403ac99f0a86538087a1575ba06efc22d85`.
The original CERN-OHL-W-2.0 header is retained. This is a regression fixture,
not another production module or an alternative SoC implementation.

The synthesis guard maps this reference and the current timeout-disabled
bridge using the same Yosys, Liberty and recipe. Both must have identical
state and total cell counts; enabling timeout must add state. The historical
0.33 measurement remains 93 flops / 193 cells; pinned 0.67+146 produces
94 / 191 for both reference and current sources. Source integrity is checked
before use, including in archives without Git history.
