#!/usr/bin/env python3
"""Read-only original bitcell endpoint diagnosis. Never an LVS acceptance gate."""
import hashlib,io,json,os,pathlib,subprocess,tarfile,zipfile
import klayout.db as kdb
P=pathlib.Path

def field(obj,name):
    v=getattr(obj,name)
    return v() if callable(v) else v

def digest(data):return hashlib.sha256(data).hexdigest()
b=subprocess.check_output(['gh','api','repos/'+os.environ['GITHUB_REPOSITORY']+'/actions/artifacts/14099039829/zip'],timeout=180)
assert digest(b)=='b99ccd77e73bcf774597d9a67c030a1a89f18ae0a154e97f512805c354c6a563'
z=zipfile.ZipFile(io.BytesIO(b));tgzs=[n for n in z.namelist() if n.endswith('.tgz')];assert len(tgzs)==1
with tarfile.open(fileobj=io.BytesIO(z.read(tgzs[0])),mode='r:gz') as t:
    data=t.extractfile('native/lvs.lvsdb').read()
assert digest(data)=='c367b0565c64b00eedd2510d465d9c0d9cba64a7c2f79e4c04b5a9389bd49598'
P('/tmp/original-bitcell.lvsdb').write_bytes(data)
db=kdb.LayoutVsSchematic();db.read('/tmp/original-bitcell.lvsdb')
pairs=[p for p in db.xref().each_circuit_pair() if p.first() and p.first().name=='RM_IHPSG13_2P_BITKIT_CELL'];assert len(pairs)==1
pair=pairs[0]

def inspect(c):
    names=[field(n,'expanded_name') for n in c.each_net()]
    assert len(names)==len(set(names)), "Expanded net names must be unique within circuit"
    pins={}
    for pin in c.each_pin():
        net=c.net_for_pin(field(pin,'id'))
        if net is not None:pins.setdefault(field(net,'expanded_name'),[]).append(field(pin,'name').upper())
    resistors=[];bodies=[]
    for d in c.each_device():
        cls=field(d,'device_class');name=field(cls,'name');params={field(q,'name'):d.parameter(field(q,'id')) for q in field(cls,'parameter_definitions')}
        terminals=[]
        for term in field(cls,'terminal_definitions'):
            net=d.net_for_terminal(field(term,'id'));anchors=sorted(pins.get(field(net,'expanded_name'),[])) if net is not None else []
            terminals.append((field(term,'name'),anchors))
        if 'res' in name.lower():
            resistors.append({'name':field(d,'name'),'class':name,'L':params['L'],'W':params['W'],'signature':sorted([anchors for _,anchors in terminals])})
        else:
            bodies.extend({'model':name,'body_external_ports':anchors} for terminal,anchors in terminals if terminal.upper()=='B')
    assert len(resistors)==6
    return {'ports':sorted(field(pin,'name') for pin in c.each_pin()),'resistors':resistors,'mos_body_port_sets':bodies}
a=inspect(pair.first());b=inspect(pair.second());mapping=[]
for r in b['resistors']:
    hits=[x for x in a['resistors'] if x['signature']==r['signature'] and all(x['signature'])]
    mapping.append({'reference_name':r['name'],'reference_class':r['class'],'reference_L':r['L'],'reference_W':r['W'],'unique_external_endpoint_match':len(hits)==1,'candidate_layout_classes_and_dimensions':[{'class':x['class'],'L':x['L'],'W':x['W']} for x in hits]})
# Never export connectivity/net names or native databases: derived correspondence only.
result={'status':'DIAGNOSTIC_COMPLETE_NOT_LVS_ACCEPTANCE','source':os.environ['GITHUB_SHA'],'native_artifact':14099039829,'database_sha256':digest(data),'mapping':mapping,'all_six_uniquely_anchored':all(x['unique_external_endpoint_match'] for x in mapping),'ports':{'layout':a['ports'],'reference':b['ports']},'mos_body_port_sets':{'layout':a['mos_body_port_sets'],'reference':b['mos_body_port_sets']},'scope':'Original unmodified comparison database. No geometry, reference, class, width, or port aliases changed. Matching named external endpoints diagnoses correspondence only; not topology/signoff proof.'}
P('out').mkdir(exist_ok=True);P('out/bitcell-endpoint-diagnosis.json').write_text(json.dumps(result,indent=2))
print(json.dumps({'status':result['status'],'all_six_uniquely_anchored':result['all_six_uniquely_anchored']}))
