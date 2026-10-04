#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Source-bound EVQ_OUT read-valid/parity observation; unchanged 3M native boot."""
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

import run_cloud_npu_frontier_trace as previous

q=previous.q
old=previous.old
ROOT=Path(__file__).resolve().parents[1]
LOCK='hw/soc/pnr/npu-evq-trace-input.lock.json'
MONITOR='hw/soc/tb/npu_evq_event_trace.v'
OWN=('scripts/run_cloud_npu_evq_trace.py',MONITOR,LOCK,'sw/tests/test_npu_evq_trace.py',
     '.github/workflows/timing-npu-evq-trace.yml')
PINS=previous.PINS | {'scripts/run_cloud_npu_frontier_trace.py': 'ed033955a372510b6f70a7717816e60940eb10973d656ac0bde9ec4c8d4d5d97', 'hw/soc/tb/npu_frontier_event_trace.v': '2dcf84d6592b3ddf2fb47f4525dde079673c7c370492edb26a04946ffd4304e4', 'hw/soc/pnr/npu-frontier-trace-input.lock.json': '0483e983e5e0beeba063a89cb5c6d1cb0c6b7fe010e4daf6b32f31f688d58d83', 'sw/tests/test_npu_frontier_trace.py': 'acfe37a94c3b04cdffb5efc8be720c49e17a160e6f5a834c1a3d894f7cdac686', '.github/workflows/timing-npu-frontier-trace.yml': 'e758b8f39c705bd061e9c91994828b4ece9d0710dd49749e579d383082494a7a'}
START,LAST=previous.START,previous.LAST
MAX_CELLS,MAX_SIGNALS,MAX_EVENTS=240,2048,100000
ROOT_BODIES=previous.ROOT_BODIES
PRIOR=dict(run_id=37158099088,source_commit='b1c69282fb0ac1525fb9d2d36d325d8aa6377cd7',
 candidate_final=dict(artifact_id=11290413846,bytes=1090853,sha256='c1c35082bb401ea5ee4f4c4ae9d5529edb2876aac3467b60cb1196888b6f53aa'),
 original_final=dict(artifact_id=11288665134,bytes=862134,sha256='ac515c74fba70241a071448fe2cee0d426927ef1236a70949a5258412286c090'),
 first_candidate_unknown_cycle=1569429,first_candidate_unknown=['_082634_','A','_027398_'])
EVQ='\\u_npu.u_node0.u_evq_out.'
native_modules=previous.native_modules
native_cells=previous.native_cells
net_key=previous.net_key
expression=previous.expression


def digest(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':')).encode()).hexdigest()


def lock():
    row=json.loads((ROOT/LOCK).read_text())
    q.require(row['schema']==1 and row['producer']==q.PRODUCER and row['prior']==PRIOR,'Wrong EVQ inputs')
    q.require(row['bounds']==dict(cells=MAX_CELLS,signals=MAX_SIGNALS,events=MAX_EVENTS),'Changed EVQ bounds')
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


def parity_leaves(conductor,cells,drivers,active=None):
    active=set() if active is None else active
    name=unique_driver(drivers,conductor)['instance']
    q.require(name not in active,'Parity combinational loop')
    cell=cells[name]
    if cell['type'] not in ('sg13g2_xor2_1','sg13g2_xnor2_1'):
        return [net_key(conductor)],0
    active=active|{name}
    a,ai=parity_leaves(cell['ports']['A'],cells,drivers,active)
    b,bi=parity_leaves(cell['ports']['B'],cells,drivers,active)
    return a+b,ai^bi^int(cell['type']=='sg13g2_xnor2_1')


