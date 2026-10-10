#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Read-only bounded next-state cones; original models, firmware and 3M boot."""
import argparse
import json
import os
from pathlib import Path
import re
import resource
import shutil
import subprocess
import time

import run_cloud_npu_state_trace as old

q=old.q
ROOT=Path(__file__).resolve().parents[1]
MONITOR='hw/soc/tb/npu_cone_event_trace.v'
OWN=('scripts/run_cloud_npu_cone_trace.py',MONITOR,'sw/tests/test_npu_cone_trace.py',
     '.github/workflows/timing-npu-cone-trace.yml')
PINS=old.PINS|{
 'scripts/run_cloud_npu_state_trace.py':'c877425001c16eae37c85f69bfd8ed6f457e7fde3501586532efee60e9a23e14',
 'hw/soc/tb/npu_state_event_trace.v':'909131caa1d65d3554846f11daff0f9538474ffaa3ae2acf1d720a120f5eec9b',
 'sw/tests/test_npu_state_trace.py':'6b693e274a1a1e0a3915738ea6faec44cc62252d90cdef30af86ce99a9cc6ba7',
 '.github/workflows/timing-npu-state-trace.yml':'3dba8c0537b1e0ff81ea2cc58d55a76e7b3a1320639907c0298302ad6a6c8808'}
START,LAST=old.START,old.LAST
DEPTH,MAX_CELLS,MAX_SIGNALS,MAX_EVENTS=2,40,512,50000
PRIOR=dict(run_id=37102953988,source_commit='14f5b2f38ce6040433b888b3522800b1b264a04d',
           first_candidate_data_unknown=1569430,first_candidate_q_unknown=1569431)
ROOT_BODIES={
 'original':(
 '  sg13g2_mux2_1 _106857_ (\n    .A0(_047080_),\n    .A1(\\u_npu.ev_state [0]),\n    .S(_047086_),\n    .X(_005305_)\n  );',
 '  sg13g2_or2_1 _106872_ (\n    .A(_047084_),\n    .B(_047098_),\n    .X(_005308_)\n  );'),
 'candidate':(
 '  sg13g2_o21ai_1 _107542_ (\n    .A1(_026978_),\n    .A2(_047302_),\n    .B1(_047305_),\n    .Y(_005304_)\n  );',
 '  sg13g2_o21ai_1 _107556_ (\n    .A1(_026979_),\n    .A2(_047302_),\n    .B1(_047316_),\n    .Y(_005307_)\n  );')}


def native_modules(model):
    old.model_contract(model)
    modules={}
    for m in re.finditer(r'\bmodule\s+(sg13g2_\w+)\s*\(.*?endmodule',model,re.S):
        ports={direction:[x.strip() for decl in re.findall(r'\b'+direction+r'\s+([^;]+);',m[0]) for x in decl.split(',')]
               for direction in ('input','output')}
        fields=[x.strip() for decl in re.findall(r'\b(?:input|output|wire|reg)\s+([^;]+);',m[0]) for x in decl.split(',')]
        q.require(all(re.fullmatch(r'[A-Za-z_]\w*',x) for x in fields),'Non-scalar native field')
        modules[m[1]]=dict(**ports,fields=sorted(set(fields)),body=m[0],
                          sequential=bool(re.search(r'\bihp_(?:dff|latch)',m[0])))
    return modules


def native_cells(netlist):
    result={}
    for m in re.finditer(r'^  (\w+) (\\\S+ |\w+) \(\n(.*?)^  \);',netlist,re.M|re.S):
        name=m[2].strip().removeprefix('\\');pairs=re.findall(r'\.([A-Za-z_]\w*)\(([^()]+)\)',m[3])
        q.require(name not in result and len(dict(pairs))==len(pairs),'Duplicate native cell or port')
        result[name]=dict(type=m[1],ports=dict(pairs),source=m[0])
    return result


