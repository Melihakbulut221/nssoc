from pathlib import Path
import ast,hashlib,json
R=Path.cwd();base=(R/'scripts/run_cloud_npu_evq_trace.py').read_text();tree=ast.parse(base)
# Keep the reviewed boot lifecycle and exact producer; replace only diagnostic
# bindings and parser. This generator is retained with a whole-byte source diff.
s=base.replace('run_cloud_npu_frontier_trace as previous','run_cloud_npu_evq_trace as previous').replace('npu_evq','npu_write').replace('npu-evq','npu-write').replace('NPU_EVQ','NPU_WRITE').replace('EVQ observer','write-frontier observer')
s=s.replace('import run_cloud_npu_write_trace as previous','import run_cloud_npu_evq_trace as previous')
start=s.index('PINS=');stop=s.index('\nEVQ=',start)
import sys
sys.path.insert(0,str(R/'scripts'));import run_cloud_npu_evq_trace as old
pins={**old.PINS,**{n:hashlib.sha256((R/n).read_bytes()).hexdigest() for n in old.OWN}}
prior=dict(run_id=37187157260,source_commit='3fead2e8288aae9f2b6a8733ca08aef0d9818f0d',first_candidate_unknown_cycle=1569426,candidate_final=dict(artifact_id=11301014889,bytes=1549446,sha256='2c538b61cdd4111e4b3c6bb3c18c66bef1942c83ac0fe32159ecd8201e6723df'),original_final=dict(artifact_id=11299662694,bytes=1454521,sha256='92fae97377c456d16c993756c28e512e63b82c46fad2b6786d6cc4922754d1b9'))
s=s[:start]+'PINS='+repr(pins)+'\nSTART,LAST=previous.START,previous.LAST\nMAX_CELLS,MAX_SIGNALS,MAX_EVENTS=2304,8192,500000\nROOT_BODIES=previous.ROOT_BODIES\nPRIOR='+repr(prior)+s[stop:]
# Replace named functions, leaving untouched execution/ownership/preparation
# bodies visible in the final ordinary source file.
def replace_function(name,text):
 global s
 t=ast.parse(s);node=next(x for x in t.body if isinstance(x,(ast.FunctionDef,ast.AsyncFunctionDef)) and x.name==name)
 lines=s.splitlines(keepends=True);s=''.join(lines[:node.lineno-1])+text+'\n'+''.join(lines[node.end_lineno:])
