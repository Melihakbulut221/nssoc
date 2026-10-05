// SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
// SPDX-License-Identifier: CERN-OHL-W-2.0
`default_nettype none
// One assigned logical lane, Gen3 normal-operation complete records.
// EIEOS resets the LFSR AFTER its last symbol; every other non-SKP record
// advances128 bits, including SDS. Only DATA payload is XORed at this boundary.
// OS bytes pass unchanged; TS field descrambling/DC balance belongs to training.
// SKPs bypass/hold the LFSR. Their state field is checked but never loaded.
// Gen3 parity uses SCRAMBLED DATA, resets at SDS and after each standard SKP.
// A parity mismatch reports lane_error_o without abort/retrain. Trailer-state
// diagnostics also do not authorize a retrain. Format faults abort until reset.
// No Polling.Compliance/Loopback, EDS adjacency, lane assignment or LTSSM here.
module soc_pcie_gen3_record_descrambler_v1 #(
    parameter LANE_ID=0
) (
    input wire clk_i, rst_ni, flush_i,
    input wire valid_i,
    output wire ready_o,
    input wire [193:0] block_i,
    input wire [2:0] length_code_i,
    input wire skp_i, eieos_i, realign_i,
    output wire valid_o,
    input wire ready_i,
    output reg [193:0] block_o,
    output reg [2:0] length_code_o,
    output reg skp_o, eieos_o, realign_o,
    output reg format_fault_o, lane_error_o, lfsr_mismatch_o
);
    function [22:0] seed;
        input integer lane;
        begin
            case(lane)
                0:seed=23'h1dbfbc; 1:seed=23'h0607bb;
                2:seed=23'h1ec760; 3:seed=23'h18c0db;
                4:seed=23'h010f12; 5:seed=23'h19cfc9;
                6:seed=23'h0277ce; 7:seed=23'h1bb807;
                default:seed=0;
            endcase
        end
    endfunction
    function [22:0] mask;
        input integer steps, bit_number;
        integer n;
        begin
            mask=23'b1<<bit_number;
            for(n=0;n<steps;n=n+1) mask={^(mask&23'h210125),mask[22:1]};
        end
    endfunction
    generate if(LANE_ID<0 || LANE_ID>7) begin: bad_parameter
        initial $fatal(1,"LANE_ID must be 0..7");
    end endgenerate
    localparam [129:0] EIEOS={128'hff00ff00ff00ff00ff00ff00ff00ff00,2'b01};
    localparam [129:0] SDS={{15{8'h55}},8'he1,2'b01};
    reg [22:0] state_q;
    reg held_q, seeded_q, parity_q, previous_data_q;
    wire [127:0] decoded;
    wire [22:0] advanced;
    wire fixed_block=length_code_i==2 && block_i[193:130]==0;
    wire is_data=fixed_block && block_i[1:0]==2'b10;
    wire is_os=fixed_block && block_i[1:0]==2'b01;
    wire is_eieos=fixed_block && block_i[129:0]==EIEOS;
    wire is_sds=fixed_block && block_i[129:0]==SDS;
    reg skp_encoding;
    reg [23:0] trailer;
    integer j;
    always @* begin
        skp_encoding=length_code_i<=4 && block_i[1:0]==2'b01;
        trailer=0;
        for(j=0;j<20;j=j+1)
            if(j<4*(length_code_i+1) && block_i[2+j*8 +: 8]!=8'haa) skp_encoding=0;
        case(length_code_i)
            0:begin trailer=block_i[65:42];if(block_i[41:34]!=8'he1 || block_i[193:66]!=0)skp_encoding=0;end
            1:begin trailer=block_i[97:74];if(block_i[73:66]!=8'he1 || block_i[193:98]!=0)skp_encoding=0;end
            2:begin trailer=block_i[129:106];if(block_i[105:98]!=8'he1 || block_i[193:130]!=0)skp_encoding=0;end
            3:begin trailer=block_i[161:138];if(block_i[137:130]!=8'he1 || block_i[193:162]!=0)skp_encoding=0;end
            4:begin trailer=block_i[193:170];if(block_i[169:162]!=8'he1)skp_encoding=0;end
            default:skp_encoding=0;
        endcase
    end
    wire [22:0] received_lfsr={trailer[6:0],trailer[15:8],trailer[23:16]};
    wire bad_record=(skp_i ? (!skp_encoding || eieos_i || realign_i) :
        (!(is_data || is_os) || (is_os && block_i[9:2]==8'haa) ||
         (eieos_i != is_eieos) || (realign_i && !is_eieos))) ||
        (!seeded_q && !is_eieos);
    wire enabled=rst_ni && !flush_i && !format_fault_o;
    assign ready_o=enabled && (!held_q || ready_i);
    assign valid_o=enabled && held_q;
    genvar bit_number;
    generate
        for(bit_number=0;bit_number<128;bit_number=bit_number+1) begin: data_bits
            assign decoded[bit_number]=block_i[2+bit_number] ^ ^(state_q&mask(bit_number,22));
        end
        for(bit_number=0;bit_number<23;bit_number=bit_number+1) begin: state_bits
            assign advanced[bit_number]=^(state_q&mask(128,bit_number));
        end
    endgenerate
    always @(posedge clk_i or negedge rst_ni) begin
        if(!rst_ni) begin
            held_q<=0;seeded_q<=0;state_q<=seed(LANE_ID);parity_q<=0;previous_data_q<=0;
            block_o<=0;length_code_o<=0;skp_o<=0;eieos_o<=0;realign_o<=0;
            format_fault_o<=0;lane_error_o<=0;lfsr_mismatch_o<=0;
        end else if(flush_i) begin
            held_q<=0;seeded_q<=0;state_q<=seed(LANE_ID);parity_q<=0;previous_data_q<=0;
            block_o<=0;length_code_o<=0;skp_o<=0;eieos_o<=0;realign_o<=0;
            format_fault_o<=0;lane_error_o<=0;lfsr_mismatch_o<=0;
        end else if(ready_o) begin
            held_q<=valid_i;
            if(valid_i) begin
                if(bad_record) begin
                    held_q<=0;
                    format_fault_o<=1;
                end else begin
                    block_o<=is_data ? {64'd0,decoded,2'b10} : block_i;
                    length_code_o<=length_code_i;skp_o<=skp_i;eieos_o<=eieos_i;realign_o<=realign_i;
                    previous_data_q<=is_data;
                    if(is_eieos) begin
                        state_q<=seed(LANE_ID);seeded_q<=1;parity_q<=0;
                    end else if(skp_i) begin
                        if(received_lfsr!=state_q || (!previous_data_q && trailer[7]!=!state_q[22])) lfsr_mismatch_o<=1;
                        if(previous_data_q && trailer[7]!=parity_q) lane_error_o<=1;
                        parity_q<=0;
                    end else begin
                        state_q<=advanced;
                        if(is_sds) parity_q<=0;
                        else if(is_data) parity_q<=parity_q ^ ^block_i[129:2];
                    end
                end
            end
        end
    end
endmodule
`default_nettype wire
