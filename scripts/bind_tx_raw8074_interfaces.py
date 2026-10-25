#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Bind real tree semantics to the actual assembled8074-device native RC planes."""
import copy,json,sys
from pathlib import Path
import pya
P=Path(sys.argv[1]);out=Path(sys.argv[2])
physical=P/'physical';composed=P/'composed'
L=pya.Layout();L.read(str(physical/'layout/layout.gds'))
TOP='nssoc_tx_full32_raw64_handoff_candidate_v1'
top=L.cell(TOP);assert top is not None
core=[i for i in top.each_inst() if i.cell.name.split('$')[0]=='native_core']
assert len(core)==1
transform=core[0].trans
assert str(transform)==str(pya.Trans(600000,0)),'Actual core placement changed'
db=pya.LayoutVsSchematic();db.read(str(physical/'flat_lvs/result.lvsdb'))
c=db.netlist().circuit_by_name(TOP);assert c is not None and c.pin_count()==163
devices={d.id():d for d in c.each_device()};assert len(devices)==8074
geometry=json.loads((P/'wires/native01/result.json').read_text())
layers={int(k):db.layer_by_index(v) for k,v in geometry['native_layer_mapping'].items()}
native=json.loads((composed/'intrinsic/native.json').read_text())
contract=json.loads((composed/'composition.json').read_text())
anchors=json.loads((composed/'intrinsic/source/anchors.json').read_text())
rows={(r['device'],r['terminal']):r for r in anchors['rows']}
records={d['native_id']:d for d in contract['device_records']}
assert len(rows)==28582 and len(records)==8074 and set(records)==set(devices)
assert contract['counts']==dict(devices=8074,R=137221,C=98241,external_ports=164,physical_ports=163,metal_reference_planes=13344,body_nets=65,conductors=698,terminals=28582)
assert contract['no_ideal_driver_core_interconnect'] and contract['every_terminal_reference_plane_preserved']
# The composed terminal identity must agree with the independently reopened full LVS database.
native_devices={d['id']:d for d in native['devices']}
assert set(native_devices)==set(devices)
for did,d in devices.items():
    nd=native_devices[did];cls=d.device_class()
    assert nd['model']==cls.name
    assert nd['parameters']=={p.name:d.parameter(p.id()) for p in cls.parameter_definitions()}
    rec=records[did];terms={t['terminal']:t for t in rec['terminals']}
    assert set(terms)=={td.name for td in d.device_class().terminal_definitions()}
    for td in d.device_class().terminal_definitions():
        net=d.net_for_terminal(td.id());a=rows[did,td.name];t=terms[td.name]
        assert a['native_cluster']==t['native_cluster']==net.cluster_id
        assert a['disposition']==t['disposition']
        if 'reference_label' in a:
            assert t['reference_label']==a['reference_label']
            assert contract['wire_node_map'][a['reference_label']]==t['node']
cm=json.loads((physical/'source/core/layout/result.json').read_text())
handoff=json.loads((physical/'source/handoff-result.json').read_text())
plan=json.loads((P/'topology.json').read_text())['plan']
dx,dy=cm['origin_translation_um']
def shifted(text):
    b=pya.DBox.from_s(text)
    b=pya.Box(round((b.left+dx)/L.dbu),round((b.bottom+dy)/L.dbu),round((b.right+dx)/L.dbu),round((b.top+dy)/L.dbu))
    return b.transformed(transform)
def probe(metal,point):
    net=db.probe_net(layers[metal],point);assert net is not None,'Missing actual native conductor'
    return net
def endpoint(name):
    macro,port=name.split('.')
    box=shifted(cm['placements'][macro]['ports'][port])
    point=box.center();net=probe(134,point)
    return dict(endpoint=name,metal=134,point_dbu=[point.x,point.y],native_cluster=net.cluster_id,native_net=net.name)
hbts={}
for did,d in devices.items():
    if d.device_class().name!='npn13G2':continue
    box=pya.Box()
    for td in d.device_class().terminal_definitions():
        if td.name=='S':continue
        for region in db.shapes_of_terminal(d.terminal_ref(td.id())).values():box+=region.bbox()
    assert not box.empty();hbts[did]=box
