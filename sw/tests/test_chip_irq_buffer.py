# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Keep the antenna ECO confined to the physical chip IRQ path."""
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
from insert_chip_irq_buffer import INSERTION, insert_buffer

SOURCE = """module nssoc_chip;
wire irq_external_i;
soc_top u_core (.irq_external_i(irq_external_i), .clk_i(clk_i));
sg13g2_IOPadIn u_pad_irq_external_i (.p2c(irq_external_i), .pad(pad_irq_external_i));
endmodule
"""


def test_only_core_irq_connection_and_one_buffer_are_added():
    result = insert_buffer(SOURCE)
    assert result.count("sg13g2_buf_16") == 1
    assert result.replace(INSERTION, "").replace(
        ".irq_external_i(irq_external_buffered)", ".irq_external_i(irq_external_i)") == SOURCE


@pytest.mark.parametrize("source", [
    SOURCE.replace("u_core", "other_core"),
    SOURCE.replace(".irq_external_i(irq_external_i)", ".irq_external_i(wrong)"),
    SOURCE.replace(".p2c(irq_external_i)", ".p2c(wrong)"),
    SOURCE + "module extra; endmodule\n",
    SOURCE.replace("endmodule", "wire irq_external_buffered; endmodule"),
])
def test_changed_source_or_collision_is_rejected(source):
    with pytest.raises(ValueError): insert_buffer(source)


def test_reapplying_eco_is_rejected():
    with pytest.raises(ValueError): insert_buffer(insert_buffer(SOURCE))
