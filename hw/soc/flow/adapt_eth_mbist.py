# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Guarded adaptation of the pinned upstream FIFO, without editing its checkout.

Only the 2048-word, <=16-bit FRAME_FIFO profile is admitted with SOC_ETH_MBIST.
The SRAM read replaces pipeline stage zero, preserving its one-edge latency.
The legacy preprocessor branch remains exactly the inferred-memory design.
With SOC_ETH_FIFO_RDREG (docs/combined-timing.md) the FIFO runs with two RAM
pipeline stages and the wrapper's registered read port is stage one; its load
enable is the pinned pipeline's own stage-one enable.
"""

def replace(text, old, new, count=1):
    if text.count(old) != count:
        raise ValueError('Ethernet MBIST adaptation anchor changed: '+old[:80])
    return text.replace(old, new)


def adapt(name, text):
    if name not in ('eth_mac_1g_fifo.v', 'axis_async_fifo_adapter.v', 'axis_async_fifo.v'):
        return text
    vector = '[1:0] ' if name == 'eth_mac_1g_fifo.v' else ''
    ports = (f'`ifdef SOC_ETH_MBIST\n    input wire mbist_por_ni,\n'
             f'    output wire {vector}mbist_done_o, mbist_failed_o,\n`endif\n')
    text = replace(text, ')\n(\n', ')\n(\n'+ports)
    if name == 'eth_mac_1g_fifo.v':
        for instance, index in (('tx_fifo', 0), ('rx_fifo', 1)):
            text = replace(text, instance+' (\n', instance+' (\n'+
                '`ifdef SOC_ETH_MBIST\n    .mbist_por_ni(mbist_por_ni),\n'+
                f'    .mbist_done_o(mbist_done_o[{index}]), .mbist_failed_o(mbist_failed_o[{index}]),\n`endif\n')
    elif name == 'axis_async_fifo_adapter.v':
        text = replace(text, ')\nfifo_inst (\n', ')\nfifo_inst (\n'+
            '`ifdef SOC_ETH_MBIST\n    .mbist_por_ni(mbist_por_ni),\n'+
            '    .mbist_done_o(mbist_done_o), .mbist_failed_o(mbist_failed_o),\n`endif\n')
    else:
        decl = 'reg [WIDTH-1:0] mem[(2**ADDR_WIDTH)-1:0];'
        text = replace(text, decl, '`ifndef SOC_ETH_MBIST\n'+decl+'\n`endif')
        decl = 'reg [WIDTH-1:0] m_axis_pipe_reg[RAM_PIPELINE+1-1:0];'
        text = replace(text, decl, '''`ifdef SOC_ETH_MBIST
wire [WIDTH-1:0] m_axis_pipe_reg[RAM_PIPELINE:0];
reg [WIDTH-1:0] mbist_pipe_reg[RAM_PIPELINE:1];
wire [15:0] mbist_rdata;
// Same write predicate as the pinned FRAME_FIFO branch; no extra register.
wire mbist_wr = s_axis_tready && s_axis_tvalid &&
    !((full && DROP_WHEN_FULL) || (full_wr && DROP_OVERSIZE_FRAME) || drop_frame_reg);
wire mbist_rd = m_axis_tready_pipe || |(~m_axis_tvalid_pipe_reg);
`ifdef SOC_ETH_FIFO_RDREG
// Stage one loads when the pinned loop loads it: output ready, or a bubble
// at stage one or above.
wire mbist_rd1 = m_axis_tready_pipe || |(~m_axis_tvalid_pipe_reg[RAM_PIPELINE:1]);
if (ADDR_WIDTH != 11 || WIDTH > 16 || !FRAME_FIFO || RAM_PIPELINE < 2) begin
    SOC_ETH_FIFO_RDREG_requires_2048x16_frame_fifo_with_two_ram_stages invalid_mbist_fifo();
end
`else
if (ADDR_WIDTH != 11 || WIDTH > 16 || !FRAME_FIFO || RAM_PIPELINE < 1) begin
    SOC_ETH_MBIST_requires_2048x16_frame_fifo invalid_mbist_fifo();
end
`endif
soc_eth_fifo_sram u_sram (
    .wclk_i(s_clk), .rclk_i(m_clk), .por_ni(mbist_por_ni),
    .wreset_i(s_rst), .rreset_i(m_rst), .wen_i(mbist_wr), .ren_i(mbist_rd),
`ifdef SOC_ETH_FIFO_RDREG
    .rnext_i(mbist_rd1),
`endif
    .waddr_i(wr_ptr_reg[10:0]), .raddr_i(rd_ptr_reg[10:0]),
    .wdata_i({{(16-WIDTH){1'b0}},s_axis}), .rdata_o(mbist_rdata),
    .done_o(mbist_done_o), .failed_o(mbist_failed_o));
`ifdef SOC_ETH_FIFO_RDREG
// Stage zero is the macro itself; stage one is the wrapper's register.
assign m_axis_pipe_reg[0] = mbist_rdata[WIDTH-1:0];
assign m_axis_pipe_reg[1] = mbist_rdata[WIDTH-1:0];
for (genvar mbp=2; mbp<=RAM_PIPELINE; mbp=mbp+1) begin: g_mbist_pipe
    assign m_axis_pipe_reg[mbp] = mbist_pipe_reg[mbp];
end
`else
assign m_axis_pipe_reg[0] = mbist_rdata[WIDTH-1:0];
for (genvar mbp=1; mbp<=RAM_PIPELINE; mbp=mbp+1) begin: g_mbist_pipe
    assign m_axis_pipe_reg[mbp] = mbist_pipe_reg[mbp];
end
`endif
`else
'''+decl+'\n`endif')
        assignment = 'mem[wr_ptr_reg[ADDR_WIDTH-1:0]] <= s_axis;'
        text = replace(text, assignment, '\n`ifndef SOC_ETH_MBIST\n'+assignment+'\n`endif\n', 4)
        assignment = 'm_axis_pipe_reg[j] <= m_axis_pipe_reg[j-1];'
        text = replace(text, assignment, '`ifdef SOC_ETH_MBIST\n            mbist_pipe_reg[j] <= m_axis_pipe_reg[j-1];\n`else\n'+assignment+'\n`endif')
        assignment = 'm_axis_pipe_reg[0] <= mem[rd_ptr_reg[ADDR_WIDTH-1:0]];'
        text = replace(text, assignment, '`ifndef SOC_ETH_MBIST\n'+assignment+'\n`endif')
    if name == 'axis_async_fifo.v':
        # SOC_ETH_FIFO_WRREG (docs/combined-timing.md section 16): the SRAM
        # wrapper writes a word one write-clock edge after the pinned loop's
        # write, so the frame commit is published to the read side one edge
        # later as well: the read domain samples a registered copy of the
        # commit toggle, which changes at the edge that writes the frame's
        # last word. The read domain can then never see a commit before the
        # data under it is written, at any clock ratio. The toggle itself and
        # the write side's handshake check are unchanged; the acknowledge
        # returns one write-clock cycle later.
        text = replace(text, '\n// pointer synchronization\n', '''
`ifdef SOC_ETH_MBIST
`ifdef SOC_ETH_FIFO_WRREG
reg mbist_update_published = 1'b0;
always @(posedge s_clk) begin
    mbist_update_published <= wr_ptr_update_reg;
    if (s_rst) begin
        mbist_update_published <= 1'b0;
    end
end
`endif
`endif

// pointer synchronization
''')
        assignment = '    wr_ptr_update_sync1_reg <= wr_ptr_update_reg;\n'
        text = replace(text, assignment, '`ifdef SOC_ETH_MBIST\n`ifdef SOC_ETH_FIFO_WRREG\n'
                       '    wr_ptr_update_sync1_reg <= mbist_update_published;\n`else\n'+assignment+
                       '`endif\n`else\n'+assignment+'`endif\n')
        # Icarus with default_nettype none requires declarations before use.
        start = text.index('// Same write predicate')
        end = text.index('`else\nreg [WIDTH-1:0] m_axis_pipe_reg', start)
        block = text[start:end]
        text = text[:start] + text[end:]
        text = replace(text, '\nendmodule', '\n`ifdef SOC_ETH_MBIST\n'+block+'`endif\nendmodule')
    return text