def net_key(expression):
    # Exact syntactic conductor identity; aliases are recorded at a frontier,
    # never silently guessed or turned into an observation cutpoint.
    return expression.strip()


def expression(instance,field):
    q.require(re.fullmatch(r'[A-Za-z_][A-Za-z0-9_.$\[\]]*',instance) is not None
              and re.fullmatch(r'[A-Za-z_]\w*',field) is not None,'Unsafe native observation')
    name=instance if re.fullmatch(r'[A-Za-z_]\w*',instance) else '\\'+instance+' '
    return 'dut.'+name+'.'+field


def bind(netlist,model,variant):
    base=old.bind(netlist,model,variant)  # checks exact full netlist/model and all 441 retained aliases
    modules=native_modules(model);cells=native_cells(netlist);drivers={}
    for name,cell in cells.items():
        if cell['type'] not in modules:continue
        for port in modules[cell['type']]['output']:
            q.require(port in cell['ports'],'Missing native output connection')
            drivers.setdefault(net_key(cell['ports'][port]),[]).append(dict(instance=name,port=port))
    roots=[]
    for bit,body in zip((0,3),ROOT_BODIES[variant],strict=True):
        matches=[name for name,c in cells.items() if c['source']==body]
        q.require(len(matches)==1,'Exact captured D root changed')
        root=matches[0];d=base['cells'][old.CELLS[variant][bit]]['ports']['D']
        q.require(drivers.get(net_key(d))==[dict(instance=root,port=modules[cells[root]['type']]['output'][0])],
                  'D root no longer uniquely drives the state input')
        roots.append(root)
    queue=[(name,0) for name in roots];selected={};frontier=[];connections=[]
    while queue:
        name,depth=queue.pop(0)
        if name in selected:continue
        q.require(len(selected)<MAX_CELLS,'Cone cell budget exceeded')
        cell=cells[name];module=modules[cell['type']]
        q.require(set(cell['ports'])==set(module['input'])|set(module['output']),'Incomplete native cone port map')
        selected[name]=dict(**cell,depth=depth,sequential=module['sequential'],model=module['body'])
        for port in module['input']:
            expr=cell['ports'][port];sources=drivers.get(net_key(expr),[])
            q.require(len(sources)<=1,'Ambiguous cone conductor driver')
            item=dict(sink=name,port=port,conductor=expr,sources=sources)
            connections.append(item)
            reason=('sequential_boundary' if module['sequential'] else 'depth_boundary' if depth==DEPTH
                    else 'source_not_native_direct_output' if not sources else None)
            if reason:frontier.append(dict(**item,reason=reason))
            else:queue.append((sources[0]['instance'],depth+1))
    shared=None
    if variant=='candidate':
        q.require(all(cells[name]['ports']['A2']=='_047302_' for name in roots),'Shared candidate root input changed')
        sources=drivers.get('_047302_',[])
        q.require(len(sources)==1 and sources[0]['instance'] in selected,'Shared control producer not captured')
        shared=dict(conductor='_047302_',**sources[0])
    signals=[dict(s,role='state_register') for s in base['signals']];seen={s['expression'] for s in signals}
    for name,cell in selected.items():
        for field in modules[cell['type']]['fields']:
            expr=expression(name,field)
            if expr in seen:continue
            seen.add(expr);signals.append(dict(index=len(signals),instance=name,field=field,expression=expr,role='cone'))
    q.require(len(signals)<=MAX_SIGNALS,'Cone scalar budget exceeded')
    return dict(schema=1,variant=variant,netlist_sha256=q.EXPECTED_NETLISTS[variant],model_sha256=old.MODEL_SHA,
        state_binding=base,roots=roots,shared_candidate_control=shared,cells=selected,connections=connections,
        frontier=frontier,signals=signals,depth=DEPTH,max_cells=MAX_CELLS,max_signals=MAX_SIGNALS,
        scope='Exact source-bound native pin/internal scalar observations; frontier records are observation limits, not logical assumptions or design modifications.')


