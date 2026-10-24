// SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
// SPDX-License-Identifier: CERN-OHL-W-2.0
`timescale 1ns/1ps
// Read-only, bounded diagnostic recorder. It never drives a DUT signal.
module nssoc_alu_boot_trace #(
  parameter WIDTH=1, parameter START=983044,
  parameter DEPTH=1024, parameter EVENT_DEPTH=2048, parameter TAIL=1024
)(input clk_i, input [63:0] cycle_i, input [WIDTH-1:0] signals_i,
  input [31:0] unknown_i, input [2:0] clocks_i, enables_i, latched_i, delayed_i,
  input [2:0] notifier_i);
  string samples [0:DEPTH-1];
  string events [0:EVENT_DEPTH-1];
  string directory;
  integer sf, ef, mf, milestones=0, pos=0, count=0, ep=0, ec=0, post=0, event_post=0;
  integer sample_total=0, event_total=0, trigger_count=0, final_index;
  reg triggered=0;
  reg [63:0] first_cycle=0;
  initial begin
    if (!$value$plusargs("trace_dir=%s", directory)) $fatal(1,"Missing trace_dir");
    sf=$fopen({directory,"/trace-samples.log"},"w");
    ef=$fopen({directory,"/trace-events.log"},"w");
    mf=$fopen({directory,"/trace-milestones.log"},"w");
    if (!sf || !ef || !mf) $fatal(1,"Cannot open trace output");
  end
  task dump_samples;
    integer j;
    begin
      for(j=0;j<count;j=j+1) $fdisplay(sf,"%s",samples[(pos-count+j+DEPTH)%DEPTH]);
      $fflush(sf);
    end
  endtask
  task milestone(input string text);
    begin
      if(milestones<1024) begin $fdisplay(mf,"%s",text);milestones=milestones+1;end
      else $fatal(1,"Diagnostic milestone bound exhausted; evidence incomplete");
    end
  endtask
  task dump_events;
    integer j;
    begin
      for(j=0;j<ec;j=j+1) $fdisplay(ef,"%s",events[(ep-ec+j+EVENT_DEPTH)%EVENT_DEPTH]);
      $fflush(ef);
    end
  endtask
  task first_unknown(input string cause);
    begin
      if(!triggered) begin
        triggered=1; trigger_count=trigger_count+1; first_cycle=cycle_i;
        $display("TRACE_FIRST_X cycle=%0d time=%0t cause=%s",cycle_i,$time,cause);
        dump_samples; dump_events;
      end
    end
  endtask
  task event_record(input string text);
    begin
      if(cycle_i>=START) begin
        event_total=event_total+1;
        if(triggered) begin
          if(event_post<EVENT_DEPTH) begin $fdisplay(ef,"%s",text);event_post=event_post+1;end
        end else begin
          events[ep]=text;ep=(ep+1)%EVENT_DEPTH;if(ec<EVENT_DEPTH)ec=ec+1;
        end
      end
    end
  endtask
  // Called at the actual vendor SRAM model's sampling edge, before its NBA.
  task memory_sample(input integer bank, input men, wen, ren,
                     input [10:0] address, input [63:0] mask, data, output_data);
    reg bad;
    begin
      if(cycle_i>=START) begin
        event_record($sformatf("MEM cycle=%0d time=%0t bank=%0d men=%b wen=%b ren=%b addr=%h bm=%h din=%h dout=%h",
          cycle_i,$time,bank,men,wen,ren,address,mask,data,output_data));
        if(cycle_i>=1500000 && bank==0 && men===1'b1 && address===11'h7a7)
          milestone($sformatf("CHECKS_MEMORY cycle=%0d time=%0t wen=%b ren=%b bm=%h din=%h dout=%h",
            cycle_i,$time,wen,ren,mask,data,output_data));
        bad=(men!==1'b0 && men!==1'b1);
        if(men===1'b1) begin
          bad=bad || ((^{wen,ren})===1'bx);
          if(wen===1'b1 || ren===1'b1) bad=bad || ((^address)===1'bx);
          if(wen===1'b1) bad=bad || ((^mask)===1'bx) || ((^(data & mask))===1'bx);
        end
        if(bad) first_unknown($sformatf("active_sram_bank_%0d",bank));
      end
    end
  endtask
  always @(clocks_i or enables_i or latched_i or delayed_i or notifier_i) begin
    event_record($sformatf("CLOCK cycle=%0d time=%0t clk=%b enable=%b latch=%b delayed=%b notifier=%b",
      cycle_i,$time,clocks_i,enables_i,latched_i,delayed_i,notifier_i));
    if(cycle_i>=START && ((^{clocks_i,enables_i,latched_i,delayed_i})===1'bx))
      first_unknown("clock_gate_unknown");
  end
  always @(negedge clk_i) begin
    // Observe after the edge; do not change native event/clock scheduling.
    #0.001;
    if(cycle_i>=START) begin
      sample_total=sample_total+1;
      if(triggered) begin
        if(post<TAIL) begin
          $fdisplay(sf,"S cycle=%0d time=%0t unknown=%h data=%h",cycle_i,$time,unknown_i,signals_i);
          post=post+1;
        end
      end else begin
        samples[pos]=$sformatf("S cycle=%0d time=%0t unknown=%h data=%h",cycle_i,$time,unknown_i,signals_i);
        pos=(pos+1)%DEPTH;if(count<DEPTH)count=count+1;
      end
      if(unknown_i!==32'b0) first_unknown($sformatf("sample_mask_%08h",unknown_i));
    end
  end
  final begin
    if(!triggered) begin
      for(final_index=0;final_index<count;final_index=final_index+1)
        $fdisplay(sf,"%s",samples[(pos-count+final_index+DEPTH)%DEPTH]);
      for(final_index=0;final_index<ec;final_index=final_index+1)
        $fdisplay(ef,"%s",events[(ep-ec+final_index+EVENT_DEPTH)%EVENT_DEPTH]);
    end
    $display("TRACE_SUMMARY triggered=%0d first_cycle=%0d triggers=%0d samples=%0d events=%0d saved_samples=%0d saved_events=%0d",
      triggered,first_cycle,trigger_count,sample_total,event_total,count+post,ec+event_post);
    $display("TRACE_MILESTONES count=%0d",milestones);
    $fclose(sf);$fclose(ef);$fclose(mf);
  end
endmodule
