#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Source-bound full FIFO write and sync/LIF predecessor observation; unchanged 3M boot."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import resource
import shutil
import subprocess
import time

import run_cloud_npu_evq_trace as previous

q=previous.q
old=previous.old
ROOT=Path(__file__).resolve().parents[1]
LOCK='hw/soc/pnr/npu-write-trace-input.lock.json'
MONITOR='hw/soc/tb/npu_write_event_trace.v'
OWN=('scripts/run_cloud_npu_write_trace.py',MONITOR,LOCK,'sw/tests/test_npu_write_trace.py',
     '.github/workflows/timing-npu-write-trace.yml')
PINS={'scripts/run_cloud_alu_qualification.py': 'cc918fbe661e7cd18f935795a08133c8b5438a256b5f50202195840f544fd429', 'scripts/run_cloud_alu_prefix.py': 'd7b390371a6f2a871b4861edcc6728d0856b9a5736308e5cc84b4bca393e5fea', 'scripts/prepare_alu_prefix.py': 'ae22ae3b8e2206ade9d5f6499bc5c9f032d4143cc9b25eda9427f78500e020b5', 'scripts/run_cloud_eco_logic_proof.py': '093cd8bfedce21561b57c049d935f1a80d3b6a09fd06b673b1ea0c58659f1c6e', 'scripts/run_cloud_timing_experiment.py': '689c4dbd5a036fc1919d25c0d816f1740a878b11d7dfef432ae7e41c31197524', 'scripts/bootstrap_oss.py': 'e721a22cd15131fcce79f0283863f0b6db2accb9c7349324360602e0f1c81277', '.github/workflows/timing-alu-qualification.yml': '777d566224bb3af9667cf997b3797b1b6829e721995bf31809aefafd4fd7352a', 'hw/soc/pnr/alu-qualification-input.lock.json': '5848b42bbdf8817205d629d7db2ef9619f82a62f12d8667fd85e749f219511c2', 'hw/soc/pnr/alu-prefix-c10-input.lock.json': '816eb1c44531345b1e8ad5b6fae5c099977ba30c5236e47a28e2bf1282a8006c', 'docs/evidence/timing-cloud-input-20260930.json': 'b8c3044903eff78728c4a5205a2e054576ad91ccdaa0bff28c59de3d88ae712a', 'hw/soc/flow/sim_logic_boot_gl.py': '85bf0e22c0ba246973953ac5c8ee79e4c7219fcee2c78c5d55babcc121385830', 'hw/soc/flow/gen_logic_boot_rom.py': '5f3510003984edf7decf2be3240fe9a13074547d7d87bcf2cfa4f73d9e3dc117', 'scripts/run_cloud_alu_boot_trace.py': 'a1a47d79de7893ef69bafe290b49fc68afcd68e5af106c987750cf536c48a5f2', 'hw/soc/tb/alu_boot_trace.v': '3cd442dcc7828c5579019d8ac8884ed220b814d5e979cd8e86d713eca2ea10fc', 'sw/tests/test_alu_boot_trace.py': 'd303f420c342895f7a136fd49077821732c09509b605fc5cd7670e3566444674', '.github/workflows/timing-alu-boot-trace.yml': '524516ba46e1437eb3ce270c73c89d49b55a1054f77c1f22359426f9336e4e7b', 'scripts/run_cloud_npu_state_trace.py': 'c877425001c16eae37c85f69bfd8ed6f457e7fde3501586532efee60e9a23e14', 'hw/soc/tb/npu_state_event_trace.v': '909131caa1d65d3554846f11daff0f9538474ffaa3ae2acf1d720a120f5eec9b', 'sw/tests/test_npu_state_trace.py': '6b693e274a1a1e0a3915738ea6faec44cc62252d90cdef30af86ce99a9cc6ba7', '.github/workflows/timing-npu-state-trace.yml': '3dba8c0537b1e0ff81ea2cc58d55a76e7b3a1320639907c0298302ad6a6c8808', 'scripts/run_cloud_npu_cone_trace.py': '15f1189dcc72096fedcbf678b2d70270cac7339b64e30dfe696282358372262a', 'hw/soc/tb/npu_cone_event_trace.v': '3bfeda92de9c7058fc48f9db27a24eb80c6928b578b84d3f377e0aadc7f04706', 'sw/tests/test_npu_cone_trace.py': '8d8113dd752600487417289d3ec7b2bec25b871c7312fb9c4b9812abe684af09', '.github/workflows/timing-npu-cone-trace.yml': '7b989d1b31af8e70e2fca5cde820c3bc970a6aa205b09f1a383d0725148335df', 'scripts/run_cloud_npu_frontier_trace.py': 'ed033955a372510b6f70a7717816e60940eb10973d656ac0bde9ec4c8d4d5d97', 'hw/soc/tb/npu_frontier_event_trace.v': '2dcf84d6592b3ddf2fb47f4525dde079673c7c370492edb26a04946ffd4304e4', 'hw/soc/pnr/npu-frontier-trace-input.lock.json': '0483e983e5e0beeba063a89cb5c6d1cb0c6b7fe010e4daf6b32f31f688d58d83', 'sw/tests/test_npu_frontier_trace.py': 'acfe37a94c3b04cdffb5efc8be720c49e17a160e6f5a834c1a3d894f7cdac686', '.github/workflows/timing-npu-frontier-trace.yml': 'e758b8f39c705bd061e9c91994828b4ece9d0710dd49749e579d383082494a7a', 'scripts/run_cloud_npu_evq_trace.py': '01bbf49336d06b173fc7c54544af5e9550231df91e4edda06b05b50862f53df4', 'hw/soc/tb/npu_evq_event_trace.v': '8b1e76dcd9e7f653c3627a8d57749f1577785c20cd359999df776eb200f00abe', 'hw/soc/pnr/npu-evq-trace-input.lock.json': '8508fe014aefa34a09fb235a63ff8ba02c6450a1c8471877cd934a2cd285c393', 'sw/tests/test_npu_evq_trace.py': '0e49f1bc4ac1afb78757f6d9a7311cb1d83e8b44657c0be4a6cbc4a67177e788', '.github/workflows/timing-npu-evq-trace.yml': 'bef3e6f1be3e3905160d24009ae1774f61f6226ac7587542ca7c974c4aab489d'}
START,LAST=previous.START,previous.LAST
MAX_CELLS,MAX_SIGNALS,MAX_EVENTS=2304,8192,500000
ROOT_BODIES=previous.ROOT_BODIES
PRIOR={'run_id': 37187157260, 'source_commit': '3fead2e8288aae9f2b6a8733ca08aef0d9818f0d', 'first_candidate_unknown_cycle': 1569426, 'candidate_final': {'artifact_id': 11301014889, 'bytes': 1549446, 'sha256': '2c538b61cdd4111e4b3c6bb3c18c66bef1942c83ac0fe32159ecd8201e6723df'}, 'original_final': {'artifact_id': 11299662694, 'bytes': 1454521, 'sha256': '92fae97377c456d16c993756c28e512e63b82c46fad2b6786d6cc4922754d1b9'}}
EVQ='\\u_npu.u_node0.u_evq_out.'
native_modules=previous.native_modules
native_cells=previous.native_cells
net_key=previous.net_key
expression=previous.expression