def instrument(bench,binding,start=START,last=LAST):
    q.require(bench.count('endmodule')==1 and 'NSSOC_NPU_CONE_BEGIN' not in bench,'Ambiguous baseline bench')
    signals=binding['signals'];q.require([s['index'] for s in signals]==list(range(len(signals))) and 0<len(signals)<=MAX_SIGNALS,'Invalid scalar inventory')
    for s in signals:
        if s['role']=='state_register':
            q.require(s['expression'] in {x['expression'] for x in binding['state_binding']['signals']},'Unbound state scalar')
        else:q.require(s['expression']==expression(s['instance'],s['field']) and s['instance'] in binding['cells']
                       and re.search(r'\b'+re.escape(s['field'])+r'\b',binding['cells'][s['instance']]['model']), 'Unbound cone scalar')
    add='\n  // NSSOC_NPU_CONE_BEGIN: read-only exact source-bound observations.\n'
    add+=f'  nssoc_npu_cone_event_trace #(.WIDTH({len(signals)}),.START({start}),.LAST({last}),.MAX_EVENTS({MAX_EVENTS})) npu_cone (\n'
    add+="    .clk_i(clk),.cycle_i({32'b0,cycles}),.signals_i({"+','.join(s['expression'] for s in reversed(signals))+'}));\n'
    return bench.replace('endmodule',add+'  // NSSOC_NPU_CONE_END\nendmodule')


def parse(log,directory,start=START,last=LAST,width=None,max_events=MAX_EVENTS):
    matches=re.findall(r'^NPU_CONE_SUMMARY start=(\d+) last=(\d+) width=(\d+) events=(\d+) samples=(\d+) sequence=(\d+) final_cycle=(\d+) armed=1$',log,re.M)
    q.require(len(matches)==1,'Missing/duplicate complete cone summary')
    a,b,w,events,samples,total,final=map(int,matches[0]);width=w if width is None else width
    q.require((a,b,w)==(start,last,width) and 0<w<=MAX_SIGNALS and final>last and samples==last-start+1
              and 0<events<=max_events and total==events+samples+1,'Incomplete cone window')
    lines=(Path(directory)/'npu-cone-events.log').read_text().splitlines();q.require(len(lines)==total,'Incomplete cone records')
    previous=None;event_count=0;sample_cycles=[];previous_time=-1;unknown=[];initial=None
    for seq,line in enumerate(lines,1):
        m=re.fullmatch(r'(INIT|EV|S) seq=(\d+) cycle=(\d+) realtime_ns=(\d+\.\d{3})(?: signal=(\d+) prior=([01xz]) value=([01xz]))? all=([01xz]+)',line)
        q.require(m is not None and int(m[2])==seq and len(m[8])==width,'Invalid cone record')
        cycle=int(m[3]);now=int(m[4].replace('.',''));q.require(now>=previous_time,'Cone time moved backwards');previous_time=now
        if seq==1:
            q.require(m[1]=='INIT' and cycle==start-1 and m[5] is None,'Missing initial static snapshot')
            previous=list(m[8][::-1]);initial=[dict(signal=i,value=v) for i,v in enumerate(previous) if v in 'xz'];continue
        q.require(m[1]!='INIT' and start-1<=cycle<=last,'Unexpected initialization/window')
        if m[1]=='S':
            q.require(m[5] is None and list(m[8][::-1])==previous,'Sample differs from complete scalar transition history')
            sample_cycles.append(cycle)
        else:
            q.require(m[5] is not None and 0<=int(m[5])<width,'Invalid scalar index')
            index=int(m[5]);prior=m[6];value=m[7]
            q.require(previous[index]==prior and prior!=value and m[8][-1-index]==value,'Invalid prior/new scalar transition')
            previous[index]=value;event_count+=1
            if value in 'xz':unknown.append(dict(sequence=seq,cycle=cycle,realtime_ns=m[4],signal=index,prior=prior,value=value))
    q.require(event_count==events and sample_cycles==list(range(start,last+1)),'Missing event or sample coverage')
    return dict(start=start,last=last,width=width,events=events,samples=samples,sequence=total,final_cycle=final,
        initialization_cycle=start-1,event_cycle_bounds=[start-1,last],initial_static_unknowns=initial,new_unknown_transitions=unknown,first_new_unknown=unknown[0] if unknown else None,
        raw_event_file=q.pin(Path(directory)/'npu-cone-events.log'))


