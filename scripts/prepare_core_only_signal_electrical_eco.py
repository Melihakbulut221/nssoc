#!/usr/bin/env python3
"""Native buffer-only ECO for measured parent control/reset fanout violations."""
import os,json,hashlib
from pathlib import Path
import odb
OUT=Path(os.environ['NSSOC_CONTROL_BUFFER_OUT'])
PREFIX='nssoc_elecbuf_'
inventory=json.loads((OUT/'load-inventory.json').read_text())
assert inventory['violating_drivers']==171 and inventory['source_unchanged']
clock_rows=[r for r in inventory['rows']if r['net_signal_type']=='CLOCK']
assert len(clock_rows)==1 and clock_rows[0]['driver']=='clkbuf_6_31_0_clk_npu/X'
TARGETS=[tuple(r['driver'].rsplit('/',1))for r in inventory['rows']if r['net_signal_type']!='CLOCK']
assert len(TARGETS)==170

def load(path):
    d=odb.dbDatabase.create();odb.read_db(d,str(path));return d,d.getChip().getBlock()
def geom(b):
    shapes=[]
    for n in b.getNets():
        for w in n.getSWires():
            for x in w.getWires():
                if x.isVia():v=x.getTechVia()or x.getBlockVia();shapes.append((n.getName(),'via',v.getName(),*x.getViaXY()))
                else:shapes.append((n.getName(),'metal',x.getTechLayer().getName(),x.xMin(),x.yMin(),x.xMax(),x.yMax()))
    ports=sorted((t.getName(),t.getNet().getName(),str(t.getIoType()),str(t.getSigType()),sorted((str(p.getPlacementStatus()),sorted((x.getTechLayer().getName(),x.xMin(),x.yMin(),x.xMax(),x.yMax())for x in p.getBoxes()))for p in t.getBPins()))for t in b.getBTerms())
    return sorted(shapes),ports
def identity(i):
    r=i.getBBox();return (i.getMaster().getName(),str(i.getOrient()),r.xMin(),r.yMin(),r.xMax(),r.yMax())