def digest(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':')).encode()).hexdigest()


def lock():
    row=json.loads((ROOT/LOCK).read_text())
    q.require(row['schema']==1 and row['producer']==q.PRODUCER and row['prior']==PRIOR,'Wrong write-frontier inputs')
    q.require(row['bounds']==dict(cells=MAX_CELLS,signals=MAX_SIGNALS,events=MAX_EVENTS),'Changed diagnostic bounds')
    q.require(row['cycle_bound']==3000000 and row['window']==[START,LAST],'Changed original workload/window')
    q.require(set(row['variants'])=={'original','candidate'},'Missing paired variant')
    return row



def source_graph(cells,modules):
    drivers={}
    for name,cell in cells.items():
        if cell['type'] not in modules:continue
        module=modules[cell['type']]
        q.require(set(cell['ports'])==set(module['input'])|set(module['output']),'Incomplete native ports')
        for port in module['output']:
            drivers.setdefault(net_key(cell['ports'][port]),[]).append(dict(instance=name,port=port))
    return drivers


def unique_driver(drivers,conductor):
    sources=drivers.get(net_key(conductor),[])
    q.require(len(sources)==1,'Missing or ambiguous exact conductor driver: '+conductor)
    return sources[0]


def complete_cone(cells,modules,drivers,roots):
    # Stop only at actual sequential outputs. A depth boundary is not closure.
    queue=list(roots);seen={}
    while queue:
        name=queue.pop(0)
        if name in seen:continue
        q.require(len(seen)<MAX_CELLS and name in cells and cells[name]['type'] in modules,'Invalid/over-budget cone')
        cell=cells[name];module=modules[cell['type']];seen[name]=cell
        if module['sequential']:continue
        for port in module['input']:
            queue.append(unique_driver(drivers,cell['ports'][port])['instance'])
    # Reject a combinational loop rather than quietly accepting a visited set.
    done=set();active=set()
    def walk(name):
        q.require(name not in active,'Combinational loop in captured frontier')
        if name in done:return
        active.add(name);cell=seen[name];module=modules[cell['type']]
        if not module['sequential']:
            for port in module['input']:walk(unique_driver(drivers,cell['ports'][port])['instance'])
        active.remove(name);done.add(name)
    for name in sorted(seen):walk(name)
    return seen




