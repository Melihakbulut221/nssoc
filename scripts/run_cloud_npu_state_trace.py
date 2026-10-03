#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Paired, read-only scalar NPU state observations; unchanged 3M boot contract."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import time

import run_cloud_alu_boot_trace as old

q=old.q
ROOT=Path(__file__).resolve().parents[1]
MONITOR='hw/soc/tb/npu_state_event_trace.v'
OWN=('scripts/run_cloud_npu_state_trace.py',MONITOR,'sw/tests/test_npu_state_trace.py',
     '.github/workflows/timing-npu-state-trace.yml')
PINS=old.BASE_PINS|old.HELPER_PINS|{
 'scripts/run_cloud_alu_boot_trace.py':'a1a47d79de7893ef69bafe290b49fc68afcd68e5af106c987750cf536c48a5f2',
 'hw/soc/tb/alu_boot_trace.v':'3cd442dcc7828c5579019d8ac8884ed220b814d5e979cd8e86d713eca2ea10fc',
 'sw/tests/test_alu_boot_trace.py':'d303f420c342895f7a136fd49077821732c09509b605fc5cd7670e3566444674',
 '.github/workflows/timing-alu-boot-trace.yml':'524516ba46e1437eb3ce270c73c89d49b55a1054f77c1f22359426f9336e4e7b'}
START,LAST,MAX_EVENTS=1569360,1569520,20000
FIELDS=('D','Q','CLK','RESET_B','delayed_D','delayed_CLK','delayed_RESET_B',
        'notifier','int_fwire_IQ','int_fwire_r','xcr_0')
CELLS={'original':tuple(f'_{n}_' for n in range(130766,130770)),
       'candidate':tuple(f'_{n}_' for n in range(131361,131365))}
MODEL_SHA='28343754a828972d614c15b7db27892e92a8c16e49fc06ed69d858a659942ed4'
PRIOR=dict(run_id=37071773733,source_commit='c7ffba6373529530bf208e58dc9d1bf66eb1182b',
           first_candidate_unknown_cycle=1569431,candidate_boot_failed=True)


def model_contract(model):
    q.require(hashlib.sha256(model.encode()).hexdigest()==MODEL_SHA,'Native standard-cell model changed')
    found=re.findall(r'module sg13g2_dfrbpq_1 \(Q, D, RESET_B, CLK\);.*?endmodule',model,re.S)
    q.require(len(found)==1,'Ambiguous native DFF model')
    body=found[0]
    declared=set()
    for declaration in re.findall(r'\b(?:input|output|wire|reg)\s+([^;]+);',body):
        declared.update(x.strip() for x in declaration.split(','))
    q.require(set(FIELDS)<=declared,'Unbound native internal observation')
    for token in ('ihp_dff_r_err (xcr_0, delayed_CLK, delayed_D, int_fwire_r);',
                  'ihp_dff_r (int_fwire_IQ, notifier, delayed_CLK, delayed_D, int_fwire_r, xcr_0);',
                  'buf (Q, int_fwire_IQ);'):
        q.require(token in body,'Native UDP relation differs')
    return body