def derive_binding(netlist,model,variant):
    historical=previous.bind(netlist,model,variant)
    modules=native_modules(model);cells=native_cells(netlist);drivers=source_graph(cells,modules)
    names=['rd_pass','u_rdv_a.bits','rdv_b']
    roots={n:unique_driver(drivers,EVQ+n) for n in names}
    for n in names[1:]:
        cell=cells[roots[n]['instance']]
        q.require(cell['type']=='sg13g2_dfrbpq_1' and roots[n]['port']=='Q'
            and net_key(cell['ports']['D'])==EVQ+'rd_pass','Changed read-valid rail')
    rd=cells[roots['rd_pass']['instance']]
    q.require(rd['type']=='sg13g2_nor2_1' and roots['rd_pass']['port']=='Y','Changed rd_pass native equation')
    leaves,inverted=parity_leaves(rd['ports']['B'],cells,drivers)
    q.require(len(leaves)==17 and len(set(leaves))==17 and inverted==0 and EVQ+'head_par' in leaves,'Changed 17-bit even parity tree')
    head=[]
    for conductor in leaves:
        if conductor==EVQ+'head_par':continue
        leaf=unique_driver(drivers,conductor)
        cone=complete_cone(cells,modules,drivers,[leaf['instance']])
        storage=[]
        for cell in cone.values():
            if cell['type']=='sg13g2_dfrbpq_1':
                match=re.fullmatch(re.escape(EVQ)+r'mem\[(\d+)\] \[(\d+)\]',net_key(cell['ports']['Q']))
                if match:storage.append(tuple(map(int,match.groups())))
        q.require(len(storage)==4 and len({bit for _,bit in storage})==1 and {slot for slot,_ in storage}==set(range(4)),'Unknown head-data storage mapping')
        head.append(dict(bit=storage[0][1],conductor=conductor,source=leaf,storage=sorted(storage)))
    q.require(sorted(x['bit'] for x in head)==list(range(16)),'Missing head-data bit')
    head.sort(key=lambda x:x['bit'])
    closed=complete_cone(cells,modules,drivers,[x['instance'] for x in roots.values()])
    selected=dict(closed)
    # Preserve a small downstream witness; the full previous capture remains immutable.
    for name in historical['state_binding']['cells']:selected[name]=cells[name]
    for conductor in ('\\u_npu.u_node0.oh_valid_b','\\u_npu.u_node0.u_ohv_a.bits'):
        name=unique_driver(drivers,conductor)['instance'];selected[name]=cells[name]
    immediate=[]
    for name,cell in list(selected.items()):
        if cell['type']!='sg13g2_dfrbpq_1':continue
        for port in ('CLK','RESET_B'):
            if cell['ports'][port]=="1'h1" and port=='RESET_B':
                immediate.append(dict(sink=name,port=port,conductor=cell['ports'][port],source=None,constant=True));continue
            source=unique_driver(drivers,cell['ports'][port]);selected[source['instance']]=cells[source['instance']]
            immediate.append(dict(sink=name,port=port,conductor=cell['ports'][port],source=source))
    q.require(len(selected)<=MAX_CELLS,'Selected cell budget exceeded')
    selected={n:dict(**cells[n],sequential=modules[cells[n]['type']]['sequential'],model=modules[cells[n]['type']]['body']) for n in sorted(selected)}
    signals=[];connections=[];frontier=[]
    for name,cell in selected.items():
        module=modules[cell['type']]
        for port in module['input']:
            sources=drivers.get(net_key(cell['ports'][port]),[]);q.require(len(sources)<=1,'Ambiguous boundary')
            row=dict(sink=name,port=port,conductor=cell['ports'][port],source=sources[0] if sources else None);connections.append(row)
            if not sources or sources[0]['instance'] not in selected:frontier.append(dict(row,reason='sequential_data_or_retained_observation_boundary'))
        for field in module['fields']:
            signals.append(dict(index=len(signals),instance=name,field=field,expression=expression(name,field),role='native'))
    rd_name=roots['rd_pass']['instance']
    semantics=[dict(name='rd_pass',expression=expression(rd_name,'Y')),
        dict(name='head_bad',expression=expression(rd_name,'B')),
        dict(name='not_rd_ok',expression=expression(rd_name,'A'))]
    for x in head:semantics.append(dict(name='selected_head_data['+str(x['bit'])+']',expression=expression(x['source']['instance'],x['source']['port'])))
    hp=unique_driver(drivers,EVQ+'head_par');semantics.append(dict(name='head_par',expression=expression(hp['instance'],hp['port'])))
    # The exact NOR equation is rd_pass = !not_rd_ok && !head_bad.
    derived=dict(index=len(signals),instance=rd_name,field='A',expression='~('+expression(rd_name,'A')+')',role='derived_rd_ok')
    signals.append(derived);semantics.append(dict(name='rd_ok',expression=derived['expression']))
    indexes={s['expression']:s['index'] for s in signals}
    for s in semantics:s['index']=indexes[s['expression']]
    q.require(len(signals)<=MAX_SIGNALS,'Scalar budget exceeded')
    return dict(schema=1,variant=variant,netlist_sha256=q.EXPECTED_NETLISTS[variant],model_sha256=old.MODEL_SHA,
        prior_binding_sha256=digest(historical),roots=roots,head_data=head,parity_leaves=leaves,parity_inversion=inverted,
        semantic_observations=semantics,closed_cone_cells=sorted(closed),sequential_boundary=sorted(n for n,c in closed.items() if modules[c['type']]['sequential']),
        immediate_clock_reset_drivers=immediate,cells=selected,signals=signals,connections=connections,frontier=frontier,
        scope='Complete rd_pass combinational predecessor to real state boundaries; exact two read-valid rails, all source-bound selected head/parity leaves, downstream state and clocks/reset. Read-only diagnostic, not proof or repair. Storage-D predecessors outside selected cells remain explicit.')


