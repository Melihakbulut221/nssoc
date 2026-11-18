#!/usr/bin/env python3
"""Build provisional physical chip connectivity, keeping shell cells unplaced."""
import hashlib,json,os
from pathlib import Path
import odb
spec=json.loads(Path(os.environ['NSSOC_ASSEMBLY_INPUTS']).read_text())
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
for row in spec['inputs'].values():assert sha(row['path'])==row['sha256']
inputs={k:Path(v['path'])for k,v in spec['inputs'].items()};out=Path(spec['output'])
db=odb.dbDatabase.create()
# A technology-only LEF correctly returns no cell library. Validate its tech.
odb.read_lef(db,str(inputs['tech']))
assert db.getTech() and len(list(db.getTech().getLayers()))==19
for name in ['std','io','core_lef']:assert odb.read_lef(db,str(inputs[name]))
chip=odb.dbChip.create(db);block=odb.dbBlock.create(chip,'nssoc_chip');units=db.getTech().getDbUnitsPerMicron()
block.setDefUnits(units);block.setDieArea(odb.Rect(0,0,4000*units,3200*units))
module=json.loads(inputs['mapped'].read_text())['modules']['nssoc_chip']
placements=json.loads(inputs['placements'].read_text())
assert len(placements)==296 and len({p['instance'] for p in placements})==296
bits=set();names={};top={}
for name,p in module['ports'].items():
    for i,bit in enumerate(p['bits']):
        assert isinstance(bit,int)
        pn=name if len(p['bits'])==1 else f'{name}[{i}]'
        assert bit not in names,('Aliased top ports',pn)
        names[bit]=pn;top[pn]=(bit,p['direction']);bits.add(bit)
for c in module['cells'].values():
    for vector in c['connections'].values():
        for bit in vector:assert isinstance(bit,int)or bit in ('0','1');bits.add(bit)
nets={bit:odb.dbNet.create(block,names.get(bit,'const_'+bit if isinstance(bit,str)else 'n_'+str(bit)))for bit in bits}
supplies={n:nets[module['ports'][n]['bits'][0]]for n in ['VDD','VSS','IOVDD','IOVSS']}
assert len({n.getName()for n in supplies.values()})==4
for n,net in supplies.items():net.setSigType('GROUND'if n.endswith('VSS')else 'POWER')
for name,(bit,direction)in top.items():
    t=odb.dbBTerm.create(nets[bit],name);t.setIoType(direction.upper())
    if name in supplies:t.setSigType('GROUND'if name.endswith('VSS')else 'POWER')
instances={};expected={}
def instance(name,master):
    m=db.findMaster(master);assert m,('Missing LEF master',master)
    i=odb.dbInst.create(block,m,name);assert i;instances[name]=i;return i

def connect(i,pin,net):
    t=i.findITerm(pin);assert t,('Missing native terminal',i.getName(),pin)
    if t.getNet():assert t.getNet()==net
    else:t.connect(net)
    expected[(i.getName(),pin)]=net.getName()
for name,c in module['cells'].items():
    i=instance(name,c['type'])
    for pin,vector in c['connections'].items():
        for k,bit in enumerate(vector):connect(i,pin if len(vector)==1 else f'{pin}[{k}]',nets[bit])