def derive_binding(netlist,model,variant):
    historical=previous.bind(netlist,model,variant)
    modules=native_modules(model);cells=native_cells(netlist);drivers=source_graph(cells,modules)
    first=EVQ+'u_wptr_a.d [0]'
    rails=[r'\u_npu.u_node0.sync_push',r'\u_npu.u_node0.u_lif.u_op_a.bits',r'\u_npu.u_node0.u_lif.op_b']
    roots={'write_pointer_d0':unique_driver(drivers,first)}
    rail_cells={name:unique_driver(drivers,name) for name in rails}
    queue=[roots['write_pointer_d0']['instance']]
    for name,source in rail_cells.items():
        cell=cells[source['instance']]
        q.require(cell['type']=='sg13g2_dfrbpq_1' and source['port']=='Q','Changed sync/output rail')
        for port in ('D','CLK','RESET_B'):
            roots[name+'.'+port]=unique_driver(drivers,cell['ports'][port])
            queue.append(roots[name+'.'+port]['instance'])
    closed=complete_cone(cells,modules,drivers,queue)
    selected=dict(closed);clock_reset=[]
    for name,cell in list(closed.items()):
        if not modules[cell['type']]['sequential']:continue
        # The real cone includes the native clock-gate latch. Do not invent
        # RESET_B or D ports for a different sequential primitive.
        for port in ('CLK','RESET_B','SET_B','GATE','GCLK','G'):
            if port not in modules[cell['type']]['input']:continue
            conductor=net_key(cell['ports'][port])
            if conductor in ("1'h0","1'h1"):
                clock_reset.append(dict(sink=name,port=port,conductor=conductor,source=None));continue
            if conductor=='clk_i' and not drivers.get(conductor):
                q.require(re.search(r'^\s*input clk_i;',netlist,re.M) is not None,'Unbound primary clock')
                clock_reset.append(dict(sink=name,port=port,conductor=conductor,source=None,boundary='primary_input'));continue
            source=unique_driver(drivers,conductor)
            selected[source['instance']]=cells[source['instance']]
            clock_reset.append(dict(sink=name,port=port,conductor=conductor,source=source))
    q.require(len(selected)<=MAX_CELLS,'Expanded write cone exceeds cell bound')
    selected={n:dict(**cells[n],sequential=modules[cells[n]['type']]['sequential'],model=modules[cells[n]['type']]['body']) for n in sorted(selected)}
    nets={};internals=[];connections=[];frontier=[]
    for name,cell in selected.items():
        module=modules[cell['type']]
        for port in module['input']:
            conductor=net_key(cell['ports'][port]);sources=drivers.get(conductor,[])
            q.require(len(sources)<=1,'Ambiguous write-cone input')
            item=dict(sink=name,port=port,conductor=conductor,source=sources[0] if sources else None)
            connections.append(item)
            if not sources or sources[0]['instance'] not in selected:
                frontier.append(dict(item,reason='sequential_data_or_clock_reset_driver_boundary'))
        for field in module['fields']:
            item=dict(instance=name,field=field,expression=expression(name,field))
            if field in cell['ports']:
                conductor=net_key(cell['ports'][field])
                nets.setdefault(conductor,dict(item,role='conductor',conductor=conductor))
            elif module['sequential']:
                internals.append(dict(item,role='native_sequential_internal'))
    signals=[dict(index=i,**row) for i,row in enumerate([*nets.values(),*internals])]
    q.require(0<len(signals)<=MAX_SIGNALS,'Write-cone scalar budget exceeded')
    sequential=sorted(n for n,c in closed.items() if modules[c['type']]['sequential'])
    return dict(schema=1,variant=variant,netlist_sha256=q.EXPECTED_NETLISTS[variant],model_sha256=old.MODEL_SHA,
        prior_binding_sha256=digest(historical),roots=roots,rail_cells=rail_cells,closed_cone_cells=sorted(closed),
        sequential_boundary=sequential,immediate_clock_reset_drivers=clock_reset,cells=selected,signals=signals,
        conductor_observations={n:next(s['index'] for s in signals if s.get('conductor')==n) for n in nets},
        connections=connections,frontier=frontier,
        scope='Complete write-pointer bit0 and three missing sync/LIF rail D/clock/reset combinational predecessors to real sequential boundaries. One observation per exact conductor plus every sequential internal field; no force, state replacement or claim past recorded frontiers.')



