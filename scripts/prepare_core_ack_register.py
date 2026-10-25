#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Prepare an isolated registered-acknowledgement request-pipe candidate.

This changes request latency and requires a held-request/payload contract.
The module simulations below do not prove that the actual Ibex satisfies that
contract, nor do they establish sequential equivalence or authorize adoption.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

SOURCE_SHA = '3041a7055a57186415284f44d86c8d0d955d8277979460e6348a7837569854ac'
REQUIRED_CORE_PROOFS = [
    'Actual Ibex keeps each permission-approved request and its complete payload stable until delayed acknowledgement, except common reset.',
    'The PMP decision cannot withdraw an already captured request before acknowledgement; denied beats never enter this queue.',
    'LSU split-beat sequencing, first/second-beat errors, fault address and response ownership remain precise with delayed acknowledgement.',
    'ID/WB hazards, retirement, branch/interrupt/exception ordering and core clock enable remain correct through the added cycle.',
    'Common reset cancels queue, core and response endpoints together; no response arrives before its acknowledged request.',
]
EDITS = [
    ('  reg valid_q;\n',
     '  // Isolated candidate: capture a held request, acknowledge next cycle,\n'
     '  // then expose it downstream. Common reset is the only legal abort.\n'
     '  reg ack_q;\n  reg valid_q;\n'),
    ('  assign gnt_o = rst_ni && req_i && !valid_q;\n'
     '  assign req_o = rst_ni && valid_q;\n',
     '  wire capture_intent = rst_ni && req_i && !valid_q;\n'
     '  assign gnt_o = rst_ni && ack_q;\n'
     '  assign req_o = rst_ni && valid_q && !ack_q;\n'),
    ("    else if (gnt_o) valid_q <= 1'b1;\n",
     "    else if (capture_intent) valid_q <= 1'b1;\n"),
    ('  // Payload is observable only while req_o is asserted.',
     "  always @(posedge clk_i or negedge rst_ni)\n"
     "    if (!rst_ni) ack_q <= 1'b0;\n"
     "    else ack_q <= capture_intent;\n\n"
     '  // Payload is observable only while req_o is asserted.'),
    ('    if (gnt_o) payload_q <= {addr_i, we_i, be_i, wdata_i};\n',
     '    if (capture_intent) payload_q <= {addr_i, we_i, be_i, wdata_i};\n'),
]


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def transform(raw):
    if hashlib.sha256(raw).hexdigest() != SOURCE_SHA:
        raise ValueError('Expected exact C10 soc_req_pipe source')
    text = raw.decode('ascii')
    for before, after in EDITS:
        if text.count(before) != 1:
            raise ValueError('Ambiguous registered-ack insertion point')
        text = text.replace(before, after, 1)
    restored = text
    for before, after in reversed(EDITS):
        restored = restored.replace(after, before, 1)
    if restored.encode('ascii') != raw:
        raise ValueError('Candidate changed outside recorded edits')
    return text.encode('ascii')


def preparation_receipt(output):
    return dict(status='PREPARED_RETIMING_NOT_ADOPTED', source_sha256=SOURCE_SHA,
        sources={n:sha(output/n) for n in ('original.v', 'candidate.v')},
        method_sha256=sha(__file__), edits=[dict(before=a, after=b) for a,b in EDITS],
        downstream_request_latency_added_cycles=1,
        upstream_ack_latency_added_cycles=1,
        required_actual_core_proofs=REQUIRED_CORE_PROOFS,
        upstream_stability_is_required=True, common_reset_is_only_legal_abort=True,
        actual_core_protocol_proved=False, sequential_equivalence_proved=False,
        whole_soc_candidate_gate='BLOCKED_PENDING_ACTUAL_CORE_PROTOCOL_AND_HAZARD_VERIFICATION',
        candidate_adopted=False, timing_accepted=False, manufacturing_approval=False)


def prepare(source, output):
    raw = source.read_bytes()
    candidate = transform(raw)
    output.mkdir(parents=True, exist_ok=False)
    (output/'original.v').write_bytes(raw)
    (output/'candidate.v').write_bytes(candidate)
    result = preparation_receipt(output)
    (output/'preparation.json').write_text(json.dumps(result, indent=2)+'\n')
    return result


def verify_prepared(directory):
    result = json.loads((directory/'preparation.json').read_text())
    if transform((directory/'original.v').read_bytes()) != (directory/'candidate.v').read_bytes():
        raise ValueError('Candidate bytes differ')
    if result != preparation_receipt(directory):
        raise ValueError('Prepared pins, method, latency or actual-core acceptance contract changed')
    return result