def tiny_execute(command,root,label):
    def bound():
        resource.setrlimit(resource.RLIMIT_AS,(2*1024**3,2*1024**3));resource.setrlimit(resource.RLIMIT_CORE,(0,0))
    env=os.environ.copy()
    for key in ('GH_TOKEN','GITHUB_TOKEN','PYTHONPATH','PYTHONHOME'):env.pop(key,None)
    command=list(map(str,command));start=time.monotonic()
    with (root/(label+'.log')).open('w') as log:
        result=subprocess.run(command,cwd=root,stdout=log,stderr=subprocess.STDOUT,env=env,preexec_fn=bound,check=False)
    return dict(command=command,returncode=result.returncode,seconds=time.monotonic()-start,memory_bytes=2*1024**3,log=q.pin(root/(label+'.log')))


def tiny_controls(iverilog,vvp,model,output):
    output=Path(output);output.mkdir();model=Path(model);old.model_contract(model.read_text());rows={}
    for case in ('known','static_x_masked','shared_input_x','latent_x_unmasked','coalesced_pulse'):
        root=output/case;root.mkdir()
        # Real combinational root and real native DFF; no force/UDP substitution.
        values={'known':("1'b0","a=0;b=1;"),'static_x_masked':("1'bx","a=1;b=1;"),'shared_input_x':("1'b0","s=1'bx;"),'latent_x_unmasked':("1'bx","a=0;"),'coalesced_pulse':("1'b0","s=1;s=0;")}[case]
        monitor='nssoc_npu_cone_event_trace #(.WIDTH(5),.START(2),.LAST(7)) obs(.clk_i(clk),.cycle_i({32\'b0,cycles}),.signals_i({ff.Q,root.Y,root.B1,root.A2,root.A1}));\n'
        text='''`timescale 1ns/1ps
module tiny;reg clk=0,rst=0;integer cycles=0;reg a=0,s='''+values[0]+''',b=1;wire d,q;
always #5 clk=~clk;always @(posedge clk)cycles=cycles+1;
sg13g2_o21ai_1 root(.A1(a),.A2(s),.B1(b),.Y(d));
sg13g2_dfrbpq_1 ff(.D(d),.Q(q),.CLK(clk),.RESET_B(rst));
'''+monitor+'''always @(negedge clk) #0.002 $display("SIGNATURE cycle=%0d d=%b q=%b",cycles,d,q);
initial begin #2;rst=1;'''+('a=1;' if case in ('static_x_masked','latent_x_unmasked') else '')+'''#28;'''+values[1]+'''#20;a=1;s=0;#40;$finish;end
endmodule
'''
        source=root/'tiny.v';source.write_text(text);cc=tiny_execute([iverilog,'-g2005-sv','-DFUNCTIONAL','-s','tiny','-o',root/'tiny.vvp',source,ROOT/MONITOR,model],root,'compile')
        q.require(cc['returncode']==0,'Native cone control compile failed')
        rr=tiny_execute([vvp,'-i',root/'tiny.vvp','+npu_cone_dir='+str(root)],root,'run');q.require(rr['returncode']==0,'Native cone control failed')
        log=(root/'run.log').read_text();parsed=parse(log,root,2,7,5)
        new_indices={e['signal'] for e in parsed['new_unknown_transitions']}
        q.require(new_indices==({'shared_input_x':{1,3,4},'latent_x_unmasked':{3,4}}.get(case,set())),'Incorrect native cone X propagation')
        q.require({x['signal'] for x in parsed['initial_static_unknowns']}==({1} if case in ('static_x_masked','latent_x_unmasked') else set()),'Initial static X classification differs')
        baseline=root/'baseline.v';baseline.write_text(text.replace(monitor,''));bc=tiny_execute([iverilog,'-g2005-sv','-DFUNCTIONAL','-s','tiny','-o',root/'baseline.vvp',baseline,model],root,'baseline-compile')
        q.require(bc['returncode']==0,'Native baseline compile failed');br=tiny_execute([vvp,'-i',root/'baseline.vvp'],root,'baseline-run')
        q.require(br['returncode']==0 and re.findall(r'^SIGNATURE.*$',log,re.M)==re.findall(r'^SIGNATURE.*$',(root/'baseline-run.log').read_text(),re.M),'Observer altered actual native D/Q trajectory')
        rows[case]=dict(compile=cc,execution=rr,observation=parsed,baseline_compile=bc,baseline_execution=br,native_output_trajectory_unchanged=True)
    return rows