def bind(netlist,model,variant):
    row=derive_binding(netlist,model,variant);expected=lock()['variants'][variant]
    q.require(digest(row)==expected['binding_sha256'] and len(row['cells'])==expected['cells']
        and len(row['signals'])==expected['signals'] and len(row['sequential_boundary'])==expected['sequential_boundaries'],'Exact EVQ binding differs')
    return row


def instrument(bench,binding,start=START,last=LAST):
    q.require(bench.count('endmodule')==1 and 'NSSOC_NPU_WRITE_BEGIN' not in bench,'Ambiguous baseline bench')
    signals=binding['signals'];q.require([s['index'] for s in signals]==list(range(len(signals))) and 0<len(signals)<=MAX_SIGNALS,'Invalid scalar inventory')
    seen=set()
    for s in signals:
        cell=binding['cells'].get(s['instance'])
        q.require(cell is not None and re.search(r'\b'+re.escape(s['field'])+r'\b',cell['model']),'Unbound scalar')
        q.require(s['expression']==expression(s['instance'],s['field']) and s['expression'] not in seen,'Changed/duplicate scalar expression')
        seen.add(s['expression'])
        if s['role']=='conductor':
            q.require(s['field'] in cell['ports'] and net_key(cell['ports'][s['field']])==s['conductor'],'Wrong native conductor')
        else:
            q.require(s['role']=='native_sequential_internal' and cell['sequential'] and s['field'] not in cell['ports'],'Wrong sequential internal')
    add='\n  // NSSOC_NPU_WRITE_BEGIN: read-only exact source-bound observations.\n'
    add+=f'  nssoc_npu_write_event_trace #(.WIDTH({len(signals)}),.START({start}),.LAST({last}),.MAX_EVENTS({MAX_EVENTS})) npu_cone (\n'
    add+="    .clk_i(clk),.cycle_i({32'b0,cycles}),.signals_i({"+','.join(s['expression'] for s in reversed(signals))+'}));\n'
    return bench.replace('endmodule',add+'  // NSSOC_NPU_WRITE_END\nendmodule')


