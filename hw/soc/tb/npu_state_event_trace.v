// SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
// SPDX-License-Identifier: CERN-OHL-W-2.0
`timescale 1ns/1ps
// Read-only scalar observations. Sequence is observer scheduler execution order,
// not a simulator-internal delta index. Never drives or forces DUT signals.
module nssoc_npu_state_event_trace #(
  parameter WIDTH=44, parameter START=1569360, parameter LAST=1569520,
  parameter MAX_EVENTS=20000
)(input clk_i, input [63:0] cycle_i, input [WIDTH-1:0] signals_i);
  string directory;
  integer fd, sequence_no=0, events=0, samples=0;
  initial begin
    if(START<0 || LAST<START || MAX_EVENTS<1) $fatal(1,"Invalid event window");
    if(!$value$plusargs("npu_trace_dir=%s",directory)) $fatal(1,"Missing npu_trace_dir");
    fd=$fopen({directory,"/npu-state-events.log"},"w");
    if(!fd) $fatal(1,"Cannot open scalar event log");
  end
  task record(input integer index, input value);
    begin
      if(cycle_i>=START && cycle_i<=LAST) begin
        if(events>=MAX_EVENTS) $fatal(1,"Native scalar event bound exhausted");
        sequence_no=sequence_no+1;events=events+1;
        $fdisplay(fd,"EV seq=%0d cycle=%0d realtime_ns=%0.3f signal=%0d value=%b all=%b",
          sequence_no,cycle_i,$realtime,index,value,signals_i);
      end
    end
  endtask
  genvar i;
  generate for(i=0;i<WIDTH;i=i+1) begin: observe_scalar
    always @(signals_i[i]) record(i,signals_i[i]);
  end endgenerate
  always @(negedge clk_i) begin
    #0.001;
    if(cycle_i>=START && cycle_i<=LAST) begin
      sequence_no=sequence_no+1;samples=samples+1;
      $fdisplay(fd,"S seq=%0d cycle=%0d realtime_ns=%0.3f all=%b",
        sequence_no,cycle_i,$realtime,signals_i);
      $fflush(fd);
    end
  end
  final begin
    $display("NPU_STATE_TRACE_SUMMARY start=%0d last=%0d width=%0d events=%0d samples=%0d sequence=%0d final_cycle=%0d",
      START,LAST,WIDTH,events,samples,sequence_no,cycle_i);
    $fclose(fd);
  end
endmodule