assert len(hbts)==589
expected={}
for macro in plan['nodes']:
    label=macro['label'];box=shifted(cm['placements'][label]['bbox_um'])
    for bank,input_name in zip(('a','b'),macro['inputs'],strict=True):
        for suffix,childout in (('p','op'),('n','on')):
            key=input_name+suffix;assert key not in expected
            sink=endpoint(label+'.'+bank+suffix);endpoints=[sink]
            if not input_name.startswith('d'):
                source=endpoint(input_name+'.'+childout)
                assert source['native_cluster']==sink['native_cluster'],'Physical tree wire broken or swapped'
                endpoints.insert(0,source)
            terminals=[]
            for did,bounds in hbts.items():
                if (bounds & box)!=bounds:continue
                a=rows[did,'B']
                if a['native_cluster']!=sink['native_cluster']:continue
                assert a['disposition']=='ACTUAL_TERMINAL_METAL_REFERENCE_WITH_UNMODELED_DEVICE_ACCESS_R'
                rec=records[did];t=next(t for t in rec['terminals'] if t['terminal']=='B')
                assert t['native_cluster']==sink['native_cluster']
                terminals.append(dict(native_id=did,instance=rec['instance'],terminal='B',node=t['node'],reference_label=a['reference_label'],metal=a['metal'],point_dbu=a['point_dbu'],native_cluster=a['native_cluster']))
            assert len(terminals)==3,(key,len(terminals))
            expected[key]=dict(endpoints=endpoints,terminals=sorted(terminals,key=lambda t:t['native_id']))
assert len(expected)==124
assert len({t['native_id'] for r in expected.values() for t in r['terminals']})==372
assert len({t['node'] for r in expected.values() for t in r['terminals']})==372
public={p['name']:p['cluster'] for p in native['ports']}
assert set(public)=={p.name() for p in c.each_pin()}
drivers={}
for row in handoff['placements']:
    key=row['net'];assert key in expected and key not in drivers
    inp=pya.Box.from_s(row['pins_dbu']['din']).center()
    output=pya.Box.from_s(row['pins_dbu']['dout']).center()
    ni,no=probe(67,inp),probe(67,output)
    assert ni.cluster_id==public[key+'0']
    assert no.cluster_id==expected[key]['endpoints'][-1]['native_cluster']
    assert ni.cluster_id!=no.cluster_id,'Driver input/output shorted'
    drivers[key]=dict(public_input=key+'0',input_cluster=ni.cluster_id,output_cluster=no.cluster_id,input_point_dbu=[inp.x,inp.y],output_point_dbu=[output.x,output.y])
assert len(drivers)==64 and set(drivers)=={f'd{i}{leg}' for i in range(32) for leg in 'pn'}
def verify(references,driver_rows):
    assert set(references)==set(expected),'Missing logical input'
    for key,r in references.items():
        assert r['endpoints']==expected[key]['endpoints'],'Logical endpoint or polarity changed'
        assert r['terminals']==expected[key]['terminals'],'Native terminal/model plane changed'
    assert driver_rows==drivers,'Actual driver/core connection changed'
verify(expected,drivers)
controls=[]
for fault in ('missing_input','swapped_polarity','wrong_device','wrong_reference_node','missing_base','duplicate_base','wrong_plane','driver_input_output_swap'):
    refs=copy.deepcopy(expected);drvs=copy.deepcopy(drivers);key=next(iter(refs));term=refs[key]['terminals'][0]
    if fault=='missing_input':del refs[key]
    elif fault=='swapped_polarity':
        other=key[:-1]+('n' if key.endswith('p') else 'p');refs[key],refs[other]=refs[other],refs[key]
    elif fault=='wrong_device':term['native_id']=-1
    elif fault=='wrong_reference_node':term['node']='0'
    elif fault=='missing_base':refs[key]['terminals'].pop()
    elif fault=='duplicate_base':refs[key]['terminals'][1]=copy.deepcopy(term)
    elif fault=='wrong_plane':term['point_dbu'][0]+=1
    else:
        k=next(iter(drvs));drvs[k]['input_cluster'],drvs[k]['output_cluster']=drvs[k]['output_cluster'],drvs[k]['input_cluster']
    try:verify(refs,drvs)
    except AssertionError as error:controls.append(dict(name=fault,rejected=True,reason=str(error)))
    else:raise AssertionError('Accepted '+fault)
# Check actual endpoint polarity independently of the candidate-record controls.
physical_faults=[]
for source,sink in [('a.op','f.an'),('b.op','f.ap')]:
    a,b=endpoint(source),endpoint(sink)
    assert a['native_cluster']!=b['native_cluster']
    physical_faults.append(dict(source=source,sink=sink,rejected=True))
result=dict(status='PASS_ACTUAL8074_NATIVE124_INPUTS372_BASES64_DRIVER_HANDOFFS_REQUIRES_LOADED_WAVES',
    references=expected,drivers=drivers,modes={'wire':{k:['xtree.'+t['node'].lower() for t in v['terminals']] for k,v in expected.items()}},
    original_core_transform=str(transform),controls=controls,actual_endpoint_faults=physical_faults,
    model_counts=contract['counts'],all_native_terminals_checked=28582,
    no_ideal_driver_core_interconnect=True,qualified_pex=False,loaded_electrical_passed=False,full_serial_phy=False,mainchip_integrated=False)
out.write_text(json.dumps(result,indent=2)+'\n');print(result['status'])