def bind(netlist,model,variant):
    q.require(variant in CELLS,'Unknown variant')
    q.require(hashlib.sha256(netlist.encode()).hexdigest()==q.EXPECTED_NETLISTS[variant],
              'Source netlist differs')
    body=model_contract(model)
    # Resolve retained state bits through the same exact source witness which
    # identified the first real X; no state-name guessing or cutpoint assumption.
    witness=old.alias_driver_witness(netlist,{'sg13g2_stdcell.v':model})
    observed=witness['fields']['u_npu.ev_state']
    cells={};signals=[];excerpts={}
    all_cells=list(re.finditer(r'^  (\w+) (\\\S+ |\w+) \(\n(.*?)^  \);',netlist,re.M|re.S))
    outputs={}
    for module in re.finditer(r'\bmodule\s+(sg13g2_\w+)\s*\(.*?endmodule',model,re.S):
        outputs[module[1]]={p.strip() for decl in re.findall(r'\boutput\s+([^;]+);',module[0]) for p in decl.split(',')}
    for bit,name in enumerate(CELLS[variant]):
        q.require(observed[str(bit)]==dict(kind='native_output',cell_type='sg13g2_dfrbpq_1',instance=name,port='Q'),
                  'Retained state/native DFF pairing differs')
        found=[m for m in all_cells if m[2].strip()==name]
        q.require(len(found)==1 and found[0][1]=='sg13g2_dfrbpq_1','Native state cell differs')
        ports=re.findall(r'\.([A-Za-z_]\w*)\(([^()]+)\)',found[0][3])
        q.require(len(ports)==4 and set(dict(ports))=={'D','Q','CLK','RESET_B'},'Native state pin contract differs')
        cells[name]=dict(state_bit=bit,ports=dict(ports),source=found[0][0])
        for field in FIELDS:
            signals.append(dict(index=len(signals),state_bit=bit,field=field,expression=f'dut.{name}.{field}'))
        # Small direct-driver excerpts help diagnose the next observed unknown.
        # This is a source excerpt, not a claim of complete cone equivalence.
        nets={dict(ports)[p].strip() for p in ('D','CLK','RESET_B')}
        excerpts[name]=[m[0] for m in all_cells if any(e.strip() in nets and port in outputs.get(m[1],set())
                         for port,e in re.findall(r'\.([A-Za-z_]\w*)\(([^()]+)\)',m[3]))]
        q.require(len(excerpts[name])<=3,'Ambiguous direct input driver excerpts')
    return dict(schema=1,variant=variant,netlist_sha256=q.EXPECTED_NETLISTS[variant],model_sha256=MODEL_SHA,
        native_dff_model=body,cells=cells,signals=signals,connected_cell_excerpts=excerpts,
        sample_encoding='Binary per scalar and complete 44-bit snapshot; signal index zero is the least significant packed bit.',
        sequence_scope='Observed scheduler execution order; not a simulator-internal delta index.')


def instrument(bench,binding):
    q.require(bench.count('endmodule')==1 and 'NSSOC_NPU_STATE_TRACE_BEGIN' not in bench,'Ambiguous original bench')
    signals=binding['signals']
    q.require([s['index'] for s in signals]==list(range(44)),'Incomplete scalar inventory')
    q.require(all(re.fullmatch(r'dut\._\d+_\.[A-Za-z_]\w*',s['expression']) for s in signals),'Unsafe scalar expression')
    addition='\n  // NSSOC_NPU_STATE_TRACE_BEGIN: read-only source-bound observations.\n'
    addition+=f'  nssoc_npu_state_event_trace #(.WIDTH(44),.START({START}),.LAST({LAST}),.MAX_EVENTS({MAX_EVENTS})) npu_state_trace (\n'
    addition+="    .clk_i(clk),.cycle_i({32'b0,cycles}),.signals_i({"+','.join(s['expression'] for s in reversed(signals))+'}));\n'
    addition+='  // NSSOC_NPU_STATE_TRACE_END\n'
    return bench.replace('endmodule',addition+'endmodule')


