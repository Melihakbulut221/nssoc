#!/usr/bin/env python3
"""Native buffer-only ECO for measured parent control/reset fanout violations."""
import os,json,hashlib
from pathlib import Path
import odb
OUT=Path(os.environ['NSSOC_CONTROL_BUFFER_OUT'])
PREFIX='nssoc_ctrlbuf_'
TARGETS=[('$auto$ff.cc:337:slice$531','Q'),('$auto$ff.cc:337:slice$529','Q')]+[('$abc$1645$auto$blifparse.cc:397:parse_blif$'+str(n),p)for n,p in [(1835,'Y'),(1684,'Y'),(1836,'X'),(1685,'Y'),(1687,'X'),(1841,'Y')]]
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
def center(t):
    r=t.getInst().getBBox();return ((r.xMin()+r.xMax())//2,(r.yMin()+r.yMax())//2)
def main():
    source=OUT/'chip-detailedroute.odb';before=hashlib.sha256(source.read_bytes()).hexdigest()
    db,b=load(source);oldids={i.getName():identity(i)for i in b.getInsts()};oldcon=connections(b);oldgeom=geom(b)
    assert not any(n.startswith(PREFIX)for n in oldids)
    assert len(oldids)==1641
    manifest=[];newnets={};newbuffers=[]
    for index,(name,pin)in enumerate(TARGETS):
        inst=b.findInst(name);assert inst;driver=inst.findITerm(pin);assert driver and str(driver.getIoType())=='OUTPUT'
        net=driver.getNet();assert net and not list(net.getBTerms())and str(net.getSigType())not in ('POWER','GROUND','CLOCK')
        assert [t for t in net.getITerms()if str(t.getIoType())=='OUTPUT']==[driver]
        terminals=[t for t in net.getITerms()if t!=driver];assert len(terminals)>8 and all(str(t.getIoType())=='INPUT'for t in terminals)
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
                for pinname,power in [('VDD','VDD'),('VSS','VSS')]:
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
        if net.getWire():odb.dbWire.destroy(net.getWire());removed+=1
    assert removed==1615
    report=dict(original_instances=oldids,original_connections=[[list(k),v]for k,v in oldcon.items()],new_net_roots=newnets,new_buffers=newbuffers,targets=manifest,removed_stale_signal_wires=removed,original_instances_and_special_geometry_unchanged=True,buffer_only_terminal_equivalence=True,accepted=False,requires_legalization_routing_and_extracted_timing=True)
    odb.write_db(db,str(OUT/'chip-buffered.odb'));d2,b2=load(OUT/'chip-buffered.odb');assert connections(b2)==connections(b)and geom(b2)==oldgeom
    assert hashlib.sha256(source.read_bytes()).hexdigest()==before
    (OUT/'buffer-eco.json').write_text(json.dumps(report,indent=2)+'\n')
if __name__=='__main__':main()