BENCH = r'''`timescale 1ns/1ps
module tb;
  reg clk=0;
  always #5 clk=!clk;
  reg rst=0, raw_req=0, deny=0, down_gnt=0;
  reg [68:0] payload=0;
  wire req=raw_req && !deny;
  wire grant, down_req;
  wire [68:0] out;
  soc_req_pipe dut(.clk_i(clk),.rst_ni(rst),.req_i(req),.gnt_o(grant),
    .addr_i(payload[68:37]),.we_i(payload[36]),.be_i(payload[35:32]),.wdata_i(payload[31:0]),
    .req_o(down_req),.gnt_i(down_gnt),.addr_o(out[68:37]),.we_o(out[36]),.be_o(out[35:32]),.wdata_o(out[31:0]));
  integer accepted=0, delivered=0, discarded=0, occupied=0, stalls=0;
  reg past_valid=0, past_rst=0, past_req=0, past_grant=0;
  reg [68:0] past_payload=0, expected=0;
  always @(posedge clk) begin
    if (!rst) begin
      if (grant || down_req) $fatal(1,"DUT_CONTRACT transfer during reset");
      if (occupied) discarded=discarded+1;
      occupied=0;
    end else begin
      // This is an explicit environment checker, not an assumed core proof.
      if (past_valid && past_rst && past_req && !past_grant) begin
        if (!req) $fatal(1,"UPSTREAM_CONTRACT withdrawn before grant");
        if (payload !== past_payload) $fatal(1,"UPSTREAM_CONTRACT payload changed before grant");
      end
      if (grant && !req) $fatal(1,"DUT_CONTRACT grant without request");
      if (grant && down_req) $fatal(1,"DUT_CONTRACT downstream before ack completes");
      if (down_req) begin
        if (occupied != 1 || out !== expected) $fatal(1,"DUT_CONTRACT lost reordered or corrupted token");
        if (down_gnt) begin occupied=0; delivered=delivered+1; end
        else stalls=stalls+1;
      end
      if (grant) begin
        if (occupied) $fatal(1,"DUT_CONTRACT duplicate ack or overwrite");
        expected=payload; occupied=1; accepted=accepted+1;
      end
    end
    past_valid=1; past_rst=rst; past_req=req; past_grant=grant; past_payload=payload;
  end
  task tick; begin @(posedge clk); #1; @(negedge clk); end endtask
  task issue(input [68:0] token);
    integer waited;
    begin
      raw_req=1; deny=0; payload=token; waited=0; #1;
      if (grant) $fatal(1,"DUT_CONTRACT combinational grant");
      while (!grant) begin tick; waited=waited+1; if(waited>20) $fatal(1,"DUT_CONTRACT no ack"); end
      if (waited!=1 || down_req) $fatal(1,"DUT_CONTRACT wrong ack latency");
      tick; raw_req=0;
      if (grant || !down_req) $fatal(1,"DUT_CONTRACT wrong downstream latency");
    end
  endtask
  task drain;
    begin down_gnt=1; tick; down_gnt=0; if(down_req || occupied) $fatal(1,"DUT_CONTRACT drain failed"); end
  endtask
  task common_reset;
    begin rst=0; raw_req=0; deny=0; down_gnt=0; tick; tick; rst=1; tick; end
  endtask
  initial begin
    repeat(3) @(negedge clk); rst=1; #1;
    if(grant || down_req) $fatal(1,"DUT_CONTRACT idle grant");
    if (`CASE != 0) begin
      raw_req=1; payload=69'h12345; tick;
      if (`CASE==1) raw_req=0;
      if (`CASE==2) payload=69'h12346;
      if (`CASE==3) deny=1;
      tick;
      $fatal(1,"NEGATIVE_CONTROL was not rejected");
    end
    issue(69'h1234512345); repeat(8) tick; drain;
    // Permission-masked raw request cannot create a queue token or ack.
    raw_req=1; deny=1;
    repeat(4) begin tick; if(grant || down_req) $fatal(1,"DUT_CONTRACT PMP masked request escaped"); end
    raw_req=0; deny=0;
    // Two ordered, adjacent-address beat-like tokens. This is not an LSU proof.
    issue({32'h1000,1'b1,4'hc,32'h11223344});
    raw_req=1; payload={32'h1004,1'b1,4'h3,32'h55667788};
    repeat(4) begin tick; if(grant || !down_req) $fatal(1,"DUT_CONTRACT full queue accepted early"); end
    down_gnt=1; tick; down_gnt=0; tick;
    if(!grant || down_req) $fatal(1,"DUT_CONTRACT second beat ack wrong");
    tick; raw_req=0; repeat(3) tick; drain;
    // First beat accepted, second permission-masked: no invented second beat.
    issue({32'h2000,1'b0,4'hf,32'h0}); drain;
    raw_req=1; deny=1; repeat(3) tick;
    if(grant || down_req) $fatal(1,"DUT_CONTRACT masked second beat escaped");
    raw_req=0; deny=0;
    // Cancel an accepted but undelivered token by resetting both endpoints.
    issue(69'h45678); repeat(2) tick; common_reset;
    // Cancel tentative capture before its acknowledgement edge.
    raw_req=1; payload=69'h98765; tick; common_reset;
    issue(69'habcdef); drain; repeat(2) tick;
    if(occupied || accepted!=delivered+discarded || accepted!=6 || delivered!=5 || discarded!=1 || stalls<10)
      $fatal(1,"DUT_CONTRACT accounting or coverage failed");
    $display("PASS_MODULE_CONTRACT accepted=%0d delivered=%0d discarded=%0d stalls=%0d",accepted,delivered,discarded,stalls);
    $finish;
  end
  initial begin #20000; $fatal(1,"DUT_CONTRACT watchdog"); end
endmodule
'''