def connections(b):return {(i.getName(),t.getMTerm().getName()):t.getNet().getName()if t.getNet()else None for i in b.getInsts()for t in i.getITerms()}
def terminal_key(t):return (t.getInst().getName(),t.getMTerm().getName())
def center(t):
    r=t.getInst().getBBox();return ((r.xMin()+r.xMax())//2,(r.yMin()+r.yMax())//2)
def main():
    source=OUT/'chip-detailedroute.odb';before=hashlib.sha256(source.read_bytes()).hexdigest()
    db,b=load(source);oldids={i.getName():identity(i)for i in b.getInsts()};oldcon=connections(b);oldgeom=geom(b)
    assert not any(n.startswith(PREFIX)for n in oldids)
    assert len(oldids)==104891
    original_statuses={i.getName():str(i.getPlacementStatus())for i in b.getInsts()}
    original_flags={n.getName():n.isDoNotTouch()for n in b.getNets()}
    for row in inventory['rows']:
        inst,pin=row['driver'].rsplit('/',1);term=b.findInst(inst).findITerm(pin);net=term.getNet()
        assert net.getName()==row['net'] and str(net.getSigType())==row['net_signal_type']
        sinks={t.getInst().getName()+'/'+t.getMTerm().getName()for t in net.getITerms()if str(t.getIoType())=='INPUT'}
        assert sinks=={s['pin']for s in row['sinks']},row['driver']

    manifest=[];newnets={};newbuffers=[]
    for index,(name,pin)in enumerate(TARGETS):
        inst=b.findInst(name);assert inst;driver=inst.findITerm(pin);assert driver and str(driver.getIoType())=='OUTPUT'
        net=driver.getNet();assert net and not list(net.getBTerms())and str(net.getSigType())not in ('POWER','GROUND','CLOCK')
        drivers=[terminal_key(t)for t in net.getITerms()if str(t.getIoType())=='OUTPUT']
        assert drivers==[terminal_key(driver)],dict(net=net.getName(),expected=terminal_key(driver),actual=drivers)
        terminals=[t for t in net.getITerms()if terminal_key(t)!=terminal_key(driver)];assert len(terminals)>8 and all(str(t.getIoType())=='INPUT'for t in terminals)
        root=net.getName();count=len(terminals);level=0;added=[]
        while len(terminals)>8:
            points=[center(t)for t in terminals];axis=max(range(2),key=lambda a:max(p[a]for p in points)-min(p[a]for p in points))
            terminals.sort(key=lambda t:(center(t)[axis],center(t)[1-axis],t.getInst().getName(),t.getMTerm().getName()))
            nextlevel=[]
            for start in range(0,len(terminals),8):
                group=terminals[start:start+8];tag=f'{PREFIX}{index}_{level}_{start//8}'
                master=db.findMaster('sg13g2_buf_4'if level==0 else 'sg13g2_buf_8');assert master
                cell=odb.dbInst.create(b,master,tag);wire=odb.dbNet.create(b,tag+'_net');assert cell and wire
                avg=tuple(sum(center(t)[a]for t in group)//len(group)for a in range(2))
                anchor=min(group,key=lambda t:sum(abs(center(t)[a]-avg[a])for a in range(2))).getInst().getBBox()
                cell.setLocation(anchor.xMin(),anchor.yMin());cell.setPlacementStatus('PLACED')
                cell.findITerm('A').connect(net);cell.findITerm('X').connect(wire)
                for pinname,power in [('VDD','VPWR'),('VSS','VGND')]:
                    t=cell.findITerm(pinname);assert t and b.findNet(power);t.connect(b.findNet(power))
                for t in group:t.connect(wire)
                newnets[wire.getName()]=root;newbuffers.append(tag);added.append(tag);nextlevel.append(cell.findITerm('A'))
            terminals=nextlevel;level+=1
        manifest.append(dict(driver=name+'/'+pin,net=root,original_sinks=count,remaining_root_sinks=len(terminals),buffers=added,levels=level))
    # Fix all existing instances during incremental legalization; new buffers move.
    for i in b.getInsts():
        if i.getName()in oldids and str(i.getPlacementStatus())=='PLACED':i.setPlacementStatus('FIRM')
    actual=connections(b)
    for key,value in oldcon.items():assert newnets.get(actual[key],actual[key])==value,(key,value,actual[key])
    assert all(identity(b.findInst(n))==v for n,v in oldids.items())and geom(b)==oldgeom
    # Pure non-inverting-buffer paths must terminate on the original source net.
    for name in newbuffers:
        cell=b.findInst(name);assert cell.getMaster().getName()in ('sg13g2_buf_4','sg13g2_buf_8')
        a=cell.findITerm('A').getNet().getName();x=cell.findITerm('X').getNet().getName();assert newnets.get(a,a)==newnets[x]
        assert len([t for t in cell.findITerm('X').getNet().getITerms()if str(t.getIoType())=='INPUT'])<=8
    assert all(len([t for t in b.findNet(x['net']).getITerms()if str(t.getIoType())=='INPUT'])<=8 for x in manifest)
    removed=0
    for net in b.getNets():
        net.clearGuides()
        if net.getWire():odb.dbWire.destroy(net.getWire());removed+=1
    assert removed==0
    report=dict(original_instances=oldids,original_connections=[[list(k),v]for k,v in oldcon.items()],new_net_roots=newnets,new_buffers=newbuffers,targets=manifest,removed_stale_signal_wires=removed,original_instances_and_special_geometry_unchanged=True,buffer_only_terminal_equivalence=True,accepted=False,requires_legalization_routing_and_extracted_timing=True)
    odb.write_db(db,str(OUT/'repair-input.odb'));d2,b2=load(OUT/'repair-input.odb');assert connections(b2)==connections(b)and geom(b2)==oldgeom
    assert hashlib.sha256(source.read_bytes()).hexdigest()==before
    (OUT/'buffer-eco.json').write_text(json.dumps(report,indent=2)+'\n')
    selection=dict(targets={m['net']:dict(driver=m['driver'])for m in manifest},original_net_flags=original_flags,original_placement_statuses=original_statuses,excluded_clock_drivers=[r['driver']for r in clock_rows],antenna_cells_deleted=0,accepted=False)
    (OUT/'repair-selection.json').write_text(json.dumps(selection,indent=2)+'\n')

if __name__=='__main__':main()