def parse(log,directory,start=START,last=LAST,width=None,max_events=MAX_EVENTS):
    matches=re.findall(r'^NPU_WRITE_SUMMARY start=(\d+) last=(\d+) width=(\d+) events=(\d+) samples=(\d+) sequence=(\d+) final_cycle=(\d+) armed=1$',log,re.M)
    q.require(len(matches)==1,'Missing/duplicate complete sparse summary')
    a,b,w,events,samples,total,final=map(int,matches[0]);width=w if width is None else width
    q.require((a,b,w)==(start,last,width) and 0<w<=MAX_SIGNALS and final>last and samples==last-start+1
        and 0<events<=max_events and total==events+samples+1,'Incomplete sparse window')
    lines=(Path(directory)/'npu-write-events.log').read_text().splitlines();q.require(len(lines)==total,'Incomplete sparse records')
    previous=None;event_count=0;sample_cycles=[];previous_time=-1;unknown=[];initial=None
    for seq,line in enumerate(lines,1):
        m=re.fullmatch(r'(INIT|EV|S) seq=(\d+) cycle=(\d+) realtime_ns=(\d+\.\d{3})(.*)',line)
        q.require(m is not None and int(m[2])==seq,'Invalid sparse record')
        cycle=int(m[3]);now=int(m[4].replace('.',''));q.require(now>=previous_time,'Sparse time moved backwards');previous_time=now
        if m[1] in ('INIT','S'):
            bits=re.fullmatch(r' all=([01xz]+)',m[5]);q.require(bits is not None and len(bits[1])==width,'Invalid snapshot')
            if seq==1:
                q.require(m[1]=='INIT' and cycle==start-1,'Missing initial snapshot')
                previous=list(bits[1][::-1]);initial=[dict(signal=i,value=v) for i,v in enumerate(previous) if v in 'xz'];continue
            q.require(m[1]=='S' and start<=cycle<=last and list(bits[1][::-1])==previous,'Sample differs from complete callback history')
            sample_cycles.append(cycle)
        else:
            q.require(previous is not None and start-1<=cycle<=last,'Event outside initialized window')
            scalar=re.fullmatch(r' signal=(\d+) prior=([01xz]) value=([01xz])',m[5]);q.require(scalar is not None,'Invalid sparse scalar')
            index=int(scalar[1]);prior=scalar[2];value=scalar[3]
            q.require(0<=index<width and previous[index]==prior and prior!=value,'Invalid prior/new scalar transition')
            previous[index]=value;event_count+=1
            if value in 'xz':unknown.append(dict(sequence=seq,cycle=cycle,realtime_ns=m[4],signal=index,prior=prior,value=value))
    q.require(event_count==events and sample_cycles==list(range(start,last+1)),'Missing event or sample coverage')
    return dict(start=start,last=last,width=width,events=events,samples=samples,sequence=total,final_cycle=final,
        initial_static_unknowns=initial,new_unknown_transitions=unknown,first_new_unknown=unknown[0] if unknown else None,
        scope='Recorded scalar callbacks reconciled with each settled snapshot. Sparse events do not pretend to contain atomic live vectors or a simulator delta index.',
        raw_event_file=q.pin(Path(directory)/'npu-write-events.log'))


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
        monitor='nssoc_npu_write_event_trace #(.WIDTH(5),.START(2),.LAST(7)) obs(.clk_i(clk),.cycle_i({32\'b0,cycles}),.signals_i({ff.Q,root.Y,root.B1,root.A2,root.A1}));\n'
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
        rr=tiny_execute([vvp,'-i',root/'tiny.vvp','+npu_write_dir='+str(root)],root,'run');q.require(rr['returncode']==0,'Native cone control failed')
        log=(root/'run.log').read_text();parsed=parse(log,root,2,7,5)
        new_indices={e['signal'] for e in parsed['new_unknown_transitions']}
        q.require(new_indices==({'shared_input_x':{1,3,4},'latent_x_unmasked':{3,4}}.get(case,set())),'Incorrect native cone X propagation')
        q.require({x['signal'] for x in parsed['initial_static_unknowns']}==({1} if case in ('static_x_masked','latent_x_unmasked') else set()),'Initial static X classification differs')
        baseline=root/'baseline.v';baseline.write_text(text.replace(monitor,''));bc=tiny_execute([iverilog,'-g2005-sv','-DFUNCTIONAL','-s','tiny','-o',root/'baseline.vvp',baseline,model],root,'baseline-compile')
        q.require(bc['returncode']==0,'Native baseline compile failed');br=tiny_execute([vvp,'-i',root/'baseline.vvp'],root,'baseline-run')
        q.require(br['returncode']==0 and re.findall(r'^SIGNATURE.*$',log,re.M)==re.findall(r'^SIGNATURE.*$',(root/'baseline-run.log').read_text(),re.M),'Observer altered actual native D/Q trajectory')
        rows[case]=dict(compile=cc,execution=rr,observation=parsed,baseline_compile=bc,baseline_execution=br,native_output_trajectory_unchanged=True)
    return rows