def prepare(output,work,variant):
    q.require(os.environ.get('GITHUB_ACTIONS')=='true','Actual SoC preparation is cloud-only')
    for name,sha in PINS.items():q.require(q.common.sha(ROOT/name)==sha,'Frozen dependency changed: '+name)
    q.boot_prepare(output,work,variant,'vendor',None);row=json.loads((output/'result.json').read_text())
    try:
        row.update(status='PREPARING_NPU_CONE_TRACE',prior_scalar_trace=PRIOR,window=dict(start=START,last=LAST,max_events=MAX_EVENTS))
        for name in (*PINS,*OWN):
            dest=output/'methods'/name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/name,dest);row['methods'][name]=q.pin(dest)
        tools=work/'oss-cad-suite/bin';model=work/'inputs/models/sg13g2_stdcell.v'
        row['cone_controls']=tiny_controls(tools/'iverilog',tools/'vvp',model,output/'cone-controls')
        net=work/'producer'/('synthesis-'+variant)/'soc_top.netlist.v'
        binding=bind(net.read_text(),model.read_text(),variant);row['cone_bindings']=binding;q.common.save(output/'cone-bindings.json',binding)
        bench=output/'tb_qualification_boot.v';baseline=output/'original-qualified-bench.v';shutil.copyfile(bench,baseline)
        row['original_bench']=q.pin(baseline);row['original_compilation']=row['compile'];row['original_compiled_simulation']=row['compiled_simulation']
        bench.write_text(instrument(baseline.read_text(),binding));monitor=output/'npu_cone_event_trace.v';shutil.copyfile(ROOT/MONITOR,monitor)
        command=row['compile']['command']+[str(monitor)]
        q.require(command.count('-DTIMEOUT_CYCLES=3000000')==1 and row['cycle_bound']==3000000,'Original qualification bound changed')
        row['sources'][str(bench)]=q.pin(bench);row['sources'][str(monitor)]=q.pin(monitor);row['compile']=q.alu.execute(command,output,'cone-compile')
        q.require(row['compile']['returncode']==0 and not re.search(r'warning: Port .*expects .*bits, got',(output/'cone-compile.log').read_text()),'Cone compile failed or width mismatch')
        row['compiled_simulation']=q.pin(Path(row['compiled_simulation_path']));row['boot_command']+=['+npu_cone_dir='+str(output)]
        for path,expected in row['sources'].items():q.common.verify_file(Path(path),expected)
        row.update(status='COMPILED_NPU_CONE_TRACE_NO_ACCEPTANCE',scope='Exact paired next-state input cones; unchanged3M workload/models/reset. No RTL repair or acceptance claim.')
    except Exception as error:row.update(status='NPU_CONE_PREPARATION_FAILED',error=repr(error));raise
    finally:q.finish(output,row)