def contract_tests(prepared, output):
    verification = verify_prepared(prepared)
    tools = {name:Path(shutil.which(name) or '') for name in ('iverilog', 'vvp')}
    if any(not p.is_file() for p in tools.values()):
        raise ValueError('Icarus Verilog and vvp are required for module contract controls')
    output.mkdir(parents=True, exist_ok=False)
    bench = output/'contract.v'; bench.write_text(BENCH)
    candidate = (prepared/'candidate.v').read_text()
    cases = [('held_and_stalled', 0, candidate, None),
             ('withdrawn_request', 1, candidate, 'UPSTREAM_CONTRACT withdrawn'),
             ('changed_payload', 2, candidate, 'UPSTREAM_CONTRACT payload'),
             ('changed_pmp_decision', 3, candidate, 'UPSTREAM_CONTRACT withdrawn')]
    for name, before, after in [
        ('unsolicited_grant', 'assign gnt_o = rst_ni && ack_q;', 'assign gnt_o = rst_ni && !valid_q;'),
        ('early_downstream', 'assign req_o = rst_ni && valid_q && !ack_q;', 'assign req_o = rst_ni && valid_q;'),
        ('corrupt_payload', 'we_i, be_i, wdata_i};', "we_i, be_i, (wdata_i ^ 32'h1)};")]:
        if candidate.count(before) != 1:
            raise ValueError('Ambiguous negative-control mutation')
        cases.append((name, 0, candidate.replace(before, after, 1), 'DUT_CONTRACT'))
    rows = []
    for name, case, source, expected in cases:
        rtl=output/(name+'.v'); rtl.write_text(source)
        executable=output/(name+'.vvp')
        command=[str(tools['iverilog']),'-g2012','-s','tb','-DCASE='+str(case),'-o',str(executable),str(rtl),str(bench)]
        compile_run=subprocess.run(command,capture_output=True,text=True,timeout=20)
        (output/(name+'-compile.log')).write_text(compile_run.stdout+compile_run.stderr)
        if compile_run.returncode:
            raise ValueError('Module contract control did not compile: '+name)
        executed=subprocess.run([str(tools['vvp']),str(executable)],capture_output=True,text=True,timeout=10)
        log=executed.stdout+executed.stderr; (output/(name+'.log')).write_text(log)
        passed=(executed.returncode==0 and log.count('PASS_MODULE_CONTRACT')==1) if expected is None else (executed.returncode!=0 and expected in log)
        if not passed:
            raise ValueError('Unexpected module contract result: '+name+'\n'+log)
        rows.append(dict(name=name,returncode=executed.returncode,expected_rejection=expected,
                         status='PASS_CONTROL',source_sha256=sha(rtl),log_sha256=sha(output/(name+'.log'))))
    verify_prepared(prepared)
    versions = {}
    for name, path in tools.items():
        version = subprocess.run([str(path), '-V'], capture_output=True, text=True, timeout=10)
        versions[name] = version.stdout + version.stderr
    result=dict(status='PASS_EXPLICIT_MODULE_CONTRACT_CONTROLS_ONLY',cases=rows,
        prepared_sources=verification['sources'],method_sha256=sha(__file__),
        principal_tool_sha256={str(p.resolve()):sha(p) for p in tools.values()},
        tool_versions=versions,
        required_actual_core_proofs=REQUIRED_CORE_PROOFS,
        actual_core_protocol_proved=False,sequential_equivalence_proved=False,
        candidate_adopted=False,timing_accepted=False,manufacturing_approval=False,
        scope='Actual candidate module simulation under checked held-request/payload contract; adjacent beat-like tokens are not an actual LSU, PMP or full-core proof.',
        output_sha256={str(p.relative_to(output)):sha(p) for p in sorted(output.iterdir()) if p.is_file()})
    (output/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    sub=parser.add_subparsers(dest='mode',required=True)
    p=sub.add_parser('prepare');p.add_argument('--source',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    p=sub.add_parser('test');p.add_argument('--prepared',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    result=prepare(args.source,args.output) if args.mode=='prepare' else contract_tests(args.prepared,args.output)
    print(result['status'])


if __name__=='__main__':
    main()