def verify_methods(output,row):
    q.require(set(row['methods'])==set(PINS)|set(OWN),'Missing EVQ methods')
    for name,expected in row['methods'].items():
        q.common.verify_file(ROOT/name,expected)
        q.common.verify_file(output/'methods'/name,expected)
        if name in PINS:q.require(expected['sha256']==PINS[name],'Changed frozen method')


def prepare(output,work,variant):
    q.require(os.environ.get('GITHUB_ACTIONS')=='true','Actual SoC preparation is cloud-only')
    for name,sha in PINS.items():q.require(q.common.sha(ROOT/name)==sha,'Frozen dependency changed: '+name)
    q.boot_prepare(output,work,variant,'vendor',None);row=json.loads((output/'result.json').read_text())
    try:
        row.update(status='PREPARING_NPU_WRITE_TRACE',prior_cone_trace=PRIOR,window=dict(start=START,last=LAST,max_events=MAX_EVENTS))
        for name in (*PINS,*OWN):
            dest=output/'methods'/name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/name,dest);row['methods'][name]=q.pin(dest)
        tools=work/'oss-cad-suite/bin';model=work/'inputs/models/sg13g2_stdcell.v'
        row['write_controls']=tiny_controls(tools/'iverilog',tools/'vvp',model,output/'write-controls')
        net=work/'producer'/('synthesis-'+variant)/'soc_top.netlist.v'
        binding=bind(net.read_text(),model.read_text(),variant);row['write_bindings']=binding;q.common.save(output/'write-bindings.json',binding)
        bench=output/'tb_qualification_boot.v';baseline=output/'original-qualified-bench.v';shutil.copyfile(bench,baseline)
        row['original_bench']=q.pin(baseline);row['original_compilation']=row['compile'];row['original_compiled_simulation']=row['compiled_simulation']
        bench.write_text(instrument(baseline.read_text(),binding));monitor=output/'npu_write_event_trace.v';shutil.copyfile(ROOT/MONITOR,monitor)
        command=row['compile']['command']+[str(monitor)]
        q.require(command.count('-DTIMEOUT_CYCLES=3000000')==1 and row['cycle_bound']==3000000,'Original qualification bound changed')
        row['sources'][str(bench)]=q.pin(bench);row['sources'][str(monitor)]=q.pin(monitor);row['compile']=q.alu.execute(command,output,'write-compile')
        q.require(row['compile']['returncode']==0 and not re.search(r'warning: Port .*expects .*bits, got',(output/'write-compile.log').read_text()),'Cone compile failed or width mismatch')
        row['compiled_simulation']=q.pin(Path(row['compiled_simulation_path']));row['boot_command']+=['+npu_write_dir='+str(output)]
        verify_methods(output,row)
        for path,expected in row['sources'].items():q.common.verify_file(Path(path),expected)
        row.update(status='COMPILED_NPU_WRITE_TRACE_NO_ACCEPTANCE',scope='Exact paired first-X semantic boundaries; unchanged3M workload/models/reset. No RTL repair or acceptance claim.')
    except Exception as error:row.update(status='NPU_WRITE_PREPARATION_FAILED',error=repr(error));raise
    finally:q.finish(output,row)