def bind(netlist,model,variant):
    row=derive_binding(netlist,model,variant);expected=lock()['variants'][variant]
    q.require(digest(row)==expected['binding_sha256'] and len(row['cells'])==expected['cells']
        and len(row['signals'])==expected['signals'] and len(row['sequential_boundary'])==expected['sequential_boundaries'],'Exact EVQ binding differs')
    return row


def instrument(bench,binding,start=START,last=LAST):
    q.require(bench.count('endmodule')==1 and 'NSSOC_NPU_EVQ_BEGIN' not in bench,'Ambiguous baseline bench')
    signals=binding['signals'];q.require([s['index'] for s in signals]==list(range(len(signals))) and 0<len(signals)<=MAX_SIGNALS,'Invalid scalar inventory')
    for s in signals:
        q.require(s['instance'] in binding['cells'] and re.search(r'\b'+re.escape(s['field'])+r'\b',binding['cells'][s['instance']]['model']),'Unbound native scalar')
        expected=expression(s['instance'],s['field'])
        if s['role']=='derived_rd_ok':
            q.require(s['instance']==binding['roots']['rd_pass']['instance'] and s['field']=='A'
                and binding['cells'][s['instance']]['type']=='sg13g2_nor2_1','Invalid derived read eligibility')
            expected='~('+expected+')'
        else:q.require(s['role']=='native','Unknown scalar role')
        q.require(s['expression']==expected,'Changed scalar expression')
    add='\n  // NSSOC_NPU_EVQ_BEGIN: read-only exact source-bound observations.\n'
    add+=f'  nssoc_npu_evq_event_trace #(.WIDTH({len(signals)}),.START({start}),.LAST({last}),.MAX_EVENTS({MAX_EVENTS})) npu_cone (\n'
    add+="    .clk_i(clk),.cycle_i({32'b0,cycles}),.signals_i({"+','.join(s['expression'] for s in reversed(signals))+'}));\n'
    return bench.replace('endmodule',add+'  // NSSOC_NPU_EVQ_END\nendmodule')

def parse(log,directory,start=START,last=LAST,width=None,max_events=MAX_EVENTS):
    matches=re.findall(r'^NPU_EVQ_SUMMARY start=(\d+) last=(\d+) width=(\d+) events=(\d+) samples=(\d+) sequence=(\d+) final_cycle=(\d+) armed=1$',log,re.M)
    q.require(len(matches)==1,'Missing/duplicate complete cone summary')
    a,b,w,events,samples,total,final=map(int,matches[0]);width=w if width is None else width
    q.require((a,b,w)==(start,last,width) and 0<w<=MAX_SIGNALS and final>last and samples==last-start+1
              and 0<events<=max_events and total==events+samples+1,'Incomplete cone window')
    lines=(Path(directory)/'npu-evq-events.log').read_text().splitlines();q.require(len(lines)==total,'Incomplete cone records')
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
        raw_event_file=q.pin(Path(directory)/'npu-evq-events.log'))

def tiny_execute(command,root,label):
    def bound():
        resource.setrlimit(resource.RLIMIT_AS,(2*1024**3,2*1024**3));resource.setrlimit(resource.RLIMIT_CORE,(0,0))
    env=os.environ.copy()
    for key in ('GH_TOKEN','GITHUB_TOKEN','PYTHONPATH','PYTHONHOME'):env.pop(key,None)
    command=list(map(str,command));start=time.monotonic()
    with (root/(label+'.log')).open('w') as log:
        result=subprocess.run(command,cwd=root,stdout=log,stderr=subprocess.STDOUT,env=env,preexec_fn=bound,check=False)
    return dict(command=command,returncode=result.returncode,seconds=time.monotonic()-start,memory_bytes=2*1024**3,log=q.pin(root/(label+'.log')))