for p in placements:
    if p['instance']not in instances:instance(p['instance'],p['master'])
    i=instances[p['instance']];assert i.getMaster().getName()==p['master']
    assert p['x_nm']*units%1000==0 and p['y_nm']*units%1000==0
    i.setOrient(['R0','R90','R180','R270'][p['rotation']]);i.setOrigin(p['x_nm']*units//1000,p['y_nm']*units//1000)
    i.setPlacementStatus('LOCKED')
for bit,master,pin in [('0','sg13g2_tielo','L_LO'),('1','sg13g2_tiehi','L_HI')]:
    if bit in nets:connect(instance('u_shell_const_'+bit,master),pin,nets[bit])
core=instances['u_core'];assert core.getMaster().getName()=='soc_top'
# Explicit provisional, site-grid-compatible translation; rebind final routed core.
core.setOrigin(round(336.96*units),round(362.88*units));core.setPlacementStatus('LOCKED')
for name,i in instances.items():
    master=i.getMaster().getName()
    if master=='soc_top':bind={'VPWR':'VDD','VGND':'VSS'}
    elif master.startswith(('sg13g2_IOPad','sg13g2_Filler','sg13g2_Corner')):
        bind={'vdd':'VDD','vss':'VSS','iovdd':'IOVDD','iovss':'IOVSS'}
    else:bind={'VDD':'VDD','VSS':'VSS'}
    for t in i.getITerms():
        m=t.getMTerm();pin=m.getName()
        if str(m.getSigType())in ('POWER','GROUND'):
            assert pin in bind,(master,pin);connect(i,pin,supplies[bind[pin]])
        assert t.getNet(),('Disconnected terminal',name,pin)
# Top pins are placed on the native IO terminal rectangles. This is not an ESD/bond qualification.
for name,(bit,direction)in top.items():
    if name in supplies:
        tail={'VDD':'Vdd','VSS':'Vss','IOVDD':'IOVdd','IOVSS':'IOVss'}[name]
        i=instances['u_supply_'+tail];terminal={'VDD':'vdd','VSS':'vss','IOVDD':'iovdd','IOVSS':'iovss'}[name]
    else:
        candidates=[t for t in nets[bit].getITerms()if t.getMTerm().getName()=='pad']
        assert len(candidates)==1,(name,len(candidates));i=candidates[0].getInst();terminal='pad'
    p=next(p for p in placements if p['instance']==i.getName())
    ox=p['x_nm']*units//1000;oy=p['y_nm']*units//1000
    bp=odb.dbBPin.create(block.findBTerm(name));bp.setPlacementStatus('PLACED');count=0
    for mp in i.findITerm(terminal).getMTerm().getMPins():
        for b in mp.getGeometry():
            points=[]
            for x,y in [(b.xMin(),b.yMin()),(b.xMin(),b.yMax()),(b.xMax(),b.yMin()),(b.xMax(),b.yMax())]:
                for _ in range(p['rotation']):x,y=-y,x
                points.append((x+ox,y+oy))
            odb.dbBox.create(bp,b.getTechLayer(),min(x for x,y in points),min(y for x,y in points),max(x for x,y in points),max(y for x,y in points));count+=1
    assert count>0,('Empty external pin',name)

def audit():
    for (name,pin),net in expected.items():
        t=block.findInst(name).findITerm(pin);assert t.getNet()and t.getNet().getName()==net,(name,pin)
    assert {n:core.findITerm(p).getNet().getName()for n,p in [('VDD','VPWR'),('VSS','VGND')]}=={'VDD':'VDD','VSS':'VSS'}
    return len(expected)
checked=audit();negative=[]
for label,term,wrong in [('missing_core_ground',core.findITerm('VGND'),None),
                          ('io_voltage_on_core',core.findITerm('VPWR'),supplies['IOVDD']),
                          ('missing_core_clock',core.findITerm('clk_i'),None)]:
    original=term.getNet();term.disconnect()
    if wrong:term.connect(wrong)
    try:audit()
    except AssertionError:negative.append(label)
    else:raise AssertionError('Fault accepted: '+label)
    term.disconnect();term.connect(original)
assert audit()==checked
fixed=[i for i in instances.values()if str(i.getPlacementStatus())=='LOCKED']
assert len(fixed)==297
for i in fixed:
    b=i.getBBox();assert b.xMin()>=0 and b.yMin()>=0 and b.xMax()<=4000*units and b.yMax()<=3200*units
    if i!=core:
        c=core.getBBox();assert min(b.xMax(),c.xMax())<=max(b.xMin(),c.xMin())or min(b.yMax(),c.yMax())<=max(b.yMin(),c.yMin())
def snapshot(b):
    return dict(instances=sorted((i.getName(),i.getMaster().getName(),str(i.getOrient()),str(i.getPlacementStatus()),i.getBBox().xMin(),i.getBBox().yMin(),i.getBBox().xMax(),i.getBBox().yMax())for i in b.getInsts()),
        connections=sorted((i.getName(),t.getMTerm().getName(),t.getNet().getName()if t.getNet()else None)for i in b.getInsts()for t in i.getITerms()),
        top=sorted((t.getName(),t.getNet().getName(),str(t.getIoType()),str(t.getSigType()))for t in b.getBTerms()))
before=snapshot(block);odb.write_db(db,str(out/'chip-initial.odb'));odb.write_def(block,str(out/'chip-initial.def'))
check=odb.dbDatabase.create();odb.read_db(check,str(out/'chip-initial.odb'));assert snapshot(check.getChip().getBlock())==before
for row in spec['inputs'].values():assert sha(row['path'])==row['sha256']
report=dict(status='PROVISIONAL_CHIP_DATABASE_CONNECTED_CORE_AND_PADS_FIXED_SHELL_UNPLACED',
    instances=len(instances),fixed_instances=len(fixed),unplaced_instances=len(instances)-len(fixed),top_bits=len(top),
    checked_terminal_connections=checked,supplies={n:net.getName()for n,net in supplies.items()},negative_controls=negative,
    core_translation_um=[336.96,362.88],odb_readback_equal=True,source_unchanged=True,
    physical_power_routed=False,signals_routed=False,final_core_route=False,timing_accepted=False,accepted=False,
    topology_sha256=hashlib.sha256(json.dumps(before,sort_keys=True).encode()).hexdigest())
(out/'native-result.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
