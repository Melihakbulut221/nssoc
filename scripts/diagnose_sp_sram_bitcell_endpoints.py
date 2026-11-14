#!/usr/bin/env python3
"""Read-only original bitcell endpoint diagnosis. Never an LVS acceptance gate."""
import hashlib,io,json,os,pathlib,subprocess,tarfile,zipfile
import klayout.db as kdb
P=pathlib.Path

def field(obj,name):
    v=getattr(obj,name)
    return v() if callable(v) else v

def digest(data):return hashlib.sha256(data).hexdigest()
b=subprocess.check_output(['gh','api','repos/'+os.environ['GITHUB_REPOSITORY']+'/actions/artifacts/14101208963/zip'],timeout=180)
assert digest(b)=='1227adf53d80628f0e6c8cf9c929c91b4e575b6754b0c5e9814443daa5147356'
z=zipfile.ZipFile(io.BytesIO(b));tgzs=[n for n in z.namelist() if n.endswith('.tgz')];assert len(tgzs)==1
with tarfile.open(fileobj=io.BytesIO(z.read(tgzs[0])),mode='r:gz') as t:
    data=t.extractfile('native/lvs.lvsdb').read()
assert digest(data)=='bddc01483e7388955407ada9e120124217a8476ffc26ccb89bc1931f6794e2f2'
P('/tmp/original-bitcell.lvsdb').write_bytes(data)
db=kdb.LayoutVsSchematic();db.read('/tmp/original-bitcell.lvsdb')
layout_netlist=field(db,'netlist');reference_netlist=field(db,'reference')
layout_circuit=layout_netlist.circuit_by_name('RM_IHPSG13_1P_BITKIT_CELL')
reference_circuit=reference_netlist.circuit_by_name('RM_IHPSG13_1P_BITKIT_CELL')
assert layout_circuit is not None and reference_circuit is not None

def inspect(c):
    # Read each terminal's outgoing pins directly. Duplicate net labels never
    # merge distinct conductors. Preserve duplicate pin names as a multiset.
    names=[field(n,'expanded_name') for n in c.each_net()]
    duplicate_net_name_count=len(names)-len(set(names))
    connected_port_count=sum(field(n,'pin_count') for n in c.each_net())
    resistors=[];bodies=[]
    for d in c.each_device():
        cls=field(d,'device_class');name=field(cls,'name');params={field(q,'name'):d.parameter(field(q,'id')) for q in field(cls,'parameter_definitions')}
        terminals=[]
        for term in field(cls,'terminal_definitions'):
            net=d.net_for_terminal(field(term,'id'));anchors=sorted(field(field(p,'pin'),'name').upper() for p in net.each_pin()) if net is not None else []
            terminals.append((field(term,'name'),anchors))
        if 'res' in name.lower():
            resistors.append({'name':field(d,'name'),'class':name,'L':params['L'],'W':params['W'],'signature':sorted([anchors for _,anchors in terminals])})
        else:
            bodies.extend({'model':name,'body_external_ports':anchors} for terminal,anchors in terminals if terminal.upper()=='B')
    assert len(resistors)==3
    assert any(x['body_external_ports'] for x in bodies) or c is layout_circuit, 'Reference MOS bodies must have named ports'
    return {'ports':sorted(field(pin,'name') for pin in c.each_pin()),'resistors':resistors,'mos_body_port_sets':bodies,'connected_port_count':connected_port_count,'duplicate_net_name_count':duplicate_net_name_count,'resistor_anchored_terminal_counts':[sum(bool(v) for v in r['signature']) for r in resistors]}
a=inspect(layout_circuit);b=inspect(reference_circuit);mapping=[]
for r in b['resistors']:
    hits=[x for x in a['resistors'] if x['signature']==r['signature'] and all(x['signature'])]
    mapping.append({'reference_name':r['name'],'reference_class':r['class'],'reference_L':r['L'],'reference_W':r['W'],'unique_external_endpoint_match':len(hits)==1,'candidate_layout_classes_and_dimensions':[{'class':x['class'],'L':x['L'],'W':x['W']} for x in hits]})
# Never export connectivity/net names or native databases: derived correspondence only.
result={'status':'DIAGNOSTIC_COMPLETE_NOT_LVS_ACCEPTANCE','source':os.environ['GITHUB_SHA'],'native_artifact':14101208963,'database_sha256':digest(data),'mapping':mapping,'anchor_counts':{label:{k:v[k] for k in ['connected_port_count','duplicate_net_name_count','resistor_anchored_terminal_counts']} for label,v in [('layout',a),('reference',b)]},'all_three_uniquely_anchored':all(x['unique_external_endpoint_match'] for x in mapping),'ports':{'layout':a['ports'],'reference':b['ports']},'mos_body_port_sets':{'layout':a['mos_body_port_sets'],'reference':b['mos_body_port_sets']},'scope':'Original unmodified comparison database. No geometry, reference, class, width, or port aliases changed. Direct Net.each_pin/NetPinRef.pin traversal avoids name-based net aliasing. External pin-name correspondence diagnoses only; duplicate names remain visible, not topology/signoff proof.'}
P('out').mkdir(exist_ok=True);P('out/bitcell-endpoint-diagnosis.json').write_text(json.dumps(result,indent=2))
print(json.dumps({'status':result['status'],'all_three_uniquely_anchored':result['all_three_uniquely_anchored']}))
