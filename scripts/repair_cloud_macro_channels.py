#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Native placement-only experiment for source-bound SRAM-channel congestion.

Run by OpenROAD Python on hosted runners. Selected combinational endpoint
cells, and explicitly selected data flip-flops in the incremental profile,
may move near SRAM channels; every other cell is temporarily fixed. Exact
connectivity, masters and all unselected positions are checked after native
legalization. Nothing is an adopted design or timing/route signoff.
"""
import hashlib
import json
import os
import re
from pathlib import Path
import odb

OUT = Path('cloud-newer-postcts')
SOURCE = OUT / 'inputs/postcts.odb'
SOURCE_SHA = 'e4e04605899913e69784bc32d4fabc39350fec8b975c6fdab095a6b95262d292'
DIAGNOSIS_SHA = '1d19f4d2bdf24f865144b28c57060c3cfed96ac3d0a4a79b23ce23f12c0a027c'


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream,'sha256').hexdigest()


def load(path):
    db=odb.dbDatabase.create();odb.read_db(db,str(path))
    return db,db.getChip().getBlock()


def signature(block):
    h=hashlib.sha256()
    for inst in sorted(block.getInsts(),key=lambda i:i.getName()):
        row=[inst.getName(),inst.getMaster().getName(),
             sorted((t.getMTerm().getName(),t.getNet().getName() if t.getNet() else None)
                    for t in inst.getITerms())]
        h.update((json.dumps(row,separators=(',',':'))+'\n').encode())
    for net in sorted(block.getNets(),key=lambda n:n.getName()):
        row=[net.getName(),str(net.getSigType()),sorted(t.getName() for t in net.getBTerms())]
        h.update((json.dumps(row,separators=(',',':'))+'\n').encode())
    return h.hexdigest()


def position(inst):
    return [*inst.getLocation(),str(inst.getOrient())]


def boundary_geometry(block):
    return {term.getName(): sorted((box.getTechLayer().getName(),box.xMin(),box.yMin(),box.xMax(),box.yMax())
            for pin in term.getBPins() for box in pin.getBoxes()) for term in block.getBTerms()}


def check(block,before):
    assert signature(block)==before['connectivity_sha256'],'Connectivity or masters changed'
    assert boundary_geometry(block)=={k:[tuple(x) for x in v] for k,v in before['boundary_geometry'].items()}, 'Boundary pin geometry changed'
    actual={i.getName():i for i in block.getInsts()}
    assert set(actual)==set(before['instances']),'Instance set changed'
    selected=set(before['selected'])
    for name,row in before['instances'].items():
        if name not in selected:
            assert position(actual[name])==row['position'],'Unselected placement changed: '+name
    return actual


def prepare():
    source=SOURCE;source_sha=SOURCE_SHA
    assert sha(SOURCE)==SOURCE_SHA
    depth=int(os.environ.get('NSSOC_ETHERNET_HOLD_DEPTH','0'));assert depth in (0,2)
    if depth:
        evidence=json.loads(Path('docs/evidence/cloud-ethernet-hold-estimate-20261013.json').read_text())
        case=next(c for c in evidence['cases'] if c['depth']==depth)
        assert case['logic']['status']=='PASS within scope' and case['inversion_control']=='EXPECTED_FUNCTIONAL_CHANGE_REJECTED'
        source=OUT/'inputs/ethernet-hold.odb';source_sha=case['candidate_odb_sha256']
        assert sha(source)==source_sha
    requested_profile=os.environ['NSSOC_PLACEMENT_PROFILE']
    routability=requested_profile=='routability_data'
    incremental=requested_profile in ('local_data_endpoints','routability_data')
    diagnosis_sha=DIAGNOSIS_SHA
    diagnosis_odb_sha=SOURCE_SHA
    if incremental:
        assert depth==2, 'Incremental source includes the proven Ethernet hold ECO'
        evidence_path = ('docs/evidence/cloud-seed13-buffers-route-failure-20261014.json' if routability
            else 'docs/evidence/cloud-local-optimize-buffers-route-failure-20261013.json')
        evidence=json.loads(Path(evidence_path).read_text())
        failure_outputs=evidence['failure_outputs']
        source=OUT/'inputs/previous-relocated.odb'
        source_sha=failure_outputs['relocated-placement.odb']
        assert sha(source)==source_sha
        diagnosis_odb_sha=failure_outputs['failed-global.odb']
        diagnosis_sha=('ca29ac20363e4f419ee3577dbd91085e48b541f91ca8d89f48e4bae72d46f01b' if routability
            else '962bf2b58b82799d346cb48a45a5af1d88fac6c10a2b582a2c41fc445000917f')
        failed_path=OUT/'inputs/previous-failed-global.odb'
        assert sha(failed_path)==diagnosis_odb_sha
        failed_db,failed_block=load(failed_path)
        candidate_db,candidate_block=load(source)
        assert signature(candidate_block)==signature(failed_block)
        failed_instances={i.getName():i for i in failed_block.getInsts()}
        assert all(position(i)==position(failed_instances[i.getName()]) for i in candidate_block.getInsts()), 'Failed-route diagnosis does not match resumed placement'
        hold_db,hold_block=load(OUT/'inputs/ethernet-hold.odb')
        assert signature(candidate_block)==signature(hold_block), 'Previous placement changed the proven hold-ECO connectivity'
    path=OUT/'endpoint-diagnosis.json';assert sha(path)==diagnosis_sha
    d=json.loads(path.read_text());assert d['source_odb_sha256']==diagnosis_odb_sha
    db,block=load(source);scale=block.getDbUnitsPerMicron()
    instances={i.getName():i for i in block.getInsts()}
    seen={p['instance']:p for net in d['all_congested_net_endpoints'].values() for p in net['terminals']}
    # Bind every diagnosed endpoint before selecting a broader data-only
    # placement domain. The new profile starts from the exact132-overflow DB.
    for name,p in seen.items():
        inst=instances[name]; box=inst.getBBox()
        assert [v/scale for v in (box.xMin(),box.yMin(),box.xMax(),box.yMax())]==p['bbox_um']
        assert inst.getMaster().getName()==p['master']
    preserved_hold=[]
    if routability:
        original_db,original_block=load(SOURCE)
        original_names={i.getName() for i in original_block.getInsts()}
        preserved_hold=sorted(set(instances)-original_names)
        assert len(preserved_hold)==20
        assert original_names <= set(instances)
        seen={}
        for name,inst in instances.items():
            box=inst.getBBox()
            seen[name]=dict(master=inst.getMaster().getName(),macro=inst.getMaster().isBlock(),
                bbox_um=[v/scale for v in (box.xMin(),box.yMin(),box.xMax(),box.yMax())])
    selected={}
    eligible_before_clock=[]
    include_data_buffers=requested_profile in ('local_optimize_buffers','local_data_endpoints','routability_data')
    for name,p in seen.items():
        inst=instances[name];b=inst.getBBox()
        actual=[v/scale for v in (b.xMin(),b.yMin(),b.xMax(),b.yMax())]
        assert actual==p['bbox_um'] and inst.getMaster().getName()==p['master']
        data_flop=incremental and not routability and p['master']=='sg13g2_dfrbpq_1'
        eligible=name.startswith('$abc$') or data_flop or (include_data_buffers and
            p['master'].startswith(('sg13g2_buf_','sg13g2_inv_')))
        upper_y=1750 if include_data_buffers else 1700
        in_x=(2280<=actual[0]<=3300) if incremental else actual[0]>=2340
        in_y=1180<=actual[1]<=upper_y
        if routability:
            eligible=bool(re.fullmatch(r'sg13g2_(?:a[0-9]+o?i?|o[0-9]+a?i?|and[0-9]+|nand[0-9]+|or[0-9]+|nor[0-9]+|xor[0-9]+|xnor[0-9]+|inv|buf|mux[0-9]+)_[0-9]+',p['master']))
            eligible=eligible and name not in preserved_hold and str(inst.getPlacementStatus())=='PLACED'
            in_x=in_y=True
        if not(eligible and not p['macro'] and in_x and in_y):
            continue
        eligible_before_clock.append(name)
        if include_data_buffers and not data_flop and any(t.getNet() and
               (str(t.getNet().getSigType())=='CLOCK' or t.getNet().getName().startswith('clknet_'))
               for t in inst.getITerms()):
            continue  # Only explicit data flops may have clock input connections.
        # Guard against mapped combinational clock gating despite its ABC name.
        if any(str(t.getIoType())=='OUTPUT' and t.getNet() and
               (str(t.getNet().getSigType())=='CLOCK' or t.getNet().getName().startswith('clknet_'))
               for t in inst.getITerms()):
            continue
        assert str(inst.getPlacementStatus())=='PLACED',name
        selected[name]=inst
    # Exact spatial/master envelope from the frozen diagnosis, before native
    # clock-connectivity exclusion. The old932bound described ABC-only cells.
    expected_envelope=1821 if incremental else (1563 if include_data_buffers else 932)
    if routability:
        assert len(selected)>1563, 'Routability profile must exceed prior narrow endpoint selection'
        expected_envelope=len(eligible_before_clock)
    assert len(eligible_before_clock)==expected_envelope
    assert 0<len(selected)<=expected_envelope
    before=dict(connectivity_sha256=signature(block),boundary_geometry=boundary_geometry(block),source_odb_sha256=source_sha,original_odb_sha256=SOURCE_SHA,
        selected=sorted(selected),eligible_before_clock_count=len(eligible_before_clock),profile=os.environ['NSSOC_PLACEMENT_PROFILE'],
        diagnosis_sha256=diagnosis_sha, diagnosis_odb_sha256=diagnosis_odb_sha,
        preserved_hold_cells=preserved_hold,
        selected_data_flops=[n for n,i in selected.items() if i.getMaster().getName()=='sg13g2_dfrbpq_1'],
        instances={n:dict(position=position(i),status=str(i.getPlacementStatus())) for n,i in instances.items()})
    if routability:
        assert not before['selected_data_flops'] and not set(preserved_hold)&set(selected)
    elif incremental:
        assert len(before['selected_data_flops'])==227, 'Changed source-bound data-flop envelope'
    profile=before['profile'];assert profile in ('left_compact','left_spread','local_optimize','local_optimize_buffers','local_data_endpoints','routability_data')
    xstart,width={'left_compact':(2110.,160.),'left_spread':(2010.,260.),'local_optimize':(0.,0.),'local_optimize_buffers':(0.,0.),'local_data_endpoints':(0.,0.),'routability_data':(0.,0.)}[profile]
    for name,inst in instances.items():
        if name not in selected:
            if str(inst.getPlacementStatus())=='PLACED':inst.setPlacementStatus('FIRM')
        else:
            if profile in ('local_optimize','local_optimize_buffers','local_data_endpoints','routability_data'):
                continue  # Native DPO starts from the exact original positions.
            x,y=inst.getLocation()
            fraction=(x/scale-2340.)/(3266.4-2340.)
            assert 0<=fraction<=1
            inst.setLocation(round((xstart+width*fraction)*scale),y)
    assert signature(block)==before['connectivity_sha256']
    (OUT/'placement-before.json').write_text(json.dumps(before,separators=(',',':'))+'\n')
    odb.write_db(db,str(OUT/'proposed-placement.odb'))
    print(json.dumps(dict(selected=len(selected),profile=profile,source_sha256=source_sha)),flush=True)


def verify():
    before=json.loads((OUT/'placement-before.json').read_text())
    db,block=load(OUT/'legalized-placement.odb')
    actual=check(block,before)
    # Two native in-memory corruption controls. Restore and recheck each before
    # writing the candidate: these do not alter the preserved source database.
    fixed=next(i for n,i in actual.items() if n not in before['selected'] and not i.getMaster().isBlock())
    old=fixed.getLocation();fixed_status=str(fixed.getPlacementStatus())
    # OpenDB itself forbids moving FIRM instances. Explicitly unlock only this
    # in-memory negative-control victim, then restore its original status.
    fixed.setPlacementStatus('PLACED')
    fixed.setLocation(old[0]+block.getDbUnitsPerMicron(),old[1])
    try:check(block,before)
    except AssertionError:pass
    else:raise AssertionError('Fixed-cell displacement escaped verification')
    fixed.setLocation(*old);fixed.setPlacementStatus(fixed_status);check(block,before)
    pin=next(t for t in actual[before['selected'][0]].getITerms() if t.getNet())
    net=pin.getNet();pin.disconnect()
    try:check(block,before)
    except AssertionError:pass
    else:raise AssertionError('Disconnected cell pin escaped verification')
    pin.connect(net);check(block,before)
    changed={n:dict(before=before['instances'][n]['position'],after=position(actual[n]))
             for n in before['selected'] if position(actual[n])!=before['instances'][n]['position']}
    assert changed,'Placement experiment produced no movement'
    for name,inst in actual.items():inst.setPlacementStatus(before['instances'][name]['status'])
    check(block,before)
    path=OUT/'relocated-placement.odb';odb.write_db(db,str(path))
    report=dict(status='PASS_NATIVE_PLACEMENT_ONLY_INVARIANTS_REQUIRES_STA_AND_ROUTING',
        profile=before['profile'],source_odb_sha256=before['source_odb_sha256'],
        original_odb_sha256=before.get('original_odb_sha256',SOURCE_SHA),output_odb_sha256=sha(path),
        connectivity_sha256=before['connectivity_sha256'],instances=len(actual),
        diagnosis_sha256=before['diagnosis_sha256'], diagnosis_odb_sha256=before['diagnosis_odb_sha256'],
        selected_data_flop_count=len(before['selected_data_flops']),
        preserved_hold_cells=before.get('preserved_hold_cells',[]),
        boundary_geometry_unchanged=True,
        changed_data_flop_count=sum(n in changed for n in before['selected_data_flops']),
        selected_count=len(before['selected']),eligible_before_clock_count=before['eligible_before_clock_count'],changed_count=len(changed),changed=changed,
        native_fault_controls=['unselected_cell_displacement_rejected','disconnected_cell_pin_rejected'])
    (OUT/'placement-repair.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k!='changed'}),flush=True)


def prepare_cugr_input():
    """Remove only three proved empty database declarations, never a terminal."""
    source=OUT/'relocated-placement.odb'
    assert sha(source)=='660692b3e59756186bb017a62823999db593fa9d77b6e4181be9625fa7bfb707'
    diagnosis=OUT/'cugr-empty-net-diagnosis.json'
    assert sha(diagnosis)=='f1d71b542a4e46f5475ee77bd4e4b7f58c5c05f6aad91e1f0151d7400c68b5b8'
    proof=json.loads(diagnosis.read_text())
    assert proof['source_odb_sha256']=='f10edd96a44037f3a20c48bd8cb1c61e93dee4857180fbdc1106db94d9d2fa8b'
    inventory=proof['signal_net_terminal_inventory']
    wanted={'u_ibex.u_ibex_core.cs_registers_i.mstack_d[2]',
        'u_pcie.flow.packets.endpoint.endpoint.header_words[0]',
        'u_pcie.flow.packets.endpoint.endpoint.transmit_packet.header_words[0]'}
    assert {r['name'] for r in inventory['low_degree_nets'] if r['physical_terminal_count']==0}==wanted
    db,block=load(source)
    def snapshot():
        return dict(instances={i.getName():dict(master=i.getMaster().getName(),position=position(i),
            status=str(i.getPlacementStatus())) for i in block.getInsts()},
            boundary=boundary_geometry(block),
            nets={n.getName():dict(signal_type=str(n.getSigType()),
                iterms=sorted((t.getInst().getName(),t.getMTerm().getName()) for t in n.getITerms()),
                bterms=sorted(t.getName() for t in n.getBTerms())) for n in block.getNets()})
    before=snapshot();counts={}
    for row in before['nets'].values():
        if row['signal_type'] not in ('POWER','GROUND'):
            degree=str(len(row['iterms'])+len(row['bterms']));counts[degree]=counts.get(degree,0)+1
    assert counts==inventory['count_by_degree']
    def require_empty(net):
        assert net is not None
        assert not list(net.getITerms()) and not list(net.getBTerms()), 'A real terminal cannot be removed'
        assert str(net.getSigType()) not in ('POWER','GROUND')
        assert net.getWire() is None and not list(net.getSWires()) and not list(net.getGuides()), 'Routed geometry cannot be removed'
    victim=block.findNet('can_rx_i')
    assert victim is not None and len(list(victim.getBTerms()))==1
    try: require_empty(victim)
    except AssertionError: pass
    else: raise AssertionError('Single-port net escaped empty-net guard')
    assert snapshot()==before
    actual_empty={name for name,row in before['nets'].items()
        if row['signal_type'] not in ('POWER','GROUND') and not row['iterms'] and not row['bterms']}
    assert actual_empty==wanted
    for name in sorted(wanted):
        net=block.findNet(name);require_empty(net);odb.dbNet.destroy(net)
    after=snapshot();expected={**before,'nets':{n:r for n,r in before['nets'].items() if n not in wanted}}
    assert after==expected, 'Retained terminals, nets, instances or pin geometry changed'
    assert len(after['nets'])==len(before['nets'])-3
    path=OUT/'cugr-input.odb';odb.write_db(db,str(path))
    report=dict(status='PASS_EXACT_THREE_ZERO_TERMINAL_DECLARATIONS_REMOVED',
        source_odb_sha256=sha(source),output_odb_sha256=sha(path),diagnosis_sha256=sha(diagnosis),
        removed_empty_declarations=sorted(wanted),all_retained_net_terminals_identical=True,
        all_instances_masters_positions_status_identical=True,boundary_pin_geometry_identical=True,
        original_non_pg_cardinality=counts,single_port_net_rejection_control=True,
        scope='Only three unconnected/unrouted database declarations; all302single-terminal nets retained, every real signal/clock/PG pin and instance unchanged. Not route or timing acceptance.')
    (OUT/'cugr-input-proof.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report),flush=True)



def verify_fresh_prects():
    """Exact placement graph, then transparent inserted CTS buffers only.

    This structural proof covers the digital buffer insertion, not electrical
    timing, transistor behavior or full serial PHY equivalence.
    """
    original_db,original=load(OUT/'prects.odb')
    assert sha(OUT/'prects.odb')=='4739da2254a80397ab82f5c70550b9215e7ac5853c0e78cd0fb7dabefece20d8'
    def fixed_geometry(block):
        return (boundary_geometry(block), {i.getName():[i.getMaster().getName(),position(i)]
            for i in block.getInsts() if i.getMaster().isBlock()},
            [block.getDieArea().xMin(),block.getDieArea().yMin(),block.getDieArea().xMax(),block.getDieArea().yMax()])
    gp_db,gp=load(OUT/'prects-placement.odb')
    assert signature(gp)==signature(original),'Placement changed circuit'
    assert fixed_geometry(gp)==fixed_geometry(original),'Placement changed fixed geometry'
    original_instances={i.getName():i for i in original.getInsts()}
    gp_instances={i.getName():i for i in gp.getInsts()}
    moved=[n for n,i in gp_instances.items() if position(i)!=position(original_instances[n])]
    moved_flops=[n for n in moved if gp_instances[n].getMaster().getName().startswith('sg13g2_df')]
    assert moved_flops, 'New trial must actually move data flops before CTS'
    report=dict(status='PASS_EXACT_PRECTS_PLACEMENT_CONNECTIVITY',moved_instances=len(moved),
        moved_data_flops=len(moved_flops),source_instances=len(original_instances),
        placement_sha256=sha(OUT/'prects-placement.odb'))
    if os.environ['NSSOC_PLACEMENT_MODE']=='verify_prects':
        (OUT/'prects-placement-proof.json').write_text(json.dumps(report,indent=2)+'\n');return
    cts_db,cts=load(OUT/'fresh-cts.odb')
    assert fixed_geometry(cts)==fixed_geometry(original),'CTS changed fixed geometry'
    def prove():
        actual={i.getName():i for i in cts.getInsts()}
        assert set(original_instances)<=set(actual),'CTS removed an original instance'
        added=set(actual)-set(original_instances)
        assert added,'CTS inserted no clock buffers'
        roots={}; dummy_loads=[]; buffer_inputs=[]
        for n in added:
            inst=actual[n]
            master=inst.getMaster().getName()
            if n.startswith('clkload'):
                # Frozen TritonCTS.cpp:2430-2437 includes inverters as dummy
                # candidates;2525-2528 connects only their input. Never treat
                # an inverter driving a real net as a transparent buffer.
                assert re.fullmatch(r'sg13g2_(?:buf|inv)_(?:1|2|4|8|16)',master),(n,master)
                inputs=[t for t in inst.getITerms() if str(t.getIoType())=='INPUT' and str(t.getSigType()) not in ('POWER','GROUND')]
                outputs=[t for t in inst.getITerms() if str(t.getIoType())=='OUTPUT' and str(t.getSigType()) not in ('POWER','GROUND')]
                assert len(inputs)==len(outputs)==1,(n,master,'Dummy pin cardinality')
                a,x=inputs[0],outputs[0]
                assert x.getNet() is None,('Dummy output must remain unconnected',n,master)
            else:
                assert master in {'sg13g2_buf_2','sg13g2_buf_4','sg13g2_buf_8','sg13g2_buf_16'},('Unexpected CTS cell',n,master)
                a=inst.findITerm('A');x=inst.findITerm('X')
                assert x and x.getNet(),('Functional CTS buffer output missing',n)
            assert a and x and a.getNet(),('Incomplete CTS buffer input',n)
            buffer_inputs.append(a.getNet())
            if x.getNet():
                drivers=sorted((t.getInst().getName(),t.getMTerm().getName())
                    for t in x.getNet().getITerms() if str(t.getIoType())=='OUTPUT')
                # SWIG wrapper equality is not native object identity. Bind the
                # unique physical instance/pin; multiple drivers still reject.
                assert drivers==[(n,'X')],('Multiple CTS drivers',n,drivers)
            else:
                # Native CTS explicitly inserts balancing dummy loads. An
                # added buffer with no output connection cannot drive an
                # original terminal; every original terminal is checked below.
                dummy_loads.append(n)
            power=[t for t in inst.getITerms() if str(t.getSigType()) in ('POWER','GROUND')]
            assert {str(t.getSigType()) for t in power}=={'POWER','GROUND'},('Missing supply pins',n)
            for t in power:
                assert t.getNet() and str(t.getNet().getSigType())==str(t.getSigType()),('Unconnected CTS supply',n,t.getMTerm().getName())
                source_net=original.findNet(t.getNet().getName())
                assert source_net and str(source_net.getSigType())==str(t.getSigType()),('New supply domain',n)
            if x.getNet():
                key=x.getNet().getName();assert key not in roots
                roots[key]=a.getNet().getName()
        def root(net):
            n=net.getName() if net else None;seen=set()
            while n in roots:
                assert n not in seen,'Cycle in inserted clock graph'
                seen.add(n);n=roots[n]
            return n
        original_nets={n.getName() for n in original.getNets()}
        for n in roots:
            assert root(cts.findNet(n)) in original_nets,('Unanchored CTS tree',n)
        assert all(root(n) in original_nets for n in buffer_inputs),'Unanchored dummy/buffer input'
        checked=0
        for n,inst in original_instances.items():
            other=actual[n]
            assert other.getMaster().getName()==inst.getMaster().getName(),('Original master changed',n)
            for term in inst.getITerms():
                pin=term.getMTerm().getName();other_term=other.findITerm(pin);assert other_term
                expected=term.getNet().getName() if term.getNet() else None
                assert root(other_term.getNet())==expected,('Original terminal changed',n,pin,expected,root(other_term.getNet()))
                checked+=1
        before={t.getName():t.getNet().getName() if t.getNet() else None for t in original.getBTerms()}
        after={t.getName():root(t.getNet()) for t in cts.getBTerms()}
        assert before==after,'Boundary connectivity changed'
        return dict(inserted_transparent_buffers=len(added),original_terminals_checked=checked,
            undriven_added_dummy_outputs=sorted(dummy_loads),driver_identity='native instance name and MTerm pin name')
    report['cts']=prove()
    fault=next(t for i in cts.getInsts() if i.getName() in original_instances
        for t in i.getITerms() if t.getNet() and str(t.getSigType()) not in ('POWER','GROUND'))
    net=fault.getNet();fault.disconnect()
    try:
        try:prove()
        except AssertionError:report['actual_terminal_disconnect_negative_control']=True
        else:raise RuntimeError('Disconnected actual terminal accepted')
    finally:fault.connect(net)
    assert prove()==report['cts']
    supply_fault=next(t for i in cts.getInsts() if i.getName() not in original_instances
        for t in i.getITerms() if str(t.getSigType())=='POWER')
    supply=supply_fault.getNet();supply_fault.disconnect()
    try:
        try:prove()
        except AssertionError:report['actual_cts_supply_disconnect_negative_control']=True
        else:raise RuntimeError('Disconnected CTS supply accepted')
    finally:supply_fault.connect(supply)
    assert prove()==report['cts']
    dummy_name=report['cts']['undriven_added_dummy_outputs'][0]
    dummy=cts.findInst(dummy_name)
    output=next(t for t in dummy.getITerms() if str(t.getIoType())=='OUTPUT')
    assert output.getNet() is None
    output.connect(net)
    try:
        try:prove()
        except AssertionError:report['actual_dummy_output_drive_negative_control']=True
        else:raise RuntimeError('Connected dummy output accepted')
    finally:output.disconnect()
    assert prove()==report['cts']
    report['dummy_load_masters']={n:cts.findInst(n).getMaster().getName()
        for n in report['cts']['undriven_added_dummy_outputs']}
    report['dummy_implementation_source']='https://github.com/The-OpenROAD-Project/OpenROAD/blob/dcf36133a369abc8f3c5e5738cd4d82e4903c0e0/src/cts/src/TritonCTS.cpp#L2430'
    report['inserted_buffer_power_and_ground_connected_to_original_domains']=True
    report.update(status='PASS_PLACEMENT_AND_TRANSPARENT_CTS_GRAPH_NOT_TIMING',
        cts_sha256=sha(OUT/'fresh-cts.odb'),scope='Original masters and every terminal preserved modulo inserted non-inverting CTS buffer trees. Source unchanged; no timing or route acceptance.')
    (OUT/'fresh-cts-proof.json').write_text(json.dumps(report,indent=2)+'\n')


def packet_net_records(block):
    """Exact output-net endpoints of the original physical packet flops."""
    scale=block.getDbUnitsPerMicron()
    rows={}
    for net in block.getNets():
        name=net.getName()
        rendered=re.sub(r'\\([\[\]])',r'\1',name)
        if not re.fullmatch(r'u_pcie\.receive_ownership\.packets\[\d+\]\[\d+\]',rendered):
            continue
        assert str(net.getSigType())=='SIGNAL' and not list(net.getBTerms())
        terms=list(net.getITerms())
        drivers=[t for t in terms if str(t.getIoType())=='OUTPUT']
        assert len(drivers)==1 and drivers[0].getMTerm().getName()=='Q'
        assert drivers[0].getInst().getMaster().getName()=='sg13g2_dfrbpq_1'
        pins=[]
        for term in terms:
            inst=term.getInst();r=term.getBBox()
            assert not inst.getMaster().isBlock()
            pins.append(dict(instance=inst.getName(),pin=term.getMTerm().getName(),
                direction=str(term.getIoType()),master=inst.getMaster().getName(),
                center_um=[(r.xMin()+r.xMax())/(2*scale),(r.yMin()+r.yMax())/(2*scale)]))
        xs=[p['center_um'][0] for p in pins];ys=[p['center_um'][1] for p in pins]
        rows[name]=dict(driver=drivers[0].getInst().getName(),pins=pins,
            endpoint_hpwl_um=max(xs)-min(xs)+max(ys)-min(ys),
            endpoint_envelope_um=[min(xs),min(ys),max(xs),max(ys)])
    assert len(rows)==1216,'Original packet-bit net census changed'
    assert len({r['driver'] for r in rows.values()})==1216
    return rows


def prepare_packet_clusters():
    """Group small connected first-level packet read cones before fresh CTS.

    Placement clusters add only optimization guidance. They never replace
    cells, merge logical nets, omit route endpoints or alter clock constraints.
    """
    assert os.environ.get('GITHUB_ACTIONS')=='true'
    path=OUT/'prects.odb'
    assert sha(path)=='4739da2254a80397ab82f5c70550b9215e7ac5853c0e78cd0fb7dabefece20d8'
    db,block=load(path);before=signature(block)
    rows=packet_net_records(block)
    diagnostic=OUT/'packet-endpoint-diagnosis.json'
    assert sha(diagnostic)=='ca29ac20363e4f419ee3577dbd91085e48b541f91ca8d89f48e4bae72d46f01b'
    diagnosis=json.loads(diagnostic.read_text())
    assert diagnosis['report_overflow_sum']==132
    diagnosed={n:r for n,r in diagnosis['all_congested_net_endpoints'].items()
               if 'u_pcie.receive_ownership.packets' in n}
    assert len(diagnosed)==193
    for name,row in diagnosed.items():
        drivers=[t for t in row['terminals'] if t['direction']=='OUTPUT']
        assert len(drivers)==1
        assert rows[name]['driver']==drivers[0]['instance']
        assert drivers[0]['pin']=='Q' and drivers[0]['master']=='sg13g2_dfrbpq_1'
    instances={i.getName():i for i in block.getInsts()}
    allowed=re.compile(r'sg13g2_(?:a[0-9]+o?i?|o[0-9]+a?i?|and[0-9]+|nand[0-9]+b?|or[0-9]+|nor[0-9]+b?|xor[0-9]+|xnor[0-9]+|inv|buf|mux[0-9]+)_[0-9]+')
    parents={}
    def root(n):
        parents.setdefault(n,n)
        if parents[n]!=n:parents[n]=root(parents[n])
        return parents[n]
    def union(a,b):
        a,b=root(a),root(b)
        if a!=b:parents[max(a,b)]=min(a,b)
    excluded=[]
    for name,row in rows.items():
        driver=row['driver'];root(driver)
        for pin in row['pins']:
            if pin['instance']==driver:continue
            inst=instances[pin['instance']]
            eligible=pin['direction']=='INPUT' and bool(allowed.fullmatch(pin['master']))
            eligible=eligible and str(inst.getPlacementStatus())=='PLACED'
            eligible=eligible and not any(t.getNet() and
                (str(t.getNet().getSigType())=='CLOCK' or t.getNet().getName().startswith('clknet_'))
                for t in inst.getITerms())
            if eligible:union(driver,pin['instance'])
            else:excluded.append(dict(net=name,**pin))
    grouped={}
    for name in sorted(parents):grouped.setdefault(root(name),[]).append(name)
    groups=sorted(grouped.values())
    sizes=[len(g) for g in groups]
    preliminary=dict(status='SOURCE_BOUND_CLUSTER_INVENTORY_NOT_YET_PLACED',
        source_odb_sha256=sha(path),connectivity_sha256=before,packet_bit_nets=len(rows),
        diagnosed_congested_packet_nets=len(diagnosed),cluster_sizes=sizes,
        clusters=groups,excluded_direct_sinks=excluded,source_net_endpoints=rows)
    (OUT/'packet-clusters.json').write_text(json.dumps(preliminary,indent=2)+'\n')
    assert groups and min(sizes)>=2 and max(sizes)<=32,('Not small disjoint cones',min(sizes),max(sizes))
    assert len({n for g in groups for n in g})==sum(sizes)
    assert all(str(instances[n].getPlacementStatus())=='PLACED' and
        not instances[n].getMaster().isBlock() for g in groups for n in g)
    assert {r['driver'] for r in rows.values()} <= set(parents)
    # Native findInst resolves exact names; get_cells wildcard interpretation
    # is deliberately avoided for Yosys dollar/bracket instance identifiers.
    tcl=['set packet_block [ord::get_db_block]']
    for group in groups:
        tcl.append('set packet_cluster {}')
        for name in group:
            assert not any(c in name for c in '{}\\\n\r')
            tcl += ['set packet_inst [$packet_block findInst {'+name+'}]',
                'if {$packet_inst == "NULL"} {error "Packet cluster instance absent"}',
                'lappend packet_cluster $packet_inst']
        tcl += [f'if {{[llength $packet_cluster] != {len(group)}}} {{error "Packet cluster cardinality"}}',
                'gpl::placement_cluster_cmd $packet_cluster']
    tcl.append(f'puts NSSOC_PACKET_CLUSTERS_{len(groups)}_INSTANCES_{sum(sizes)}')
    (OUT/'packet-clusters.tcl').write_text('\n'.join(tcl)+'\n')
    assert signature(block)==before and sha(path)==preliminary['source_odb_sha256']
    preliminary.update(status='PASS_EXACT_PRECTS_PACKET_CLUSTER_GUIDANCE_NOT_IMPLEMENTATION',
        source_diagnosis_sha256=sha(diagnostic),guidance_sha256=sha(OUT/'packet-clusters.tcl'),
        native_command_source='https://github.com/The-OpenROAD-Project/OpenROAD/blob/dcf36133a369abc8f3c5e5738cd4d82e4903c0e0/src/gpl/src/replace.i',
        scope='Small disjoint first-level packet data cones only. All cells and nets remain; placement connectivity, rebuilt CTS, strict routing, all-corner timing and detailed-route signoff are still required.')
    (OUT/'packet-clusters.json').write_text(json.dumps(preliminary,indent=2)+'\n')


def measure_packet_cluster_placement():
    proof=json.loads((OUT/'packet-clusters.json').read_text())
    assert proof['status']=='PASS_EXACT_PRECTS_PACKET_CLUSTER_GUIDANCE_NOT_IMPLEMENTATION'
    db,block=load(OUT/'prects-placement.odb')
    assert signature(block)==proof['connectivity_sha256']
    after=packet_net_records(block);before=proof['source_net_endpoints']
    assert set(after)==set(before)
    for name,row in before.items():
        key=lambda p:(p['instance'],p['pin'],p['direction'],p['master'])
        assert sorted(map(key,row['pins']))==sorted(map(key,after[name]['pins']))
    stats={}
    congested=json.loads((OUT/'packet-endpoint-diagnosis.json').read_text())['all_congested_net_endpoints']
    for label,names in [('all_packet_bits',sorted(before)),
                        ('previously_congested_packet_bits',sorted(n for n in before
                         if n in congested))]:
        stats[label]=dict(nets=len(names),
            original_endpoint_hpwl_um=sum(before[n]['endpoint_hpwl_um'] for n in names),
            candidate_endpoint_hpwl_um=sum(after[n]['endpoint_hpwl_um'] for n in names))
    (OUT/'packet-cluster-placement.json').write_text(json.dumps(dict(
        status='COMPLETE_PACKET_ENDPOINT_GEOMETRY_NOT_ROUTE_OR_TIMING_ACCEPTANCE',
        candidate_odb_sha256=sha(OUT/'prects-placement.odb'),
        statistics=stats,source_guidance_sha256=proof['guidance_sha256'],
        candidate_net_endpoints=after),indent=2)+'\n')


if __name__=='__main__':
    mode=os.environ['NSSOC_PLACEMENT_MODE'];assert mode in ('prepare','verify','prepare_cugr','verify_prects','verify_fresh_cts','prepare_packet_clusters','measure_packet_clusters')
    if mode in ('verify_prects','verify_fresh_cts'): verify_fresh_prects()
    elif mode=='prepare_cugr': prepare_cugr_input()
    elif mode=='prepare_packet_clusters': prepare_packet_clusters()
    elif mode=='measure_packet_clusters': measure_packet_cluster_placement()
    else: prepare() if mode=='prepare' else verify()