def parse(log,directory,start=START,last=LAST,width=44,max_events=MAX_EVENTS):
    matches=re.findall(r'^NPU_STATE_TRACE_SUMMARY start=(\d+) last=(\d+) width=(\d+) events=(\d+) samples=(\d+) sequence=(\d+) final_cycle=(\d+)$',log,re.M)
    q.require(len(matches)==1,'Missing/duplicate scalar summary')
    a,b,w,events,samples,total,final=map(int,matches[0])
    q.require((a,b,w)==(start,last,width) and final>last and samples==last-start+1 and 0<events<=max_events
              and total==events+samples,'Incomplete/unbounded scalar window')
    raw=(Path(directory)/'npu-state-events.log').read_text().splitlines()
    q.require(len(raw)==total,'Incomplete scalar event file')
    sample_cycles=[];event_count=0;previous_time=-1;unknowns=[]
    for seq,line in enumerate(raw,1):
        m=re.fullmatch(r'(EV|S) seq=(\d+) cycle=(\d+) realtime_ns=(\d+\.\d{3})(?: signal=(\d+) value=([01xz]))? all=([01xz]+)',line)
        q.require(m is not None and int(m[2])==seq and start<=int(m[3])<=last and len(m[7])==width,'Invalid scalar record')
        now=int(m[4].replace('.',''));q.require(now>=previous_time,'Scalar time moved backwards');previous_time=now
        if m[1]=='S':
            q.require(m[5] is None,'Sample contains event index');sample_cycles.append(int(m[3]))
        else:
            q.require(m[5] is not None and 0<=int(m[5])<width,'Scalar index outside bound')
            q.require(m[7][-1-int(m[5])]==m[6],'Scalar value differs from binary snapshot')
            event_count+=1
            if m[6] in 'xz':unknowns.append(dict(sequence=seq,cycle=int(m[3]),realtime_ns=m[4],signal=int(m[5]),value=m[6]))
    q.require(event_count==events and sample_cycles==list(range(start,last+1)),'Missing/duplicate scalar cycle coverage')
    return dict(start=start,last=last,width=width,events=events,samples=samples,sequence=total,
        final_cycle=final,unknown_scalar_events=unknowns,raw_event_file=q.pin(Path(directory)/'npu-state-events.log'))


