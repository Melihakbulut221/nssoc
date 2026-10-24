// SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
// SPDX-License-Identifier: CERN-OHL-W-2.0
`default_nettype none

// Transaction-layer register backend, NOT a PCIe controller or PHY.
// One complete, integrity-checked TLP descriptor per RX handshake. Header
// DW0 is [127:96], DW1 [95:64], DW2 [63:32], DW3 [31:0]. Payload is a
// separate DWORD in APB byte-lane order. The upstream packet assembler must
// supply the actual payload count (not a copy of the header Length field),
// discard bad LCRC/ECRC packets, and supply the assigned function ID.
// Supports only TC0, untranslated, unprefixed, non-poisoned single-DWORD
// register transactions. See docs/98 for exact exclusions and integration.
module soc_pcie_tlp_regs #(
    parameter [15:0] VENDOR_ID = 16'hffff, // No assigned product identity.
    parameter [15:0] DEVICE_ID = 16'h0000,
    parameter integer APB_TIMEOUT = 256
) (
    input wire clk_i,
    input wire rst_ni,
    input wire [15:0] function_id_i,
    input wire [127:0] rx_hdr_i,
    input wire [31:0] rx_data_i,
    input wire [10:0] rx_payload_dw_i,
    input wire rx_valid_i,
    output wire rx_ready_o,
    output reg [127:0] tx_hdr_o,
    output reg [31:0] tx_data_o,
    output reg tx_has_data_o,
    output reg tx_valid_o,
    input wire tx_ready_i,
    output wire psel_o,
    output wire penable_o,
    output reg [11:0] paddr_o,
    output reg pwrite_o,
    output reg [3:0] pstrb_o,
    output reg [31:0] pwdata_o,
    input wire pready_i,
    input wire pslverr_i,
    input wire [31:0] prdata_i,
    output reg error_o, // One-cycle local report, not PCIe AER messaging.
    output wire memory_enable_o,
    output wire [31:0] bar0_o
);
    localparam [2:0] IDLE=0, SETUP=1, ACCESS=2, RESPONSE=3;
    localparam integer TW = APB_TIMEOUT > 1 ? $clog2(APB_TIMEOUT) : 1;
    localparam [TW-1:0] TIMEOUT_LAST = TW'(APB_TIMEOUT-1);
    reg [2:0] state;
    reg [TW-1:0] timer;
    reg memory_enable;
    reg [31:0] bar0;
    reg [15:0] requester, completer;
    reg [7:0] tag;
    reg [6:0] lower_address;
    reg [11:0] byte_count;

    wire [31:0] dw0=rx_hdr_i[127:96], dw1=rx_hdr_i[95:64];
    wire [31:0] dw2=rx_hdr_i[63:32], dw3=rx_hdr_i[31:0];
    wire [2:0] fmt=dw0[31:29];
    wire [4:0] typ=dw0[28:24];
    wire has_data=fmt[1];
    wire is_memory=typ==0 && fmt<=3;
    wire is_config=typ==4 && (fmt==0 || fmt==2);
    wire is_posted=(is_memory && has_data) || typ[4];
    wire is_completion=typ==10 || typ==11;
    wire [31:0] addr=fmt[0] ? dw3 : dw2;
    wire [3:0] first_be=dw1[3:0];
    wire [31:0] be_mask={{8{first_be[3]}},{8{first_be[2]}},
                         {8{first_be[1]}},{8{first_be[0]}}};
    // Length 0 encodes 1024 DWORDs, never an empty request.
    wire one_dw=dw0[9:0]==1 && dw1[7:4]==0;
    wire payload_ok=rx_payload_dw_i==(has_data ? 11'd1 : 11'd0);
    // Unsupported/reserved fields include extended tags, hints, digest,
    // poison, attributes and address translation. Report and discard them;
    // do not guess semantics or issue a local bus transfer.
    wire simple_header=dw0[23:10]==0;
    wire target_ok=addr[31:12]==bar0[31:12] &&
                   (!fmt[0] || dw2==0) && addr[1:0]==0;
    wire [1:0] first_byte=first_be[0] ? 0 : first_be[1] ? 1 : first_be[2] ? 2 : 3;
    wire [1:0] last_byte=first_be[3] ? 3 : first_be[2] ? 2 : first_be[1] ? 1 : 0;
    wire [11:0] count_bytes=first_be==0 ? 12'd1 :
                            12'd1+{10'b0,last_byte}-{10'b0,first_byte};

    assign memory_enable_o=memory_enable;
    assign bar0_o=bar0;
    assign rx_ready_o=state==IDLE && rst_ni;
    assign psel_o=(state==SETUP || state==ACCESS) && rst_ni;
    assign penable_o=state==ACCESS && rst_ni;

    // Type-0 configuration subset only. PCIe capability, MSI, PM, AER,
    // FLR and link capabilities remain unimplemented, not advertised.
    reg [31:0] cfg_data;
    always @* begin
        cfg_data=0;
        case (dw2[11:2])
            10'h000: cfg_data={DEVICE_ID,VENDOR_ID};
            10'h001: cfg_data={30'b0,memory_enable,1'b0};
            10'h004: cfg_data=bar0;
            default: cfg_data=0;
        endcase
    end

    task complete;
        input [2:0] status;
        input data_valid;
        input [31:0] data;
        input [15:0] cid, rid;
        input [7:0] req_tag;
        input [11:0] bytes_left;
        input [6:0] low_addr;
        begin
            tx_hdr_o<={data_valid ? 32'h4a000001 : 32'h0a000000,
                      cid,status,1'b0,bytes_left,rid,req_tag,1'b0,low_addr,32'b0};
            tx_data_o<=data;
            tx_has_data_o<=data_valid;
            tx_valid_o<=1;
            state<=RESPONSE;
        end
    endtask

    always @(posedge clk_i or negedge rst_ni) begin
        if (!rst_ni) begin
            state<=IDLE; timer<=0; memory_enable<=0; bar0<=0;
            requester<=0; completer<=0; tag<=0; lower_address<=0; byte_count<=0;
            tx_hdr_o<=0; tx_data_o<=0; tx_has_data_o<=0; tx_valid_o<=0;
            paddr_o<=0; pwrite_o<=0; pstrb_o<=0; pwdata_o<=0; error_o<=0;
        end else begin
            error_o<=0;
            case (state)
                IDLE: if (rx_valid_i) begin
                    if (!simple_header || !payload_ok) begin
                        error_o<=1;
                    end else if (is_completion || fmt>3 || typ[4]) begin
                        error_o<=1; // No response to completions or messages.
                    end else if (!one_dw || (!is_memory && !is_config)) begin
                        error_o<=1;
                        if (!is_posted)
                            complete(3'd1,0,0,function_id_i,dw1[31:16],dw1[15:8],0,0);
                    end else if (is_config) begin
                        if (dw2[31:16]!=function_id_i || dw2[15:12]!=0 || dw2[1:0]!=0) begin
                            error_o<=1;
                            complete(3'd1,0,0,function_id_i,dw1[31:16],dw1[15:8],0,0);
                        end else if (has_data) begin
                            if (dw2[11:2]==1 && first_be[0]) memory_enable<=rx_data_i[1];
                            if (dw2[11:2]==4)
                                bar0<=((bar0 & ~be_mask) | (rx_data_i & be_mask)) & 32'hfffff000;
                            complete(0,0,0,function_id_i,dw1[31:16],dw1[15:8],4,0);
                        end else begin
                            complete(0,1,cfg_data & be_mask,function_id_i,dw1[31:16],dw1[15:8],4,0);
                        end
                    end else if (!memory_enable || !target_ok) begin
                        error_o<=1;
                        if (!has_data)
                            complete(3'd1,0,0,function_id_i,dw1[31:16],dw1[15:8],0,0);
                    end else if (first_be==0) begin
                        // PCIe zero-length memory writes have no side effects;
                        // reads complete with an unspecified single DWORD.
                        if (!has_data)
                            complete(0,1,0,function_id_i,dw1[31:16],dw1[15:8],1,addr[6:0]);
                    end else begin
                        requester<=dw1[31:16]; tag<=dw1[15:8]; completer<=function_id_i;
                        lower_address<={addr[6:2],first_byte}; byte_count<=count_bytes;
                        paddr_o<=addr[11:0]; pwrite_o<=has_data;
                        pstrb_o<=has_data ? first_be : 4'b0; pwdata_o<=rx_data_i; timer<=0; state<=SETUP;
                    end
                end
                SETUP: state<=ACCESS;
                ACCESS: begin
                    if (pready_i || timer==TIMEOUT_LAST) begin
                        if (pslverr_i || !pready_i) begin
                            error_o<=1;
                            if (!pwrite_o) complete(3'd4,0,0,completer,requester,tag,0,0);
                            else state<=IDLE;
                        end else if (pwrite_o) state<=IDLE;
                        else complete(0,1,prdata_i,completer,requester,tag,byte_count,lower_address);
                    end else timer<=timer+1'b1;
                end
                RESPONSE: if (tx_ready_i) begin tx_valid_o<=0; state<=IDLE; end
                default: state<=IDLE;
            endcase
        end
    end
    generate if (APB_TIMEOUT<1) begin : g_bad_timeout
        INVALID_PCIE_APB_TIMEOUT invalid_parameter();
    end endgenerate
endmodule
`default_nettype wire
