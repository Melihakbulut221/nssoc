// SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
// SPDX-License-Identifier: CERN-OHL-W-2.0
`timescale 1ns/1ps
// Reads source-bound scalars only. INIT reports static X/Z separately from EV.
// Sequence is observed scheduler order, not an internal simulator delta index.
module nssoc_npu_frontier_event_trace #(
  parameter WIDTH=44, parameter START=1569360, parameter LAST=1569520,
  parameter MAX_EVENTS=100000
)(input clk_i,input [63:0] cycle_i,input [WIDTH-1:0] signals_i);
  string directory;
  integer fd, sequence_no=0, events=0, samples=0;
  reg armed=0;
  reg [WIDTH-1:0] previous;
  initial begin
    if(WIDTH<1 || WIDTH>1024 || START<1 || LAST<START || MAX_EVENTS<1) $fatal(1,"Invalid cone window");
    if(!$value$plusargs("npu_frontier_dir=%s",directory)) $fatal(1,"Missing npu_frontier_dir");
    fd=$fopen({directory,"/npu-frontier-events.log"},"w");
    if(!fd) $fatal(1,"Cannot open cone log");
  end
  task record(input integer index,input value);
    reg prior;
    begin
      if(armed && cycle_i>=START-1 && cycle_i<=LAST && value !== previous[index]) begin
        if(events>=MAX_EVENTS) $fatal(1,"Cone event bound exhausted");
        prior=previous[index];previous[index]=value;
        sequence_no=sequence_no+1;events=events+1;
        $fdisplay(fd,"EV seq=%0d cycle=%0d realtime_ns=%0.3f signal=%0d prior=%b value=%b all=%b",
          sequence_no,cycle_i,$realtime,index,prior,value,signals_i);
      end
    end
  endtask
  genvar i;
  generate for(i=0;i<WIDTH;i=i+1) begin: observe_scalar
    always @(signals_i[i]) record(i,signals_i[i]);
  end endgenerate
  always @(negedge clk_i) begin
    #0.001;
    if(cycle_i==START-1) begin
      if(armed) $fatal(1,"Duplicate cone initialization");
      previous=signals_i;armed=1;sequence_no=sequence_no+1;
      $fdisplay(fd,"INIT seq=%0d cycle=%0d realtime_ns=%0.3f all=%b",
        sequence_no,cycle_i,$realtime,signals_i);
    end
    if(cycle_i>=START && cycle_i<=LAST) begin
      if(!armed) $fatal(1,"Uninitialized cone capture");
      sequence_no=sequence_no+1;samples=samples+1;
      $fdisplay(fd,"S seq=%0d cycle=%0d realtime_ns=%0.3f all=%b",
        sequence_no,cycle_i,$realtime,signals_i);$fflush(fd);
    end
  end
  final begin
    $display("NPU_FRONTIER_SUMMARY start=%0d last=%0d width=%0d events=%0d samples=%0d sequence=%0d final_cycle=%0d armed=%b",
      START,LAST,WIDTH,events,samples,sequence_no,cycle_i,armed);
    $fclose(fd);
  end
endmodule