def head_control_source(binding, model, mutate=False):
    """Native mapped head-selection subgraph with explicit synthetic boundary inputs.

    This finite control validates the observation labels, not the SoC state or
    FIFO invariant. No cut or assumption is added to the actual boot design.
    """
    cells=binding['cells'];modules=native_modules(model);drivers=source_graph(cells,modules)
    cuts={EVQ+f'mem[{slot}] [{bit}]':f'memory[{slot*16+bit}]' for slot in range(4) for bit in range(16)}
    cuts.update({EVQ+f'u_par.bits [{slot}]':f'parity[{slot}]' for slot in range(4)})
    cuts.update({EVQ+f'rd_idx [{bit}]':f'address[{bit}]' for bit in range(2)})
    rd=cells[binding['roots']['rd_pass']['instance']]
    selected={};active=set()
    def walk(conductor):
        key=net_key(conductor)
        if key in cuts:return
        name=unique_driver(drivers,key)['instance']
        q.require(name not in active,'Head-network loop')
        if name in selected:return
        cell=cells[name];q.require(not modules[cell['type']]['sequential'],'Unexpected head-network state boundary')
        active.add(name)
        for port in modules[cell['type']]['input']:walk(cell['ports'][port])
        active.remove(name);selected[name]=cell
    walk(rd['ports']['B'])
    q.require(0<len(selected)<=100,'Native head control exceeds bound')
    wires=sorted({net_key(c) for cell in selected.values() for c in cell['ports'].values()}-set(cuts))
    aliases={c:'w'+str(i) for i,c in enumerate(wires)}|cuts
    text='''`timescale 1ns/1ps
module head_control;
reg [63:0] memory;reg [3:0] parity;reg [1:0] address;
integer i,j,k;reg [15:0] expected;reg expected_par;
'''
    text+='wire '+','.join('w'+str(i) for i in range(len(wires)))+';\n'
    for name,cell in sorted(selected.items()):
        ports={p:aliases[net_key(c)] for p,c in cell['ports'].items()}
        if mutate:
            # Exactly one real data input rerouted to the opposite stored value.
            candidates=[p for p,c in ports.items() if c=='memory[0]']
            if candidates:ports[candidates[0]]='~memory[0]';mutate=False
        text+=cell['type']+' '+name+' ('+','.join('.'+p+'('+c+')' for p,c in ports.items())+');\n'
    text+='wire [15:0] observed={'+','.join(aliases[x['conductor']] for x in reversed(binding['head_data']))+'};\n'
    text+='wire observed_par='+aliases[EVQ+'head_par']+';\nwire observed_bad='+aliases[net_key(rd['ports']['B'])]+';\n'
    text+='''task check;
begin #1; expected=memory[address*16+:16];expected_par=parity[address];
if(observed!==expected || observed_par!==expected_par || observed_bad!==(^{expected_par,expected}))
$fatal(1,"Mapped head/parity labels differ i=%0d address=%b",i,address);
end endtask
initial begin
for(i=0;i<256;i=i+1)begin
memory={16'h1234,16'habcd,16'h2468,16'h1357} ^ (64'h0101010101010101*i);
parity=i;for(j=0;j<4;j=j+1)begin address=j;check;end
end
// Unknown stored data is observed only when selected; no X-to-zero oracle.
for(k=0;k<64;k=k+1)begin
memory=64'h0123456789abcdef;memory[k]=1'bx;parity=4'b1010;
for(j=0;j<4;j=j+1)begin address=j;check;end
end
for(k=0;k<4;k=k+1)begin
memory=64'h0123456789abcdef;parity=4'b1010;parity[k]=1'bx;
for(j=0;j<4;j=j+1)begin address=j;check;end
end
$display("EVQ_HEAD_NATIVE_PASS checks=1296");$finish;
end
endmodule
'''
    return text