replace_function('lock', '''def lock():
    row=json.loads((ROOT/LOCK).read_text())
    q.require(row['schema']==1 and row['producer']==q.PRODUCER and row['prior']==PRIOR,'Wrong write-frontier inputs')
    q.require(row['bounds']==dict(cells=MAX_CELLS,signals=MAX_SIGNALS,events=MAX_EVENTS),'Changed diagnostic bounds')
    q.require(row['cycle_bound']==3000000 and row['window']==[START,LAST],'Changed original workload/window')
    q.require(set(row['variants'])=={'original','candidate'},'Missing paired variant')
    return row
''')
replace_function('derive_binding', '''def derive_binding(netlist,model,variant):
    historical=previous.bind(netlist,model,variant)
    modules=native_modules(model);cells=native_cells(netlist);drivers=source_graph(cells,modules)
    first=EVQ+'u_wptr_a.d [0]'
    rails=[r'\\u_npu.u_node0.sync_push',r'\\u_npu.u_node0.u_lif.u_op_a.bits',r'\\u_npu.u_node0.u_lif.op_b']
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
''')
replace_function('instrument', '''def instrument(bench,binding,start=START,last=LAST):
    q.require(bench.count('endmodule')==1 and 'NSSOC_NPU_WRITE_BEGIN' not in bench,'Ambiguous baseline bench')
    signals=binding['signals'];q.require([s['index'] for s in signals]==list(range(len(signals))) and 0<len(signals)<=MAX_SIGNALS,'Invalid scalar inventory')
    seen=set()
    for s in signals:
        cell=binding['cells'].get(s['instance'])
        q.require(cell is not None and re.search(r'\\b'+re.escape(s['field'])+r'\\b',cell['model']),'Unbound scalar')
        q.require(s['expression']==expression(s['instance'],s['field']) and s['expression'] not in seen,'Changed/duplicate scalar expression')
        seen.add(s['expression'])
        if s['role']=='conductor':
            q.require(s['field'] in cell['ports'] and net_key(cell['ports'][s['field']])==s['conductor'],'Wrong native conductor')
        else:
            q.require(s['role']=='native_sequential_internal' and cell['sequential'] and s['field'] not in cell['ports'],'Wrong sequential internal')
    add='\\n  // NSSOC_NPU_WRITE_BEGIN: read-only exact source-bound observations.\\n'
    add+=f'  nssoc_npu_write_event_trace #(.WIDTH({len(signals)}),.START({start}),.LAST({last}),.MAX_EVENTS({MAX_EVENTS})) npu_cone (\\n'
    add+="    .clk_i(clk),.cycle_i({32'b0,cycles}),.signals_i({"+','.join(s['expression'] for s in reversed(signals))+'}));\\n'
    return bench.replace('endmodule',add+'  // NSSOC_NPU_WRITE_END\\nendmodule')
''')
replace_function('parse', '''def parse(log,directory,start=START,last=LAST,width=None,max_events=MAX_EVENTS):
    matches=re.findall(r'^NPU_WRITE_SUMMARY start=(\\d+) last=(\\d+) width=(\\d+) events=(\\d+) samples=(\\d+) sequence=(\\d+) final_cycle=(\\d+) armed=1$',log,re.M)
    q.require(len(matches)==1,'Missing/duplicate complete sparse summary')
    a,b,w,events,samples,total,final=map(int,matches[0]);width=w if width is None else width
    q.require((a,b,w)==(start,last,width) and 0<w<=MAX_SIGNALS and final>last and samples==last-start+1
        and 0<events<=max_events and total==events+samples+1,'Incomplete sparse window')
    lines=(Path(directory)/'npu-write-events.log').read_text().splitlines();q.require(len(lines)==total,'Incomplete sparse records')
    previous=None;event_count=0;sample_cycles=[];previous_time=-1;unknown=[];initial=None
    for seq,line in enumerate(lines,1):
        m=re.fullmatch(r'(INIT|EV|S) seq=(\\d+) cycle=(\\d+) realtime_ns=(\\d+\\.\\d{3})(.*)',line)
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
            scalar=re.fullmatch(r' signal=(\\d+) prior=([01xz]) value=([01xz])',m[5]);q.require(scalar is not None,'Invalid sparse scalar')
            index=int(scalar[1]);prior=scalar[2];value=scalar[3]
            q.require(0<=index<width and previous[index]==prior and prior!=value,'Invalid prior/new scalar transition')
            previous[index]=value;event_count+=1
            if value in 'xz':unknown.append(dict(sequence=seq,cycle=cycle,realtime_ns=m[4],signal=index,prior=prior,value=value))
    q.require(event_count==events and sample_cycles==list(range(start,last+1)),'Missing event or sample coverage')
    return dict(start=start,last=last,width=width,events=events,samples=samples,sequence=total,final_cycle=final,
        initial_static_unknowns=initial,new_unknown_transitions=unknown,first_new_unknown=unknown[0] if unknown else None,
        scope='Recorded scalar callbacks reconciled with each settled snapshot. Sparse events do not pretend to contain atomic live vectors or a simulator delta index.',
        raw_event_file=q.pin(Path(directory)/'npu-write-events.log'))
''')
# Head parity is outside this diagnostic's interface; retain existing tested
# native scalar controls adapted to sparse monitor and add regression in tests.
for fn in ('head_control_source','head_controls','parity_leaves'):
 t=ast.parse(s);node=next(x for x in t.body if isinstance(x,ast.FunctionDef) and x.name==fn)
 lines=s.splitlines(keepends=True);s=''.join(lines[:node.lineno-1]+lines[node.end_lineno:])
s=s.replace("binding=bind(net.read_text(),model.read_text(),variant);row['head_controls']=head_controls(tools/'iverilog',tools/'vvp',model,binding,output/'head-controls');row['evq_bindings']=binding", "binding=bind(net.read_text(),model.read_text(),variant);row['evq_bindings']=binding")
s=s.replace('Source-bound EVQ_OUT read-valid/parity observation; unchanged 3M native boot.','Source-bound full FIFO write and sync/LIF predecessor observation; unchanged 3M boot.')
p=R/'scripts/run_cloud_npu_write_trace.py';p.write_text(s);compile(s,str(p),'exec')
monitor=(R/'hw/soc/tb/npu_evq_event_trace.v').read_text().replace('npu_evq','npu_write').replace('npu-evq','npu-write').replace('NPU_EVQ','NPU_WRITE').replace('WIDTH>2048','WIDTH>8192')
monitor=monitor.replace('prior=%b value=%b all=%b",','prior=%b value=%b",').replace('sequence_no,cycle_i,$realtime,index,prior,value,signals_i);','sequence_no,cycle_i,$realtime,index,prior,value);')
monitor=monitor.replace('// Sequence is observed scheduler order, not an internal simulator delta index.','// Sequence is observed scheduler order, not an internal simulator delta index.\n// Sparse EV lines contain callback history only; INIT/S contain settled vectors.')
(R/'hw/soc/tb/npu_write_event_trace.v').write_text(monitor)