def tiny_controls(iverilog,vvp,model,output):
    """Exact native four-cell preflight; actual chip never runs in this function."""
    output=Path(output);output.mkdir();model=Path(model);model_contract(model.read_text())
    results={}
    for case in ('known','bit0_unknown','bit3_unknown'):
        root=output/case;root.mkdir();celltext=[];signals=[]
        for bit in range(4):
            name=f'_{100+bit}_'
            celltext.append(f'sg13g2_dfrbpq_1 {name}(.Q(q[{bit}]),.D(d[{bit}]),.CLK(clk),.RESET_B(rst));')
            signals += [f'{name}.{field}' for field in FIELDS]
        change={'known':"d=4'b1010;",'bit0_unknown':"d=4'b000x;",'bit3_unknown':"d=4'bx000;"}[case]
        source=root/'tiny.v'
        monitor_instance='nssoc_npu_state_event_trace #(.WIDTH(44),.START(2),.LAST(7),.MAX_EVENTS(20000)) trace('+".clk_i(clk),.cycle_i({32'b0,cycles}),.signals_i({"+','.join(reversed(signals))+'}));\n'
        source.write_text('`timescale 1ns/1ps\nmodule tiny;reg clk=0,rst=0;reg[3:0] d=0;wire[3:0]q;integer cycles=0;\n'
            +'\n'.join(celltext)+'\nalways #5 clk=~clk;always @(posedge clk)cycles=cycles+1;\n'
            +monitor_instance
            +'always @(negedge clk) #0.002 $display("SIGNATURE cycle=%0d q=%b",cycles,q);\n'
            +'initial begin #2;rst=1;#18;'+change+'#10;d=4\'b0101;#60;$display("TINY_FINAL q=%b",q);$finish;end\nendmodule\n')
        compiled=q.alu.execute([iverilog,'-g2005-sv','-DFUNCTIONAL','-s','tiny','-o',root/'sim.vvp',source,ROOT/MONITOR,model],root,'compile')
        q.require(compiled['returncode']==0,'Native scalar control compile failed')
        executed=q.alu.execute([vvp,'-i',root/'sim.vvp','+npu_trace_dir='+str(root)],root,'run')
        q.require(executed['returncode']==0,'Native scalar control failed')
        text=(root/'run.log').read_text();observed=parse(text,root,2,7)
        q.require(text.count('TINY_FINAL q=0101')==1,'Observer changed native DFF behavior')
        unknown_q={e['signal']//len(FIELDS) for e in observed['unknown_scalar_events'] if e['signal']%len(FIELDS)==FIELDS.index('Q')}
        q.require(unknown_q==({'bit0_unknown':{0},'bit3_unknown':{3}}.get(case,set())),'Native scalar bit distinction differs')
        baseline=root/'baseline.v';baseline.write_text(source.read_text().replace(monitor_instance,''))
        bc=q.alu.execute([iverilog,'-g2005-sv','-DFUNCTIONAL','-s','tiny','-o',root/'baseline.vvp',baseline,model],root,'baseline-compile')
        q.require(bc['returncode']==0,'Uninstrumented native control compile failed')
        br=q.alu.execute([vvp,'-i',root/'baseline.vvp'],root,'baseline-run')
        q.require(br['returncode']==0 and re.findall(r'^SIGNATURE.*$',text,re.M)==re.findall(r'^SIGNATURE.*$',(root/'baseline-run.log').read_text(),re.M),'Observer altered native control output trajectory')
        results[case]=dict(compile=compiled,execution=executed,observation=observed,unknown_q_bits=sorted(unknown_q),baseline_compile=bc,baseline_execution=br,native_output_trajectory_unchanged=True)
    return results


def prepare(output,work,variant):
    q.require(os.environ.get('GITHUB_ACTIONS')=='true','Actual SoC preparation is cloud-only')
    for name,sha in PINS.items():q.require(q.common.sha(ROOT/name)==sha,'Frozen dependency changed: '+name)
    q.boot_prepare(output,work,variant,'vendor',None)
    row=json.loads((output/'result.json').read_text())
    try:
        row.update(status='PREPARING_NPU_SCALAR_TRACE',prior_trace=PRIOR,window=dict(start=START,last=LAST,max_events=MAX_EVENTS))
        for name in (*PINS,*OWN):
            dest=output/'methods'/name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/name,dest);row['methods'][name]=q.pin(dest)
        tools=work/'oss-cad-suite/bin';model=work/'inputs/models/sg13g2_stdcell.v'
        row['scalar_controls']=tiny_controls(tools/'iverilog',tools/'vvp',model,output/'scalar-controls')
        net=work/'producer'/('synthesis-'+variant)/'soc_top.netlist.v'
        binding=bind(net.read_text(),model.read_text(),variant);row['scalar_bindings']=binding
        q.common.save(output/'scalar-bindings.json',binding)
        bench=output/'tb_qualification_boot.v';baseline=output/'original-qualified-bench.v';shutil.copyfile(bench,baseline)
        row['original_bench']=q.pin(baseline);row['original_compilation']=row['compile'];row['original_compiled_simulation']=row['compiled_simulation']
        bench.write_text(instrument(baseline.read_text(),binding));monitor=output/'npu_state_event_trace.v';shutil.copyfile(ROOT/MONITOR,monitor)
        command=row['compile']['command']+[str(monitor)]
        q.require(command.count('-DTIMEOUT_CYCLES=3000000')==1 and row['cycle_bound']==3000000,'Original qualification bound changed')
        row['sources'][str(bench)]=q.pin(bench);row['sources'][str(monitor)]=q.pin(monitor)
        row['compile']=q.alu.execute(command,output,'scalar-compile')
        q.require(row['compile']['returncode']==0,'Source-bound native scalar compile failed')
        q.require(not re.search(r'warning: Port .*expects .*bits, got',(output/'scalar-compile.log').read_text()),'Scalar port width mismatch')
        row['compiled_simulation']=q.pin(Path(row['compiled_simulation_path']));row['boot_command']+=['+npu_trace_dir='+str(output)]
        for p,pin in row['sources'].items():q.common.verify_file(Path(p),pin)
        row.update(status='COMPILED_NPU_SCALAR_TRACE_NO_ACCEPTANCE',scope='Unchanged 3M boot workload and native models; read-only paired scalar window. No RTL repair, equivalence, timing or adoption claim.')
    except Exception as error:row.update(status='NPU_TRACE_PREPARATION_FAILED',error=repr(error));raise
    finally:q.finish(output,row)


