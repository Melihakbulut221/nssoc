// SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
// SPDX-License-Identifier: CERN-OHL-W-2.0
// Independent port-level FIFO model for the product's PCIe register slices.
module pcie_stream_skid_props #(parameter W=12) (
    input wire clk_i, rst_ni, clear_i, s_valid_i, m_ready_i,
    input wire [W-1:0] s_data_i
);
    wire s_ready_o, m_valid_o;
    wire [W-1:0] m_data_o;
    soc_pcie_stream_skid #(.W(W)) dut (.*);

    reg [1:0] count;
    reg [W-1:0] first, second;
    wire push = s_valid_i && s_ready_o;
    wire pop = m_valid_o && m_ready_i;
    initial assume(!rst_ni);

    always @(posedge clk_i or negedge rst_ni) begin
        if (!rst_ni) begin
            count <= 0;
            first <= 0;
            second <= 0;
        end else if (clear_i) begin
            count <= 0;
        end else begin
            case ({push, pop})
                2'b10: count <= count + 1'b1;
                2'b01: count <= count - 1'b1;
            endcase
            if (pop && count == 2)
                first <= second;
            if (push) begin
                if (count == 0 || pop)
                    first <= s_data_i;
                else
                    second <= s_data_i;
            end
        end
    end

    always @(posedge clk_i) begin
        if (rst_ni) begin
            assert(count <= 2);
            assert(s_ready_o == (count < 2));
            assert(m_valid_o == (count != 0));
            if (m_valid_o)
                assert(m_data_o == first);
            cover(count == 2 && !clear_i && pop);
            cover(push && pop && !clear_i);
        end
    end
endmodule
