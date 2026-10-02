#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Read-only, source-bound diagnostic replay of the rejected ALU vendor boot.

The 1.6M-cycle diagnostic is separate from the unchanged 3M-cycle qualification.
Neither a captured trace nor a successful reference boot adopts the candidate.
"""
import argparse
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import time

import run_cloud_alu_qualification as q

ROOT=q.ROOT
CYCLES=1_600_000
START=983_044  # First cycle after the unchanged 983043-cycle native MBIST receipt.
MONITOR='hw/soc/tb/alu_boot_trace.v'
OWN=('scripts/run_cloud_alu_boot_trace.py', MONITOR, 'sw/tests/test_alu_boot_trace.py',
     '.github/workflows/timing-alu-boot-trace.yml')
BASE_PINS={
 'scripts/run_cloud_alu_qualification.py':'cc918fbe661e7cd18f935795a08133c8b5438a256b5f50202195840f544fd429',
 'scripts/run_cloud_alu_prefix.py':'d7b390371a6f2a871b4861edcc6728d0856b9a5736308e5cc84b4bca393e5fea',
 'scripts/prepare_alu_prefix.py':'ae22ae3b8e2206ade9d5f6499bc5c9f032d4143cc9b25eda9427f78500e020b5',
 'scripts/run_cloud_eco_logic_proof.py':'093cd8bfedce21561b57c049d935f1a80d3b6a09fd06b673b1ea0c58659f1c6e',
 'scripts/run_cloud_timing_experiment.py':'689c4dbd5a036fc1919d25c0d816f1740a878b11d7dfef432ae7e41c31197524',
 'scripts/bootstrap_oss.py':'e721a22cd15131fcce79f0283863f0b6db2accb9c7349324360602e0f1c81277',
 '.github/workflows/timing-alu-qualification.yml':'777d566224bb3af9667cf997b3797b1b6829e721995bf31809aefafd4fd7352a',
 'hw/soc/pnr/alu-qualification-input.lock.json':'5848b42bbdf8817205d629d7db2ef9619f82a62f12d8667fd85e749f219511c2',
 'hw/soc/pnr/alu-prefix-c10-input.lock.json':'816eb1c44531345b1e8ad5b6fae5c099977ba30c5236e47a28e2bf1282a8006c',
 'docs/evidence/timing-cloud-input-20260930.json':'b8c3044903eff78728c4a5205a2e054576ad91ccdaa0bff28c59de3d88ae712a'}
HELPER_PINS={
 'hw/soc/flow/sim_logic_boot_gl.py':'85bf0e22c0ba246973953ac5c8ee79e4c7219fcee2c78c5d55babcc121385830',
 'hw/soc/flow/gen_logic_boot_rom.py':'5f3510003984edf7decf2be3240fe9a13074547d7d87bcf2cfa4f73d9e3dc117'}
CORE='u_ibex.u_ibex_core.'
FIELDS=(
 ('rst_raw_n',1),('rst_por_sync_n',1),('rst_sync',2),('bus_clk_en',1),('clk_bus',1),('clk_npu',1),
 ('u_ibex.clk',1),('u_ibex.clock_en',1),('g_core_req_reg.u_data_request.rst_ni',1),
 ('g_core_req_reg.u_data_request.valid_q',1),('bus_data_addr',32),('bus_data_be',4),('bus_data_we',1),('bus_data_wdata',32),
 ('u_bus.g_req_reg.r_val',1),('u_bus.g_req_reg.r_own',1),('u_bus.g_req_reg.r_tgt',3),('u_bus.push',7),
 ('s_addr',28),('s_be',4),('s_we',1),('s_wdata',32),('s_rdata_ram',32),('s_rdata_npu',32),
 ('u_apb.gnt_o',1),('u_apb.rvalid_o',1),('u_apb.state',3),('paddr',20),('penable',1),('pwrite',1),('pwdata',32),
 ('u_ram.g_ram_2048x64_ecc.u_ecc.gnt_o',1),
 (CORE+'cs_registers_i.pc_wb_i',32),(CORE+'id_stage_i.controller_i.instr_i',32),
 (CORE+'id_stage_i.controller_i.instr_valid_i',1),(CORE+'id_stage_i.controller_i.ctrl_fsm_cs',10),
 (CORE+'load_store_unit_i.ls_fsm_cs',4),(CORE+'load_store_unit_i.lsu_err_q',1),
 (CORE+'load_store_unit_i.pmp_err_q',1),
 (CORE+'wb_stage_i.g_writeback_stage.wb_valid_q',1),
 (CORE+'if_stage_i.gen_prefetch_buffer.prefetch_buffer_i.fetch_addr_q',32),
 ('u_npu.rvalid_o',1),('u_npu.err_o',1),('u_npu.ev_state',4),('u_npu.win_state',2),
 ('u_npu.u_ser.state',2),('u_npu.blk_rst_n',1),('u_npu.u_node0.state_clr_req',1),
 ('u_npu.u_node0.dstate',2),('u_scrub.cnt[0]',16),('u_scrub.cnt[2]',16))
GATES=('g_clkgate.u_bus_cg.u_icg','g_clkgate.u_npu_cg.u_icg','u_ibex.core_clock_gate_i.u_icg')
SRAMS=tuple(f'u_ram.g_ram_2048x64_ecc.u_b{i}' for i in range(4))


def ref(name):
    return 'dut.'+(name if re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*',name) else '\\'+name+' ')


def declarations(text):
    result={}
    for match in re.finditer(r'^  wire(?: \[(\d+):(\d+)\])? (\\\S+ |[A-Za-z_]\w*);$',text,re.M):
        name=match[3].strip().removeprefix('\\')
        q.require(name not in result,'Duplicate named wire: '+name)
        result[name]=abs(int(match[1])-int(match[2]))+1 if match[1] else 1
    return result


def validate_bindings(text,models):
    actual=declarations(text)
    for name,width in FIELDS:q.require(actual.get(name)==width,'Missing/wrong-width retained alias: '+name)
    cells={}
    for name,kind in [(n,'sg13g2_lgcp_1') for n in GATES]+[(n,'RM_IHPSG13_1P_2048x64_c2_bm_bist') for n in SRAMS]:
        matches=re.findall(r'^  '+kind+r' \\'+re.escape(name)+r'  \(\n(.*?)^  \);',text,re.M|re.S)
        q.require(len(matches)==1,'Missing/duplicate actual native instance: '+name)
        cells[name]=dict(type=kind,connections=matches[0])
    std=models['sg13g2_stdcell.v'];part=std.split('module sg13g2_lgcp_1 (GCLK, GATE, CLK);',1)[1].split('endmodule',1)[0]
    for token in ('delayed_CLK','int_fwire_int_GATE','notifier','ihp_latch (int_fwire_int_GATE'):
        q.require(token in part,'Native clock observation contract changed')
    wrapper=models['RM_IHPSG13_1P_2048x64_c2_bm_bist.v']
    q.require(') i_SRAM_1P_behavioral_bm_bist (' in wrapper,'Native SRAM hierarchy changed')
    behavior=models['RM_IHPSG13_1P_core_behavioral_bm_bist.v']
    q.require('always @(posedge CLK_MUX)' in behavior,'Native SRAM sampling edge changed')
    for name in ('MEN','WEN','REN','ADDR','BM','DIN','CLK'):
        q.require(name+'_MUX' in behavior,'Native SRAM sample signal missing')
    return dict(fields=[dict(name=n,width=w,expression=ref(n)) for n,w in FIELDS],
                cells=cells,packed_bits=sum(w for _,w in FIELDS),sample_order='FIELDS[0] is most significant',
                memory_sampling='Actual vendor CLK_MUX posedge; current active controls/address/masked DIN before native NBA',
                monitor_start_cycle=START,milestone_start_cycle=1_500_000,
                unknown_mask_bits={str(i):name for i,name in enumerate(('reset_tree','clock_enables','core_control',
                    'valid_instruction','queued_data_request','fabric_response_control','npu_control','ram_ecc_counters',
                    'valid_npu_response','valid_writeback_pc'))},
                checks_counter=dict(address='0x00001e9c',bank=0,vendor_row='0x7a7',
                    observation='Request valid/address/write/BE/data/RAM grant/fabric push/PC plus actual SRAM sampling-edge controls and stored value; no inferred completion from UART alone'),
                clock_order=list(GATES),unknown_notifier_is_recorded_but_not_itself_a_failure=True)


def unknown(expressions):
    return '((^{'+','.join(expressions)+'}) === 1\'bx)'


def request_unknown():
    mask='{'+','.join('{8{'+ref('bus_data_be')+f'[{i}]'+'}}' for i in (3,2,1,0))+'}'
    return ('('+ref('g_core_req_reg.u_data_request.valid_q')+" === 1'b1 && ("+unknown(
        [ref(n) for n in ('bus_data_addr','bus_data_be','bus_data_we')])+" || ("+ref('bus_data_we')+
        " === 1'b1 && "+unknown(['('+ref('bus_data_wdata')+' & '+mask+')'])+')))')


def bindings():
    f=lambda name:ref(name)
    checks=[unknown([f(n) for n in ('rst_raw_n','rst_por_sync_n','rst_sync','g_core_req_reg.u_data_request.rst_ni')]),
        unknown([f(n) for n in ('u_ibex.clk','u_ibex.clock_en','clk_bus','clk_npu','bus_clk_en')]),
        unknown([f(n) for n in (CORE+'id_stage_i.controller_i.ctrl_fsm_cs',CORE+'load_store_unit_i.ls_fsm_cs',
                'g_core_req_reg.u_data_request.valid_q',CORE+'id_stage_i.controller_i.instr_valid_i')]),
        '('+f(CORE+'id_stage_i.controller_i.instr_valid_i')+" === 1'b1 && "+unknown([f(CORE+'id_stage_i.controller_i.instr_i')])+')',
        request_unknown(),
        unknown([f(n) for n in ('u_bus.g_req_reg.r_val','u_bus.push','u_npu.rvalid_o','u_apb.rvalid_o')]),
        unknown([f(n) for n in ('u_npu.ev_state','u_npu.win_state','u_npu.u_ser.state','u_npu.blk_rst_n')]),
        unknown([f(n) for n in ('u_scrub.cnt[0]','u_scrub.cnt[2]')]),
        '('+f('u_npu.rvalid_o')+" === 1'b1 && "+unknown([f('s_rdata_npu'),f('u_npu.err_o')])+')',
        '('+f(CORE+'wb_stage_i.g_writeback_stage.wb_valid_q')+" === 1'b1 && "+unknown([f(CORE+'cs_registers_i.pc_wb_i')])+')']
    lines=['  // NSSOC_TRACE_BEGIN: read-only observation; original design/bench statements retained.',
           '  wire [31:0] trace_unknown;',*[f'  assign trace_unknown[{i}] = {check};' for i,check in enumerate(checks)],
           f"  assign trace_unknown[31:{len(checks)}] = 0;",
           f'  nssoc_alu_boot_trace #(.WIDTH({sum(w for _,w in FIELDS)})) trace (',
           '    .clk_i(clk), .cycle_i({32\'b0,cycles}), .signals_i({'+','.join(f(n) for n,_ in FIELDS)+'}),',
           '    .unknown_i(trace_unknown),']
    for port,terminal in [('clocks_i','GCLK'),('enables_i','GATE'),('latched_i','int_fwire_int_GATE'),('delayed_i','delayed_CLK'),('notifier_i','notifier')]:
        lines.append('    .'+port+'({'+','.join(f(n)+'.'+terminal for n in GATES)+'})'+(');' if port=='notifier_i' else ','))
    for bank,name in enumerate(SRAMS):
        path=f(name)+'.i_SRAM_1P_behavioral_bm_bist.'
        lines += ['  always @(posedge '+path+'CLK_MUX)',
            f'    trace.memory_sample({bank},'+','.join(path+t for t in ('MEN_MUX','WEN_MUX','REN_MUX','ADDR_MUX','BM_MUX','DIN_MUX'))+','+f(name)+'.A_DOUT);']
    lines += ['  always @(negedge clk) if(cycles>=1500000 && '+f('g_core_req_reg.u_data_request.valid_q')+" === 1'b1 && "+f('bus_data_addr')+" === 32'h00001e9c)",
        '    trace.milestone($sformatf("CHECKS_REQUEST cycle=%0d time=%0t we=%b be=%h data=%h ram_gnt=%b fabric_push=%b pc=%h stored=%h",cycles,$time,'+
        ','.join(f(n) for n in ('bus_data_we','bus_data_be','bus_data_wdata','u_ram.g_ram_2048x64_ecc.u_ecc.gnt_o','u_bus.push',CORE+'cs_registers_i.pc_wb_i'))+','+
        f(SRAMS[0])+".i_SRAM_1P_behavioral_bm_bist.memory[11'h7a7]));"]
    return '\n'.join(lines)+'\n  // NSSOC_TRACE_END\n'


def instrument(bench):
    q.require(bench.count('endmodule')==1 and 'NSSOC_TRACE_BEGIN' not in bench,'Ambiguous source bench')
    return bench.replace('endmodule',bindings()+'endmodule')


def validate_log(text,directory,*,boot=True):
    matches=re.findall(r'^TRACE_SUMMARY triggered=(\d+) first_cycle=(\d+) triggers=(\d+) samples=(\d+) events=(\d+) saved_samples=(\d+) saved_events=(\d+)$',text,re.M)
    q.require(len(matches)==1,'Missing/duplicate final trace summary')
    values=list(map(int,matches[0]));triggered,cycle,triggers,samples,events,saved,esaved=values
    q.require(triggered in (0,1) and triggers==triggered and samples>0 and events>0,'Trace observer did not execute')
    first=re.findall(r'^TRACE_FIRST_X cycle=(\d+) time=(\d+) cause=(\S+)$',text,re.M)
    q.require(len(first)==triggered and (not triggered or int(first[0][0])==cycle),'First-X receipt differs')
    raw_samples=(directory/'trace-samples.log').read_text().splitlines();raw_events=(directory/'trace-events.log').read_text().splitlines()
    q.require(len(raw_samples)==saved and len(raw_events)==esaved and 0<saved<=2048 and 0<esaved<=4096,'Unbounded/incomplete trace output')
    markers=re.findall(r'^TRACE_MILESTONES count=(\d+)$',text,re.M)
    q.require(len(markers)==1 and int(markers[0])<=1024
              and len((directory/'trace-milestones.log').read_text().splitlines())==int(markers[0]),'Missing/incomplete milestone evidence')
    if boot:
        q.require(samples>=1000 and (not triggered or START<=cycle<=CYCLES+100),'Wrong full replay interval')
        q.require(text.count('QUALIFICATION_MBIST PASS cycles=983043')==1,'Exact original power-on MBIST not witnessed')
    return dict(first_unknown=first[0] if first else None,samples_observed=samples,events_observed=events,
                samples_saved=saved,events_saved=esaved,milestones_saved=int(markers[0]),trace_samples=q.pin(directory/'trace-samples.log'),trace_events=q.pin(directory/'trace-events.log'),trace_milestones=q.pin(directory/'trace-milestones.log'))


def tiny_controls(iverilog,vvp,output):
    output.mkdir()
    rows={}
    for case in ('known','sample_high_bit','masked_unknown','active_unknown','clock_unknown'):
        d=output/case;d.mkdir()
        fault={'known':'','sample_high_bit':"u=32'h80000000;",'masked_unknown':'t.memory_sample(0,1,1,0,0,0,64\'hx,0);',
               'active_unknown':'t.memory_sample(0,1,1,0,0,1,64\'hx,0);','clock_unknown':'badclock=1;'}[case]
        bench=d/'tiny.v';bench.write_text('''`timescale 1ns/1ps
module tiny; reg clk=0;always #5 clk=~clk; reg [63:0] cycle=0;
always @(posedge clk)cycle=cycle+1;reg [31:0]u=0;reg badclock=0;
nssoc_alu_boot_trace #(.WIDTH(8),.START(2),.DEPTH(4),.EVENT_DEPTH(8),.TAIL(4)) t
(.clk_i(clk),.cycle_i(cycle),.signals_i(8'h55),.unknown_i(u),.clocks_i(badclock ? 3'bxxx : {3{clk}}),
.enables_i(3'b111),.latched_i(3'b111),.delayed_i({3{clk}}),.notifier_i(3'bxxx));
initial begin repeat(8)@(negedge clk);#1;'''+fault+'''repeat(8)@(negedge clk);#1;$finish;end
endmodule
''')
        compile_result=q.alu.execute([iverilog,'-g2005-sv','-s','tiny','-o',d/'tiny.vvp',ROOT/MONITOR,bench],d,'compile')
        q.require(compile_result['returncode']==0,'Tiny trace compilation failed')
        run=q.alu.execute([vvp,'-i',d/'tiny.vvp','+trace_dir='+str(d.resolve())],d,'run')
        q.require(run['returncode']==0,'Tiny trace execution failed')
        parsed=validate_log((d/'run.log').read_text(),d,boot=False)
        q.require(bool(parsed['first_unknown'])==(case in ('sample_high_bit','active_unknown','clock_unknown')),'Tiny trace classification failed')
        rows[case]=dict(compile=compile_result,execution=run,observation=parsed)
    return rows


def prepare(output,work,variant):
    q.require(os.environ.get('GITHUB_ACTIONS')=='true','Actual SoC preparation is cloud-only')
    for name,sha in (BASE_PINS|HELPER_PINS).items():
        q.require(q.common.sha(ROOT/name)==sha,'Frozen qualification method changed: '+name)
    q.boot_prepare(output,work,variant,'vendor',None)
    row=json.loads((output/'result.json').read_text())
    try:
        row.update(status='PREPARING_DIAGNOSTIC_TRACE',diagnostic_cycle_bound=CYCLES,original_qualification_cycle_bound=q.CYCLES)
        for name in (*OWN,*HELPER_PINS):
            dest=output/'methods'/name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/name,dest);row['methods'][name]=q.pin(dest)
            if name in HELPER_PINS:q.require(row['methods'][name]['sha256']==HELPER_PINS[name],'Dynamic helper changed during preparation')
        toolroot=work/'oss-cad-suite';row['trace_controls']=tiny_controls(toolroot/'bin/iverilog',toolroot/'bin/vvp',output/'trace-controls')
        net=work/'producer'/('synthesis-'+variant)/'soc_top.netlist.v'
        q.require(q.common.sha(net)==q.EXPECTED_NETLISTS[variant],'Trace netlist differs')
        models={n:(work/'inputs/models'/n).read_text() for n in ('sg13g2_stdcell.v','RM_IHPSG13_1P_2048x64_c2_bm_bist.v','RM_IHPSG13_1P_core_behavioral_bm_bist.v')}
        row['bindings']=validate_bindings(net.read_text(),models);q.common.save(output/'trace-bindings.json',row['bindings'])
        bench=output/'tb_qualification_boot.v';baseline=output/'original-qualified-bench.v';shutil.copyfile(bench,baseline)
        row['original_bench']=q.pin(baseline);row['original_compilation']=row['compile'];row['original_compiled_simulation']=row['compiled_simulation']
        bench.write_text(instrument(baseline.read_text()))
        monitor=output/'alu_boot_trace.v';shutil.copyfile(ROOT/MONITOR,monitor)
        command=row['compile']['command'];q.require(command.count('-DTIMEOUT_CYCLES=3000000')==1,'Original cycle bound differs')
        command=[f'-DTIMEOUT_CYCLES={CYCLES}' if c=='-DTIMEOUT_CYCLES=3000000' else c for c in command]+[str(monitor)]
        row['sources'][str(bench)]=q.pin(bench);row['sources'][str(monitor)]=q.pin(monitor)
        row['compile']=q.alu.execute(command,output,'trace-compile')
        q.require(row['compile']['returncode']==0,'Actual trace binding compilation failed')
        q.require(not re.search(r'warning: Port .*expects .*bits, got', (output/'trace-compile.log').read_text()),'Trace binding port width mismatch')
        row['compiled_simulation']=q.pin(Path(row['compiled_simulation_path']));row['boot_command']+=['+trace_dir='+str(output)]
        for p,pin in row['sources'].items():q.common.verify_file(Path(p),pin)
        row.update(status='COMPILED_SOURCE_BOUND_DIAGNOSTIC_TRACE',scope='Read-only first-X/cycle/clock/SRAM trace; no hardware, workload, model, reset, or clock changes. Diagnostic interval only; no candidate or qualification acceptance.')
    except Exception as error:
        row.update(status='TRACE_PREPARATION_FAILED',error=repr(error));raise
    finally:q.finish(output,row)


def run(output):
    q.require(os.environ.get('GITHUB_ACTIONS')=='true','Actual SoC trace is cloud-only')
    row=json.loads((output/'result.json').read_text())
    try:
        q.require(row['status']=='COMPILED_SOURCE_BOUND_DIAGNOSTIC_TRACE' and row['github_source_commit']==os.environ['GITHUB_SHA'],'Wrong diagnostic checkpoint')
        q.require(row['diagnostic_cycle_bound']==CYCLES and row['original_qualification_cycle_bound']==q.CYCLES
                  and row['cycle_bound']==q.CYCLES and row['producer']==q.PRODUCER
                  and row['variant'] in q.EXPECTED_NETLISTS and row['memory']=='vendor','Changed diagnostic/qualification contract')
        q.require(all(row[n] is False for n in ('candidate_adopted','timing_accepted','manufacturing_approval',
                  'mapped_core_equivalence_accepted','full_soc_functional_accepted')),'Invalid acceptance claim')
        q.verify_outputs(output,row)
        q.require(set(row['methods'])==set(BASE_PINS)|set(HELPER_PINS)|set(OWN),'Incomplete trace methods')
        for name,sha in (BASE_PINS|HELPER_PINS).items():q.require(row['methods'][name]['sha256']==sha,'Changed frozen method')
        for p,pin in row['sources'].items():q.common.verify_file(Path(p),pin)
        q.common.verify_file(Path(row['compiled_simulation_path']),row['compiled_simulation'])
        command=row['boot_command'];q.common.verify_file(Path(command[0]),row['runtime']['tools']['vvp'])
        q.require(command[1:]==['-i',row['compiled_simulation_path'],'+flash0='+str(output/'firmware/flash0.hex'),'+trace_dir='+str(output)],'Trace command changed')
        row['status']='RUNNING_SOURCE_BOUND_DIAGNOSTIC_TRACE';q.common.save(output/'result.json',row)
        env=os.environ.copy()
        for key in ('GH_TOKEN','GITHUB_TOKEN','PYTHONPATH','PYTHONHOME'):env.pop(key,None)
        start=time.monotonic()
        with (output/'boot.log').open('x') as log:
            child=subprocess.Popen(command,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,bufsize=1,env=env,stdin=subprocess.DEVNULL)
            for line in child.stdout:log.write(line);log.flush();print(line,end='',flush=True)
            code=child.wait()
        row['boot_execution']=dict(command=command,returncode=code,elapsed_s=time.monotonic()-start)
        row['trace_observation']=validate_log((output/'boot.log').read_text(),output)
        row['observed_boot_pass']=q.passed_boot(code,(output/'boot.log').read_text())
        for p,pin in row['sources'].items():q.common.verify_file(Path(p),pin)
        q.common.verify_file(Path(row['compiled_simulation_path']),row['compiled_simulation'])
        row.update(status='DIAGNOSTIC_CAPTURE_COMPLETE_NOT_ACCEPTANCE',boot_failure_preserved=not row['observed_boot_pass'])
    except Exception as error:
        row.update(status='TRACE_FAILED_OR_INCOMPLETE',error=repr(error));raise
    finally:q.finish(output,row)


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('phase',choices=('prepare','run'))
    parser.add_argument('--output',type=Path,required=True);parser.add_argument('--work',type=Path)
    parser.add_argument('--variant',choices=('original','candidate'));args=parser.parse_args()
    if args.phase=='run':run(args.output.resolve())
    else:
        q.require(args.work is not None and args.variant is not None,'Preparation arguments missing')
        prepare(args.output.resolve(),args.work.resolve(),args.variant)


if __name__=='__main__':main()
