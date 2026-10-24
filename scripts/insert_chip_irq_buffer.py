#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Insert a noninverting native buffer in the mapped chip IRQ input path.

The core and pad instances are unchanged. This netlist ECO needs fresh routing,
native antenna/DRC, extracted connectivity and timing checks before acceptance.
"""
import re

CELL = "u_irq_antenna_buffer"
NET = "irq_external_buffered"
INSERTION = (f"  wire {NET};\n"
             f"  sg13g2_buf_16 {CELL} (.A(irq_external_i), .X({NET}));\n")


def insert_buffer(source):
    if CELL in source or NET in source:
        raise ValueError("IRQ buffer already present or name collision")
    if len(re.findall(r"\bmodule\s+nssoc_chip\b", source)) != 1 or source.count("endmodule") != 1:
        raise ValueError("Expected one mapped chip module")
    cores = list(re.finditer(r"\bsoc_top\s+u_core\s*\((.*?)\);", source, re.S))
    if len(cores) != 1:
        raise ValueError("Expected exactly one mapped core")
    core = cores[0]
    port = ".irq_external_i(irq_external_i)"
    if core[0].count(port) != 1:
        raise ValueError("Unexpected original IRQ core connection")
    pads = re.findall(r"\bsg13g2_IOPadIn\s+u_pad_irq_external_i\s*\((.*?)\);", source, re.S)
    if len(pads) != 1 or pads[0].count(".p2c(irq_external_i)") != 1:
        raise ValueError("Unexpected IRQ pad connection")
    updated = core[0].replace(port, f".irq_external_i({NET})")
    result = source[:core.start()] + updated + source[core.end():]
    result = result.replace("endmodule", INSERTION + "endmodule")
    # Removing exactly the ECO must recover every original source byte.
    restored = result.replace(INSERTION, "").replace(f".irq_external_i({NET})", port)
    if restored != source:
        raise ValueError("Unexpected non-ECO netlist change")
    return result