def run(output):
    q.require(os.environ.get('GITHUB_ACTIONS')=='true','Actual SoC trace is cloud-only');row=json.loads((output/'result.json').read_text())
    try:
        q.require(row['status']=='COMPILED_NPU_CONE_TRACE_NO_ACCEPTANCE' and row['github_source_commit']==os.environ['GITHUB_SHA'],'Wrong cone checkpoint')
        q.require(row['cycle_bound']==3000000 and row['prior_scalar_trace']==PRIOR and row['window']==dict(start=START,last=LAST,max_events=MAX_EVENTS),'Changed cone scope')
        q.require(row['producer']==q.PRODUCER and row['variant'] in ROOT_BODIES and row['memory']=='vendor','Changed input variant')
        flags=('candidate_adopted','timing_accepted','manufacturing_approval','mapped_core_equivalence_accepted','full_soc_functional_accepted')
        q.require(all(row[k] is False for k in flags),'Unexpected acceptance');q.verify_outputs(output,row)
        q.require(set(row['methods'])==set(PINS)|set(OWN),'Missing cone methods')
        for name,sha in PINS.items():q.require(row['methods'][name]['sha256']==sha,'Frozen source changed')
        q.require(row['cone_bindings']==json.loads((output/'cone-bindings.json').read_text()),'Cone bindings changed')
        q.require(instrument((output/'original-qualified-bench.v').read_text(),row['cone_bindings'])==(output/'tb_qualification_boot.v').read_text(),'Instrumentation changed baseline statements')
        for path,expected in row['sources'].items():q.common.verify_file(Path(path),expected)
        q.common.verify_file(Path(row['compiled_simulation_path']),row['compiled_simulation'])
        command=row['boot_command'];q.common.verify_file(Path(command[0]),row['runtime']['tools']['vvp'])
        q.require(command[1:]==['-i',row['compiled_simulation_path'],'+flash0='+str(output/'firmware/flash0.hex'),'+npu_cone_dir='+str(output)],'Native command differs')
        row['status']='RUNNING_NPU_CONE_TRACE';q.common.save(output/'result.json',row);env=os.environ.copy()
        for key in ('GH_TOKEN','GITHUB_TOKEN','PYTHONPATH','PYTHONHOME'):env.pop(key,None)
        start=time.monotonic()
        with (output/'boot.log').open('x') as log:
            child=subprocess.Popen(command,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,bufsize=1,env=env,stdin=subprocess.DEVNULL)
            for line in child.stdout:log.write(line);log.flush();print(line,end='',flush=True)
            code=child.wait()
        row['boot_execution']=dict(command=command,returncode=code,elapsed_s=time.monotonic()-start);text=(output/'boot.log').read_text()
        row['cone_observation']=parse(text,output,width=len(row['cone_bindings']['signals']))
        q.require(text.count('QUALIFICATION_MBIST PASS cycles=983043')==1,'Original MBIST not observed')
        row['observed_boot_pass']=q.passed_boot(code,text)
        for path,expected in row['sources'].items():q.common.verify_file(Path(path),expected)
        q.common.verify_file(Path(row['compiled_simulation_path']),row['compiled_simulation'])
        row.update(status='NPU_CONE_CAPTURE_COMPLETE_NOT_ACCEPTANCE',boot_failure_preserved=not row['observed_boot_pass'])
    except Exception as error:row.update(status='NPU_CONE_FAILED_OR_INCOMPLETE',error=repr(error));raise
    finally:q.finish(output,row)


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('phase',choices=('prepare','run'));parser.add_argument('--output',type=Path,required=True);parser.add_argument('--work',type=Path);parser.add_argument('--variant',choices=tuple(ROOT_BODIES));args=parser.parse_args()
    if args.phase=='run':run(args.output.resolve())
    else:
        q.require(args.work is not None and args.variant is not None,'Missing preparation inputs');prepare(args.output.resolve(),args.work.resolve(),args.variant)


if __name__=='__main__':main()