def head_controls(iverilog,vvp,model,binding,output):
    output=Path(output);output.mkdir();result={};model=Path(model)
    for negative in (False,True):
        name='wrong_memory_input' if negative else 'exact_mapped_head';root=output/name;root.mkdir()
        source=root/'head.v';source.write_text(head_control_source(binding,model.read_text(),negative))
        cc=tiny_execute([iverilog,'-g2005-sv','-DFUNCTIONAL','-s','head_control','-o',root/'head.vvp',source,model],root,'compile')
        q.require(cc['returncode']==0,'Native head control compilation failed')
        rr=tiny_execute([vvp,'-i',root/'head.vvp'],root,'run');log=(root/'run.log').read_text()
        if negative:q.require(rr['returncode']!=0 and 'Mapped head/parity labels differ' in log,'Wrong head input not rejected')
        else:q.require(rr['returncode']==0 and log.count('EVQ_HEAD_NATIVE_PASS checks=1296')==1,'Exact mapped head labels did not match native finite oracle')
        result[name]=dict(compile=cc,execution=rr,expected_negative=negative,source=q.pin(source))
    return result


def tiny_controls(iverilog,vvp,model,output):
    output=Path(output);output.mkdir();model=Path(model);old.model_contract(model.read_text());rows={}
    for case in ('known','static_x_masked','shared_input_x','latent_x_unmasked','coalesced_pulse'):
        root=output/case;root.mkdir()
        # Real combinational root and real native DFF; no force/UDP substitution.
        values={'known':("1'b0","a=0;b=1;"),'static_x_masked':("1'bx","a=1;b=1;"),'shared_input_x':("1'b0","s=1'bx;"),'latent_x_unmasked':("1'bx","a=0;"),'coalesced_pulse':("1'b0","s=1;s=0;")}[case]
        monitor='nssoc_npu_evq_event_trace #(.WIDTH(5),.START(2),.LAST(7)) obs(.clk_i(clk),.cycle_i({32\'b0,cycles}),.signals_i({ff.Q,root.Y,root.B1,root.A2,root.A1}));\n'
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
        rr=tiny_execute([vvp,'-i',root/'tiny.vvp','+npu_evq_dir='+str(root)],root,'run');q.require(rr['returncode']==0,'Native cone control failed')
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
        row.update(status='PREPARING_NPU_EVQ_TRACE',prior_cone_trace=PRIOR,window=dict(start=START,last=LAST,max_events=MAX_EVENTS))
        for name in (*PINS,*OWN):
            dest=output/'methods'/name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/name,dest);row['methods'][name]=q.pin(dest)
        tools=work/'oss-cad-suite/bin';model=work/'inputs/models/sg13g2_stdcell.v'
        row['evq_controls']=tiny_controls(tools/'iverilog',tools/'vvp',model,output/'evq-controls')
        net=work/'producer'/('synthesis-'+variant)/'soc_top.netlist.v'
        binding=bind(net.read_text(),model.read_text(),variant);row['head_controls']=head_controls(tools/'iverilog',tools/'vvp',model,binding,output/'head-controls');row['evq_bindings']=binding;q.common.save(output/'evq-bindings.json',binding)
        bench=output/'tb_qualification_boot.v';baseline=output/'original-qualified-bench.v';shutil.copyfile(bench,baseline)
        row['original_bench']=q.pin(baseline);row['original_compilation']=row['compile'];row['original_compiled_simulation']=row['compiled_simulation']
        bench.write_text(instrument(baseline.read_text(),binding));monitor=output/'npu_evq_event_trace.v';shutil.copyfile(ROOT/MONITOR,monitor)
        command=row['compile']['command']+[str(monitor)]
        q.require(command.count('-DTIMEOUT_CYCLES=3000000')==1 and row['cycle_bound']==3000000,'Original qualification bound changed')
        row['sources'][str(bench)]=q.pin(bench);row['sources'][str(monitor)]=q.pin(monitor);row['compile']=q.alu.execute(command,output,'evq-compile')
        q.require(row['compile']['returncode']==0 and not re.search(r'warning: Port .*expects .*bits, got',(output/'evq-compile.log').read_text()),'Cone compile failed or width mismatch')
        row['compiled_simulation']=q.pin(Path(row['compiled_simulation_path']));row['boot_command']+=['+npu_evq_dir='+str(output)]
        verify_methods(output,row)
        for path,expected in row['sources'].items():q.common.verify_file(Path(path),expected)
        row.update(status='COMPILED_NPU_EVQ_TRACE_NO_ACCEPTANCE',scope='Exact paired first-X semantic boundaries; unchanged3M workload/models/reset. No RTL repair or acceptance claim.')
    except Exception as error:row.update(status='NPU_EVQ_PREPARATION_FAILED',error=repr(error));raise
    finally:q.finish(output,row)

