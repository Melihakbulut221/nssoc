# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Observe sent-credit snapshots on every cycle around a stalled final byte."""

import cocotb
from test_soc_pcie_fc_tx import Bench


@cocotb.test()
async def sent_limits_change_only_when_final_byte_is_accepted(d):
    b = Bench(d)
    await b.reset()
    for _ in range(20):
        assert b.v("sent_header_o") == 0
        assert b.v("sent_data_o") == 0
        assert not b.v("sent_valid_o")
        if b.v("tx_valid_o") and b.v("tx_eop_o"):
            break
        await b.tick(tx_ready_i=1)
    else:
        raise AssertionError("First FC advertisement did not reach EOP")

    assert len(b.current) == 5 and not b.frames
    for _ in range(4):
        await b.tick(tx_ready_i=0)
        assert b.v("tx_valid_o") and b.v("tx_eop_o")
        assert b.v("sent_header_o") == 0
        assert b.v("sent_data_o") == 0
        assert not b.v("sent_valid_o")
        assert not b.frames and not b.commits

    await b.tick(tx_ready_i=1)
    assert b.frames == [(0, 0, 2, 4)]
    assert b.commits == [(0, 0)]
    assert b.v("sent_header_o") == 2 and b.v("sent_data_o") == 4
    assert b.v("sent_valid_o")

    await b.tick(tx_ready_i=0)
    assert b.v("sent_header_o") == 2 and b.v("sent_data_o") == 4
    assert not b.v("sent_valid_o")