def run(output):
    q.require(os.environ.get('GITHUB_ACTIONS')=='true','Actual SoC trace is cloud-only')
    row=json.loads((output/'result.json').read_text())
    try:
        q.require(row['status']=='COMPILED_NPU_SCALAR_TRACE_NO_ACCEPTANCE' and row['github_source_commit']==os.environ['GITHUB_SHA'],'Wrong scalar checkpoint')
        q.require(row['cycle_bound']==3000000 and row['prior_trace']==PRIOR and row['window']==dict(start=START,last=LAST,max_events=MAX_EVENTS),'Changed scalar scope')
        q.require(row['producer']==q.PRODUCER and row['variant'] in CELLS and row['memory']=='vendor','Changed input variant')
        flags=('candidate_adopted','timing_accepted','manufacturing_approval','mapped_core_equivalence_accepted','full_soc_functional_accepted')
        q.require(all(row[k] is False for k in flags),'Unexpected acceptance')
        q.verify_outputs(output,row)
        q.require(set(row['methods'])==set(PINS)|set(OWN),'Missing scalar methods')
        for name,sha in PINS.items():q.require(row['methods'][name]['sha256']==sha,'Frozen source changed')
        q.require(row['scalar_bindings']==json.loads((output/'scalar-bindings.json').read_text()),'Native bindings changed')
        q.require(instrument((output/'original-qualified-bench.v').read_text(),row['scalar_bindings'])==(output/'tb_qualification_boot.v').read_text(),'Instrumentation changed original statements')
        for p,pin in row['sources'].items():q.common.verify_file(Path(p),pin)
        q.common.verify_file(Path(row['compiled_simulation_path']),row['compiled_simulation'])
        command=row['boot_command'];q.common.verify_file(Path(command[0]),row['runtime']['tools']['vvp'])
        q.require(command[1:]==['-i',row['compiled_simulation_path'],'+flash0='+str(output/'firmware/flash0.hex'),'+npu_trace_dir='+str(output)],'Native command differs')
        row['status']='RUNNING_NPU_SCALAR_TRACE';q.common.save(output/'result.json',row)
        env=os.environ.copy()
        for key in ('GH_TOKEN','GITHUB_TOKEN','PYTHONPATH','PYTHONHOME'):env.pop(key,None)
        start=time.monotonic()
        with (output/'boot.log').open('x') as log:
            child=subprocess.Popen(command,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,bufsize=1,env=env,stdin=subprocess.DEVNULL)
            for line in child.stdout:log.write(line);log.flush();print(line,end='',flush=True)
            code=child.wait()
        row['boot_execution']=dict(command=command,returncode=code,elapsed_s=time.monotonic()-start)
        text=(output/'boot.log').read_text();row['scalar_observation']=parse(text,output)
        q.require(text.count('QUALIFICATION_MBIST PASS cycles=983043')==1,'Original MBIST not observed')
        row['observed_boot_pass']=q.passed_boot(code,text)
        for p,pin in row['sources'].items():q.common.verify_file(Path(p),pin)
        q.common.verify_file(Path(row['compiled_simulation_path']),row['compiled_simulation'])
        row.update(status='NPU_SCALAR_CAPTURE_COMPLETE_NOT_ACCEPTANCE',boot_failure_preserved=not row['observed_boot_pass'])
    except Exception as error:row.update(status='NPU_TRACE_FAILED_OR_INCOMPLETE',error=repr(error));raise
    finally:q.finish(output,row)


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('phase',choices=('prepare','run'))
    p.add_argument('--output',type=Path,required=True);p.add_argument('--work',type=Path);p.add_argument('--variant',choices=tuple(CELLS));args=p.parse_args()
    if args.phase=='run':run(args.output.resolve())
    else:
        q.require(args.work is not None and args.variant is not None,'Missing preparation inputs');prepare(args.output.resolve(),args.work.resolve(),args.variant)


if __name__=='__main__':main()