def run(output):
    q.require(os.environ.get('GITHUB_ACTIONS')=='true','Actual SoC trace is cloud-only');row=json.loads((output/'result.json').read_text())
    try:
        q.require(row['status']=='COMPILED_NPU_EVQ_TRACE_NO_ACCEPTANCE' and row['github_source_commit']==os.environ['GITHUB_SHA'],'Wrong cone checkpoint')
        q.require(row['cycle_bound']==3000000 and row['prior_cone_trace']==PRIOR and row['window']==dict(start=START,last=LAST,max_events=MAX_EVENTS),'Changed cone scope')
        q.require(row['producer']==q.PRODUCER and row['variant'] in ROOT_BODIES and row['memory']=='vendor','Changed input variant')
        flags=('candidate_adopted','timing_accepted','manufacturing_approval','mapped_core_equivalence_accepted','full_soc_functional_accepted')
        q.require(all(row[k] is False for k in flags),'Unexpected acceptance');q.verify_outputs(output,row)
        q.require(set(row['methods'])==set(PINS)|set(OWN),'Missing cone methods')
        for name,sha in PINS.items():q.require(row['methods'][name]['sha256']==sha,'Frozen source changed')
        q.require(row['evq_bindings']==json.loads((output/'evq-bindings.json').read_text()) and digest(row['evq_bindings'])==lock()['variants'][row['variant']]['binding_sha256'],'Frontier bindings changed')
        q.require(instrument((output/'original-qualified-bench.v').read_text(),row['evq_bindings'])==(output/'tb_qualification_boot.v').read_text(),'Instrumentation changed baseline statements')
        verify_methods(output,row)
        for path,expected in row['sources'].items():q.common.verify_file(Path(path),expected)
        q.common.verify_file(Path(row['compiled_simulation_path']),row['compiled_simulation'])
        command=row['boot_command'];q.common.verify_file(Path(command[0]),row['runtime']['tools']['vvp'])
        q.require(command[1:]==['-i',row['compiled_simulation_path'],'+flash0='+str(output/'firmware/flash0.hex'),'+npu_evq_dir='+str(output)],'Native command differs')
        row['status']='RUNNING_NPU_EVQ_TRACE';q.common.save(output/'result.json',row);env=os.environ.copy()
        for key in ('GH_TOKEN','GITHUB_TOKEN','PYTHONPATH','PYTHONHOME'):env.pop(key,None)
        start=time.monotonic()
        with (output/'boot.log').open('x') as log:
            child=subprocess.Popen(command,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,bufsize=1,env=env,stdin=subprocess.DEVNULL)
            for line in child.stdout:log.write(line);log.flush();print(line,end='',flush=True)
            code=child.wait()
        row['boot_execution']=dict(command=command,returncode=code,elapsed_s=time.monotonic()-start);text=(output/'boot.log').read_text()
        row['evq_observation']=parse(text,output,width=len(row['evq_bindings']['signals']))
        q.require(text.count('QUALIFICATION_MBIST PASS cycles=983043')==1,'Original MBIST not observed')
        row['observed_boot_pass']=q.passed_boot(code,text)
        verify_methods(output,row)
        for path,expected in row['sources'].items():q.common.verify_file(Path(path),expected)
        q.common.verify_file(Path(row['compiled_simulation_path']),row['compiled_simulation'])
        row.update(status='NPU_EVQ_CAPTURE_COMPLETE_NOT_ACCEPTANCE',boot_failure_preserved=not row['observed_boot_pass'])
    except Exception as error:row.update(status='NPU_EVQ_FAILED_OR_INCOMPLETE',error=repr(error));raise
    finally:q.finish(output,row)

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('phase',choices=('prepare','run'));parser.add_argument('--output',type=Path,required=True);parser.add_argument('--work',type=Path);parser.add_argument('--variant',choices=tuple(ROOT_BODIES));args=parser.parse_args()
    if args.phase=='run':run(args.output.resolve())
    else:
        q.require(args.work is not None and args.variant is not None,'Missing preparation inputs');prepare(args.output.resolve(),args.work.resolve(),args.variant)

if __name__=='__main__':main()