def run(output):
    q.require(os.environ.get('GITHUB_ACTIONS')=='true','Actual SoC trace is cloud-only');row=json.loads((output/'result.json').read_text())
    try:
        q.require(row['status']=='COMPILED_NPU_WRITE_TRACE_NO_ACCEPTANCE' and row['github_source_commit']==os.environ['GITHUB_SHA'],'Wrong cone checkpoint')
        q.require(row['cycle_bound']==3000000 and row['prior_cone_trace']==PRIOR and row['window']==dict(start=START,last=LAST,max_events=MAX_EVENTS),'Changed cone scope')
        q.require(row['producer']==q.PRODUCER and row['variant'] in ROOT_BODIES and row['memory']=='vendor','Changed input variant')
        flags=('candidate_adopted','timing_accepted','manufacturing_approval','mapped_core_equivalence_accepted','full_soc_functional_accepted')
        q.require(all(row[k] is False for k in flags),'Unexpected acceptance');q.verify_outputs(output,row)
        q.require(set(row['methods'])==set(PINS)|set(OWN),'Missing cone methods')
        for name,sha in PINS.items():q.require(row['methods'][name]['sha256']==sha,'Frozen source changed')
        q.require(row['write_bindings']==json.loads((output/'write-bindings.json').read_text()) and digest(row['write_bindings'])==lock()['variants'][row['variant']]['binding_sha256'],'Frontier bindings changed')
        q.require(instrument((output/'original-qualified-bench.v').read_text(),row['write_bindings'])==(output/'tb_qualification_boot.v').read_text(),'Instrumentation changed baseline statements')
        verify_methods(output,row)
        for path,expected in row['sources'].items():q.common.verify_file(Path(path),expected)
        q.common.verify_file(Path(row['compiled_simulation_path']),row['compiled_simulation'])
        command=row['boot_command'];q.common.verify_file(Path(command[0]),row['runtime']['tools']['vvp'])
        q.require(command[1:]==['-i',row['compiled_simulation_path'],'+flash0='+str(output/'firmware/flash0.hex'),'+npu_write_dir='+str(output)],'Native command differs')
        row['status']='RUNNING_NPU_WRITE_TRACE';q.common.save(output/'result.json',row);env=os.environ.copy()
        for key in ('GH_TOKEN','GITHUB_TOKEN','PYTHONPATH','PYTHONHOME'):env.pop(key,None)
        start=time.monotonic()
        with (output/'boot.log').open('x') as log:
            child=subprocess.Popen(command,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,bufsize=1,env=env,stdin=subprocess.DEVNULL)
            for line in child.stdout:log.write(line);log.flush();print(line,end='',flush=True)
            code=child.wait()
        row['boot_execution']=dict(command=command,returncode=code,elapsed_s=time.monotonic()-start);text=(output/'boot.log').read_text()
        row['evq_observation']=parse(text,output,width=len(row['write_bindings']['signals']))
        q.require(text.count('QUALIFICATION_MBIST PASS cycles=983043')==1,'Original MBIST not observed')
        row['observed_boot_pass']=q.passed_boot(code,text)
        verify_methods(output,row)
        for path,expected in row['sources'].items():q.common.verify_file(Path(path),expected)
        q.common.verify_file(Path(row['compiled_simulation_path']),row['compiled_simulation'])
        row.update(status='NPU_WRITE_CAPTURE_COMPLETE_NOT_ACCEPTANCE',boot_failure_preserved=not row['observed_boot_pass'])
    except Exception as error:row.update(status='NPU_WRITE_FAILED_OR_INCOMPLETE',error=repr(error));raise
    finally:q.finish(output,row)

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('phase',choices=('prepare','run'));parser.add_argument('--output',type=Path,required=True);parser.add_argument('--work',type=Path);parser.add_argument('--variant',choices=tuple(ROOT_BODIES));args=parser.parse_args()
    if args.phase=='run':run(args.output.resolve())
    else:
        q.require(args.work is not None and args.variant is not None,'Missing preparation inputs');prepare(args.output.resolve(),args.work.resolve(),args.variant)

if __name__=='__main__':main()
