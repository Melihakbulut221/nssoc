// SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
// SPDX-License-Identifier: CERN-OHL-W-2.0
// Negative regression fixture: unchanged 71-cell DED-counter cone extracted
// from bb0ea7d native-boot netlist, GitHub run 35548416066, artifact 10618972531.
// Cell models are external, untouched IHP models. This is not product RTL.
// Boundary: pwdata bit, decoded clear, DED event, clock and POR.
module scrub_counter_clear_pre_fix(input clk_i,rst_por_sync_n,_014624_,_040474_,_031540_,output [15:0] count);
wire [15:0] \u_scrub.cnt[2] ;
wire _003046_ ;
wire _003047_ ;
wire _003048_ ;
wire _003049_ ;
wire _003050_ ;
wire _003051_ ;
wire _003052_ ;
wire _003053_ ;
wire _003054_ ;
wire _003055_ ;
wire _003056_ ;
wire _003057_ ;
wire _003058_ ;
wire _003059_ ;
wire _003060_ ;
wire _003061_ ;
wire _040475_ ;
wire _040576_ ;
wire _040577_ ;
wire _040578_ ;
wire _040579_ ;
wire _040580_ ;
wire _040581_ ;
wire _040582_ ;
wire _040583_ ;
wire _040584_ ;
wire _040585_ ;
wire _040586_ ;
wire _040587_ ;
wire _040588_ ;
wire _040589_ ;
wire _040590_ ;
wire _040591_ ;
wire _040592_ ;
wire _040593_ ;
wire _040594_ ;
wire _040595_ ;
wire _040596_ ;
wire _040597_ ;
wire _040598_ ;
wire _040599_ ;
wire _040600_ ;
wire _040601_ ;
wire _040602_ ;
wire _040603_ ;
wire _040604_ ;
wire _040605_ ;
wire _040606_ ;
wire _040607_ ;
wire _040608_ ;
wire _040609_ ;
wire _040610_ ;
wire _040611_ ;
wire _040612_ ;
wire _040613_ ;
assign count=\u_scrub.cnt[2] ;
  sg13g2_buf_1 _087427_ (
    .A(_040474_),
    .X(_040475_)
  );
  sg13g2_nand2_1 _087584_ (
    .A(_014624_),
    .B(_040475_),
    .Y(_040576_)
  );
  sg13g2_inv_1 _087586_ (
    .A(_031540_),
    .Y(_040577_)
  );
  sg13g2_buf_1 _087587_ (
    .A(_040576_),
    .X(_040578_)
  );
  sg13g2_and4_1 _087588_ (
    .A(\u_scrub.cnt[2] [0]),
    .B(\u_scrub.cnt[2] [1]),
    .C(\u_scrub.cnt[2] [3]),
    .D(\u_scrub.cnt[2] [2]),
    .X(_040579_)
  );
  sg13g2_and4_1 _087589_ (
    .A(\u_scrub.cnt[2] [4]),
    .B(\u_scrub.cnt[2] [5]),
    .C(\u_scrub.cnt[2] [6]),
    .D(_040579_),
    .X(_040580_)
  );
  sg13g2_and4_1 _087590_ (
    .A(\u_scrub.cnt[2] [7]),
    .B(\u_scrub.cnt[2] [8]),
    .C(\u_scrub.cnt[2] [9]),
    .D(_040580_),
    .X(_040581_)
  );
  sg13g2_and4_1 _087591_ (
    .A(\u_scrub.cnt[2] [11]),
    .B(\u_scrub.cnt[2] [10]),
    .C(\u_scrub.cnt[2] [12]),
    .D(_040581_),
    .X(_040582_)
  );
  sg13g2_and3_1 _087592_ (
    .A(\u_scrub.cnt[2] [14]),
    .B(\u_scrub.cnt[2] [13]),
    .C(_040582_),
    .X(_040583_)
  );
  sg13g2_a21oi_1 _087593_ (
    .A1(\u_scrub.cnt[2] [15]),
    .A2(_040583_),
    .B1(_040577_),
    .Y(_040584_)
  );
  sg13g2_and2_1 _087594_ (
    .A(_014624_),
    .B(_040474_),
    .X(_040585_)
  );
  sg13g2_o21ai_1 _087595_ (
    .A1(_040585_),
    .A2(_040584_),
    .B1(\u_scrub.cnt[2] [0]),
    .Y(_040586_)
  );
  sg13g2_o21ai_1 _087596_ (
    .A1(\u_scrub.cnt[2] [0]),
    .A2(_040584_),
    .B1(_040586_),
    .Y(_040587_)
  );
  sg13g2_o21ai_1 _087597_ (
    .A1(_040577_),
    .A2(_040578_),
    .B1(_040587_),
    .Y(_003046_)
  );
  sg13g2_nor2b_1 _087598_ (
    .A(\u_scrub.cnt[2] [1]),
    .B_N(_040586_),
    .Y(_040588_)
  );
  sg13g2_and3_1 _087599_ (
    .A(\u_scrub.cnt[2] [0]),
    .B(\u_scrub.cnt[2] [1]),
    .C(_040584_),
    .X(_040589_)
  );
  sg13g2_nor3_1 _087600_ (
    .A(_040585_),
    .B(_040588_),
    .C(_040589_),
    .Y(_003047_)
  );
  sg13g2_and2_1 _087601_ (
    .A(\u_scrub.cnt[2] [2]),
    .B(_040589_),
    .X(_040590_)
  );
  sg13g2_o21ai_1 _087602_ (
    .A1(\u_scrub.cnt[2] [2]),
    .A2(_040589_),
    .B1(_040578_),
    .Y(_040591_)
  );
  sg13g2_nor2_1 _087603_ (
    .A(_040590_),
    .B(_040591_),
    .Y(_003048_)
  );
  sg13g2_and2_1 _087604_ (
    .A(\u_scrub.cnt[2] [3]),
    .B(_040590_),
    .X(_040592_)
  );
  sg13g2_o21ai_1 _087605_ (
    .A1(\u_scrub.cnt[2] [3]),
    .A2(_040590_),
    .B1(_040578_),
    .Y(_040593_)
  );
  sg13g2_nor2_1 _087606_ (
    .A(_040592_),
    .B(_040593_),
    .Y(_003049_)
  );
  sg13g2_xnor2_1 _087607_ (
    .A(\u_scrub.cnt[2] [4]),
    .B(_040592_),
    .Y(_040594_)
  );
  sg13g2_nor2_1 _087608_ (
    .A(_040585_),
    .B(_040594_),
    .Y(_003050_)
  );
  sg13g2_and3_1 _087609_ (
    .A(\u_scrub.cnt[2] [4]),
    .B(\u_scrub.cnt[2] [5]),
    .C(_040592_),
    .X(_040595_)
  );
  sg13g2_a21oi_1 _087610_ (
    .A1(\u_scrub.cnt[2] [4]),
    .A2(_040592_),
    .B1(\u_scrub.cnt[2] [5]),
    .Y(_040596_)
  );
  sg13g2_nor3_1 _087611_ (
    .A(_040585_),
    .B(_040595_),
    .C(_040596_),
    .Y(_003051_)
  );
  sg13g2_o21ai_1 _087612_ (
    .A1(\u_scrub.cnt[2] [6]),
    .A2(_040595_),
    .B1(_040578_),
    .Y(_040597_)
  );
  sg13g2_and2_1 _087613_ (
    .A(\u_scrub.cnt[2] [6]),
    .B(_040595_),
    .X(_040598_)
  );
  sg13g2_nor2_1 _087614_ (
    .A(_040597_),
    .B(_040598_),
    .Y(_003052_)
  );
  sg13g2_o21ai_1 _087615_ (
    .A1(\u_scrub.cnt[2] [7]),
    .A2(_040598_),
    .B1(_040578_),
    .Y(_040599_)
  );
  sg13g2_a21oi_1 _087616_ (
    .A1(\u_scrub.cnt[2] [7]),
    .A2(_040598_),
    .B1(_040599_),
    .Y(_003053_)
  );
  sg13g2_a21oi_1 _087617_ (
    .A1(\u_scrub.cnt[2] [7]),
    .A2(_040598_),
    .B1(\u_scrub.cnt[2] [8]),
    .Y(_040600_)
  );
  sg13g2_and4_1 _087618_ (
    .A(\u_scrub.cnt[2] [6]),
    .B(\u_scrub.cnt[2] [7]),
    .C(\u_scrub.cnt[2] [8]),
    .D(_040595_),
    .X(_040601_)
  );
  sg13g2_nor3_1 _087619_ (
    .A(_040585_),
    .B(_040600_),
    .C(_040601_),
    .Y(_003054_)
  );
  sg13g2_o21ai_1 _087620_ (
    .A1(\u_scrub.cnt[2] [9]),
    .A2(_040601_),
    .B1(_040578_),
    .Y(_040602_)
  );
  sg13g2_and2_1 _087621_ (
    .A(\u_scrub.cnt[2] [9]),
    .B(_040601_),
    .X(_040603_)
  );
  sg13g2_nor2_1 _087622_ (
    .A(_040602_),
    .B(_040603_),
    .Y(_003055_)
  );
  sg13g2_o21ai_1 _087623_ (
    .A1(\u_scrub.cnt[2] [10]),
    .A2(_040603_),
    .B1(_040578_),
    .Y(_040604_)
  );
  sg13g2_and2_1 _087624_ (
    .A(\u_scrub.cnt[2] [10]),
    .B(_040603_),
    .X(_040605_)
  );
  sg13g2_nor2_1 _087625_ (
    .A(_040604_),
    .B(_040605_),
    .Y(_003056_)
  );
  sg13g2_o21ai_1 _087626_ (
    .A1(\u_scrub.cnt[2] [11]),
    .A2(_040605_),
    .B1(_040578_),
    .Y(_040606_)
  );
  sg13g2_and2_1 _087627_ (
    .A(\u_scrub.cnt[2] [11]),
    .B(_040605_),
    .X(_040607_)
  );
  sg13g2_nor2_1 _087628_ (
    .A(_040606_),
    .B(_040607_),
    .Y(_003057_)
  );
  sg13g2_o21ai_1 _087629_ (
    .A1(\u_scrub.cnt[2] [12]),
    .A2(_040607_),
    .B1(_040578_),
    .Y(_040608_)
  );
  sg13g2_and2_1 _087630_ (
    .A(\u_scrub.cnt[2] [12]),
    .B(_040607_),
    .X(_040609_)
  );
  sg13g2_nor2_1 _087631_ (
    .A(_040608_),
    .B(_040609_),
    .Y(_003058_)
  );
  sg13g2_o21ai_1 _087632_ (
    .A1(\u_scrub.cnt[2] [13]),
    .A2(_040609_),
    .B1(_040578_),
    .Y(_040610_)
  );
  sg13g2_nand2_1 _087633_ (
    .A(\u_scrub.cnt[2] [13]),
    .B(_040609_),
    .Y(_040611_)
  );
  sg13g2_nor2b_1 _087634_ (
    .A(_040610_),
    .B_N(_040611_),
    .Y(_003059_)
  );
  sg13g2_xor2_1 _087635_ (
    .A(\u_scrub.cnt[2] [14]),
    .B(_040611_),
    .X(_040612_)
  );
  sg13g2_nor2_1 _087636_ (
    .A(_040585_),
    .B(_040612_),
    .Y(_003060_)
  );
  sg13g2_a21oi_1 _087637_ (
    .A1(_031540_),
    .A2(_040583_),
    .B1(\u_scrub.cnt[2] [15]),
    .Y(_040613_)
  );
  sg13g2_nor2_1 _087638_ (
    .A(_040585_),
    .B(_040613_),
    .Y(_003061_)
  );
  sg13g2_dfrbpq_1 _103033_ (
    .CLK(clk_i),
    .D(_003046_),
    .Q(\u_scrub.cnt[2] [0]),
    .RESET_B(rst_por_sync_n)
  );
  sg13g2_dfrbpq_1 _103034_ (
    .CLK(clk_i),
    .D(_003047_),
    .Q(\u_scrub.cnt[2] [1]),
    .RESET_B(rst_por_sync_n)
  );
  sg13g2_dfrbpq_1 _103035_ (
    .CLK(clk_i),
    .D(_003048_),
    .Q(\u_scrub.cnt[2] [2]),
    .RESET_B(rst_por_sync_n)
  );
  sg13g2_dfrbpq_1 _103036_ (
    .CLK(clk_i),
    .D(_003049_),
    .Q(\u_scrub.cnt[2] [3]),
    .RESET_B(rst_por_sync_n)
  );
  sg13g2_dfrbpq_1 _103037_ (
    .CLK(clk_i),
    .D(_003050_),
    .Q(\u_scrub.cnt[2] [4]),
    .RESET_B(rst_por_sync_n)
  );
  sg13g2_dfrbpq_1 _103038_ (
    .CLK(clk_i),
    .D(_003051_),
    .Q(\u_scrub.cnt[2] [5]),
    .RESET_B(rst_por_sync_n)
  );
  sg13g2_dfrbpq_1 _103039_ (
    .CLK(clk_i),
    .D(_003052_),
    .Q(\u_scrub.cnt[2] [6]),
    .RESET_B(rst_por_sync_n)
  );
  sg13g2_dfrbpq_1 _103040_ (
    .CLK(clk_i),
    .D(_003053_),
    .Q(\u_scrub.cnt[2] [7]),
    .RESET_B(rst_por_sync_n)
  );
  sg13g2_dfrbpq_1 _103041_ (
    .CLK(clk_i),
    .D(_003054_),
    .Q(\u_scrub.cnt[2] [8]),
    .RESET_B(rst_por_sync_n)
  );
  sg13g2_dfrbpq_1 _103042_ (
    .CLK(clk_i),
    .D(_003055_),
    .Q(\u_scrub.cnt[2] [9]),
    .RESET_B(rst_por_sync_n)
  );
  sg13g2_dfrbpq_1 _103043_ (
    .CLK(clk_i),
    .D(_003056_),
    .Q(\u_scrub.cnt[2] [10]),
    .RESET_B(rst_por_sync_n)
  );
  sg13g2_dfrbpq_1 _103044_ (
    .CLK(clk_i),
    .D(_003057_),
    .Q(\u_scrub.cnt[2] [11]),
    .RESET_B(rst_por_sync_n)
  );
  sg13g2_dfrbpq_1 _103045_ (
    .CLK(clk_i),
    .D(_003058_),
    .Q(\u_scrub.cnt[2] [12]),
    .RESET_B(rst_por_sync_n)
  );
  sg13g2_dfrbpq_1 _103046_ (
    .CLK(clk_i),
    .D(_003059_),
    .Q(\u_scrub.cnt[2] [13]),
    .RESET_B(rst_por_sync_n)
  );
  sg13g2_dfrbpq_1 _103047_ (
    .CLK(clk_i),
    .D(_003060_),
    .Q(\u_scrub.cnt[2] [14]),
    .RESET_B(rst_por_sync_n)
  );
  sg13g2_dfrbpq_1 _103048_ (
    .CLK(clk_i),
    .D(_003061_),
    .Q(\u_scrub.cnt[2] [15]),
    .RESET_B(rst_por_sync_n)
  );
endmodule
