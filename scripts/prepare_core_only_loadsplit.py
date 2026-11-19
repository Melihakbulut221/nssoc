#!/usr/bin/env python3
"""Twenty-one load buffers on eight measured nets; frozen original geometry and logical identity."""
import os,json,re,copy
from pathlib import Path
import odb
from buffer_core_only_chip_controls import load,identity,geom,connections
OUT=Path(os.environ['NSSOC_CRITICAL_ECO_OUT']);mode=os.environ['NSSOC_CRITICAL_ECO_MODE']
SPEC=[('nssoc_sta_i_8564', 'Y', 'sg13g2_o21ai_1', 'nssoc_sta_n_100391', 'sg13g2_buf_8', [('load_slew1735', 'A'), ('ANTENNA_1616', 'A'), ('ANTENNA_1614', 'A')]), ('nssoc_sta_i_8564', 'Y', 'sg13g2_o21ai_1', 'nssoc_sta_n_100391', 'sg13g2_buf_8', [('load_slew1736', 'A'), ('wire1734', 'A'), ('ANTENNA_1617', 'A'), ('ANTENNA_1615', 'A')]), ('nssoc_sta_i_52754', 'Y', 'sg13g2_o21ai_1', 'nssoc_sta_n_53514', 'sg13g2_buf_8', [('nssoc_sta_i_52768', 'A2'), ('nssoc_sta_i_57628', 'A1')]), ('nssoc_sta_i_63235', 'Y', 'sg13g2_nand2_1', 'nssoc_sta_n_62713', 'sg13g2_buf_8', [('nssoc_sta_i_65893', 'A1'), ('nssoc_sta_i_64404', 'A')]), ('nssoc_sta_i_63235', 'Y', 'sg13g2_nand2_1', 'nssoc_sta_n_62713', 'sg13g2_buf_8', [('nssoc_sta_i_66252', 'A1'), ('nssoc_sta_i_66332', 'B2'), ('ANTENNA_1383', 'A'), ('ANTENNA_1379', 'A'), ('ANTENNA_1386', 'A'), ('ANTENNA_1382', 'A')]), ('nssoc_sta_i_63235', 'Y', 'sg13g2_nand2_1', 'nssoc_sta_n_62713', 'sg13g2_buf_8', [('nssoc_sta_i_64309', 'B'), ('nssoc_sta_i_63261', 'B2'), ('ANTENNA_1373', 'A'), ('ANTENNA_1377', 'A'), ('ANTENNA_1385', 'A'), ('ANTENNA_1381', 'A'), ('ANTENNA_1371', 'A'), ('ANTENNA_1375', 'A')]), ('nssoc_sta_i_63235', 'Y', 'sg13g2_nand2_1', 'nssoc_sta_n_62713', 'sg13g2_buf_8', [('nssoc_sta_i_64131', 'A1'), ('nssoc_sta_i_65864', 'A'), ('ANTENNA_1372', 'A'), ('ANTENNA_1376', 'A'), ('ANTENNA_1384', 'A'), ('ANTENNA_1380', 'A'), ('ANTENNA_1374', 'A'), ('ANTENNA_1378', 'A')]), ('fanout5181', 'X', 'sg13g2_buf_1', 'net5181', 'sg13g2_buf_8', [('nssoc_sta_i_8881', 'B1'), ('nssoc_sta_i_8855', 'B1'), ('nssoc_sta_i_8808', 'B1'), ('nssoc_sta_i_8979', 'B1')]), ('fanout5181', 'X', 'sg13g2_buf_1', 'net5181', 'sg13g2_buf_8', [('nssoc_sta_i_8797', 'B1'), ('nssoc_sta_i_8776', 'B1'), ('nssoc_sta_i_8711', 'B1'), ('nssoc_sta_i_8705', 'B1')]), ('nssoc_sta_i_78307', 'Q', 'sg13g2_dfrbpq_1', 'nssoc_sta_n_95189', 'sg13g2_buf_8', [('nssoc_sta_i_59630', 'A'), ('nssoc_sta_i_48888', 'A'), ('nssoc_sta_i_48842', 'B')]), ('nssoc_sta_i_78307', 'Q', 'sg13g2_dfrbpq_1', 'nssoc_sta_n_95189', 'sg13g2_buf_8', [('nssoc_sta_i_54325', 'A'), ('nssoc_sta_i_19259', 'A1'), ('nssoc_sta_i_18485', 'A1'), ('nssoc_sta_i_11349', 'A')]), ('nssoc_sta_i_78698', 'Q', 'sg13g2_dfrbpq_1', 'nssoc_sta_n_95548', 'sg13g2_buf_8', [('nssoc_sta_i_60494', 'A'), ('nssoc_sta_i_49007', 'A'), ('nssoc_sta_i_49039', 'A')]), ('nssoc_sta_i_78698', 'Q', 'sg13g2_dfrbpq_1', 'nssoc_sta_n_95548', 'sg13g2_buf_8', [('nssoc_sta_i_55723', 'A'), ('nssoc_sta_i_18642', 'B2'), ('nssoc_sta_i_19776', 'B2'), ('nssoc_sta_i_10968', 'A1')]), ('fanout4366', 'X', 'sg13g2_buf_1', 'net4366', 'sg13g2_buf_8', [('nssoc_sta_i_53821', 'A1'), ('nssoc_sta_i_54195', 'A'), ('ANTENNA_2436', 'A')]), ('fanout4366', 'X', 'sg13g2_buf_1', 'net4366', 'sg13g2_buf_8', [('nssoc_sta_i_56557', 'A1'), ('nssoc_sta_i_56970', 'B2'), ('ANTENNA_2437', 'A'), ('ANTENNA_2438', 'A'), ('ANTENNA_2432', 'A'), ('ANTENNA_2428', 'A')]), ('fanout4366', 'X', 'sg13g2_buf_1', 'net4366', 'sg13g2_buf_8', [('nssoc_sta_i_51869', 'A1'), ('nssoc_sta_i_52478', 'A'), ('ANTENNA_2429', 'A'), ('ANTENNA_2433', 'A'), ('ANTENNA_2430', 'A'), ('ANTENNA_2427', 'A'), ('ANTENNA_2434', 'A')]), ('fanout4366', 'X', 'sg13g2_buf_1', 'net4366', 'sg13g2_buf_8', [('nssoc_sta_i_51562', 'A1'), ('nssoc_sta_i_53469', 'A1'), ('ANTENNA_2431', 'A'), ('ANTENNA_2435', 'A')]), ('fanout5013', 'X', 'sg13g2_buf_1', 'net5013', 'sg13g2_buf_8', [('nssoc_sta_i_28657', 'A1'), ('nssoc_sta_i_37377', 'A'), ('ANTENNA_1830', 'A'), ('ANTENNA_1832', 'A'), ('ANTENNA_1838', 'A'), ('ANTENNA_1836', 'A'), ('ANTENNA_1837', 'A'), ('ANTENNA_1831', 'A')]), ('fanout5013', 'X', 'sg13g2_buf_1', 'net5013', 'sg13g2_buf_8', [('nssoc_sta_i_45509', 'B'), ('nssoc_sta_i_45710', 'B'), ('ANTENNA_1839', 'A'), ('ANTENNA_1833', 'A'), ('ANTENNA_1834', 'A'), ('ANTENNA_1840', 'A')]), ('fanout5013', 'X', 'sg13g2_buf_1', 'net5013', 'sg13g2_buf_8', [('nssoc_sta_i_45366', 'B'), ('nssoc_sta_i_45365', 'B'), ('ANTENNA_1841', 'A'), ('ANTENNA_1835', 'A')]), ('fanout5013', 'X', 'sg13g2_buf_1', 'net5013', 'sg13g2_buf_8', [('nssoc_sta_i_45288', 'A'), ('nssoc_sta_i_45837', 'A1')])]
def function(text,name):
 m=re.search(r'cell\s*\(\s*"?'+re.escape(name)+r'"?\s*\)\s*\{',text);assert m
 j=m.end();start=j;depth=1
 while depth:depth+=(text[j]=='{')-(text[j]=='}');j+=1
 f=re.findall(r'\bfunction\s*:\s*([^;]+)',text[start:j]);assert len(f)==1
 return f[0].strip().strip('"')
d,b=load(OUT/'source.odb');assert len(list(b.getInsts()))==446672
if mode=='prepare':
 statuses={i.getName():str(i.getPlacementStatus())for i in b.getInsts()};before=connections(b);newcells={};moves={}
 # Every original load on these eight nets must be explicitly assigned once.
 assigned={}
 for name,pin,old,netname,mastername,sinks in SPEC:
  assigned.setdefault(netname,[]).extend(sinks)
 for netname,sinks in assigned.items():
  net=b.findNet(netname);assert net and not list(net.getBTerms())
  actual={(t.getInst().getName(),t.getMTerm().getName())for t in net.getITerms()if str(t.getIoType())=='INPUT'}
  assert len(sinks)==len(set(sinks)) and set(sinks)==actual,(netname,sinks,actual)
 expected_diodes={'ANTENNA_2427', 'ANTENNA_1380', 'ANTENNA_1835', 'ANTENNA_1385', 'ANTENNA_1614', 'ANTENNA_1378', 'ANTENNA_1840', 'ANTENNA_1375', 'ANTENNA_2438', 'ANTENNA_1830', 'ANTENNA_1831', 'ANTENNA_1615', 'ANTENNA_1372', 'ANTENNA_1833', 'ANTENNA_1837', 'ANTENNA_1371', 'ANTENNA_1377', 'ANTENNA_2432', 'ANTENNA_1374', 'ANTENNA_2428', 'ANTENNA_2433', 'ANTENNA_1376', 'ANTENNA_1384', 'ANTENNA_2430', 'ANTENNA_1386', 'ANTENNA_2434', 'ANTENNA_1381', 'ANTENNA_1382', 'ANTENNA_2437', 'ANTENNA_1834', 'ANTENNA_1373', 'ANTENNA_1838', 'ANTENNA_1616', 'ANTENNA_1617', 'ANTENNA_2429', 'ANTENNA_1839', 'ANTENNA_1383', 'ANTENNA_1836', 'ANTENNA_2436', 'ANTENNA_1379', 'ANTENNA_2435', 'ANTENNA_2431', 'ANTENNA_1841', 'ANTENNA_1832'}
 actual_diodes={sn for sinks in assigned.values()for sn,sp in sinks if b.findInst(sn).getMaster().getName()=='sg13g2_antennanp'}
 assert actual_diodes==expected_diodes

 for index,(name,pin,old,netname,mastername,sinks)in enumerate(SPEC):
  assert function((OUT/'std.lib').read_text(),mastername)=='A'
  driver=b.findInst(name);assert driver and driver.getMaster().getName()==old
  net=driver.findITerm(pin).getNet();assert net.getName()==netname and str(net.getSigType())=='SIGNAL'and not list(net.getBTerms())
  assert sum(str(t.getIoType())=='OUTPUT'for t in net.getITerms())==1
  tag='nssoc_loadsplit_'   +str(index);assert not b.findInst(tag)and not b.findNet(tag+'_net')
  master=d.findMaster(mastername);assert master
  cell=odb.dbInst.create(b,master,tag);wire=odb.dbNet.create(b,tag+'_net');wire.setSigType('SIGNAL')
  cell.setOrient(driver.getOrient());x,y=driver.getLocation();cell.setLocation(x+driver.getMaster().getWidth()+480,y);cell.setPlacementStatus('PLACED')
  cell.findITerm('A').connect(net);cell.findITerm('X').connect(wire)
  for kind in ['POWER','GROUND']:
   supplies={t.getNet().getName():t.getNet()for t in driver.getITerms()if str(t.getSigType())==kind};assert len(supplies)==1
   terms=[t for t in cell.getITerms()if str(t.getSigType())==kind];assert len(terms)==1;terms[0].connect(next(iter(supplies.values())))
  for sn,sp in sinks:
   sink=b.findInst(sn);assert sink,('missing_sink',sn)
   t=sink.findITerm(sp);assert t and t.getNet(),('missing_connected_terminal',sn,sp)
   actual=t.getNet().getName();assert actual==netname and str(t.getIoType())=='INPUT',('unexpected_sink_connection',sn,sp,actual,netname,str(t.getIoType()))
   t.connect(wire);moves[sn+'/'+sp]=dict(old=netname,new=wire.getName())
  newcells[tag]=dict(master=mastername,input=netname,output=wire.getName(),initial_xy=list(cell.getLocation()))
 for i in b.getInsts():
  if i.getName()in statuses and statuses[i.getName()]=='PLACED':i.setPlacementStatus('FIRM')
 for netname in [v[3]for v in SPEC]:
  n=b.findNet(netname);n.clearGuides()
  if n.getWire():odb.dbWire.destroy(n.getWire())
 odb.write_db(d,str(OUT/'before-legalize.odb'));(OUT/'plan.json').write_text(json.dumps(dict(original_statuses=statuses,new_cells=newcells,moves=moves),indent=2)+'\n')
elif mode=='audit':
 dd,bb=load(OUT/'legalized.odb');plan=json.loads((OUT/'plan.json').read_text());old={i.getName():i for i in b.getInsts()};new={i.getName():i for i in bb.getInsts()}
 assert set(new)-set(old)==set(plan['new_cells'])and set(old)<=set(new)
 assert geom(b)==geom(bb)
 for name,i in old.items():assert identity(i)==identity(new[name]),name
 oldnets={n.getName():str(n.getSigType())for n in b.getNets()};newnets={n.getName():str(n.getSigType())for n in bb.getNets()};assert all(newnets[n]==v for n,v in oldnets.items())
 assert set(newnets)-set(oldnets)=={v['output']for v in plan['new_cells'].values()}
 before=connections(b);after=connections(bb)
 for key,value in before.items():
  moved=plan['moves'].get('/'.join(key));assert after[key]==(moved['new']if moved else value),key
 for name,info in plan['new_cells'].items():
  i=new[name];assert i.getMaster().getName()==info['master']and str(i.getPlacementStatus())=='PLACED'
  assert i.findITerm('A').getNet().getName()==info['input']and i.findITerm('X').getNet().getName()==info['output']
  x,y=i.getLocation();ox,oy=info['initial_xy'];assert abs(x-ox)+abs(y-oy)<=100*bb.getDbUnitsPerMicron()
  for t in i.getITerms():assert t.getNet()and str(t.getSigType())==str(t.getNet().getSigType())
 # Collapse the verified identity buffers and prove all original terminal nets recover exactly.
 collapsed={k:v for k,v in after.items()if k[0]in old};reverse={v['output']:v['input']for v in plan['new_cells'].values()}
 collapsed={k:reverse.get(v,v)for k,v in collapsed.items()};assert collapsed==before
 damaged=dict(collapsed);first=next(iter(before));damaged[first]='__fault__';assert damaged!=before
 for name,i in old.items():new[name].setPlacementStatus(plan['original_statuses'][name])
 # Compare serialized DEF net records to prove all unaffected route geometry
 # and terminal lists survive legalization, including every clock net.
 def records(block,path):
  odb.write_def(block,str(path))
  text=path.read_text();match=re.search(r'^NETS (\d+) ;\n(.*?)^END NETS',text,re.M|re.S);assert match
  entries=re.findall(r'^[ \t]*- (\S+) (.*?);',match.group(2),re.M|re.S)
  result={name:' '.join(body.split()) for name,body in entries};assert len(result)==len(entries)==int(match.group(1)),(len(result),len(entries),match.group(1))
  return result
 left=records(b,OUT/'source-route-audit.def');right=records(bb,OUT/'candidate-route-audit.def')
 changed={v[3]for v in SPEC}|{v['output']for v in plan['new_cells'].values()}
 checked=0
 for name,value in left.items():
  if name not in changed and str(b.findNet(name).getSigType())not in ['POWER','GROUND']:assert right.get(name)==value,('unaffected_route_changed',name);checked+=1
 assert checked==443086,checked
 clocks=[n for n in b.getNets()if str(n.getSigType())=='CLOCK'];assert len(clocks)==2113
 assert all(left[n.getName()]==right[n.getName()]for n in clocks)
 for net in b.getNets():
  oldrule=net.getNonDefaultRule();newrule=bb.findNet(net.getName()).getNonDefaultRule()
  assert (oldrule.getName()if oldrule else None)==(newrule.getName()if newrule else None),('ndr_assignment_changed',net.getName())
 for name in changed:assert not bb.findNet(name).getWire()
 (OUT/'preserved-route-audit.json').write_text(json.dumps(dict(unchanged_def_net_records=checked,changed_nets=sorted(changed),clock_routes_preserved=True,checked_clock_nets=2113,ndr_assignments_preserved=True,requires_incremental_routing=True),indent=2)+'\n')
 diode_moves={}
 for name,i in old.items():
  if i.getMaster().getName()!='sg13g2_antennanp':continue
  original=i.findITerm('A').getNet().getName();updated=new[name].findITerm('A').getNet().getName()
  if original!=updated:
   assert plan['moves'][name+'/A']==dict(old=original,new=updated)
   diode_moves[name]=dict(master='sg13g2_antennanp',old_net=original,new_net=updated)
 assert len(diode_moves)==44
 for netname in changed:
  net=bb.findNet(netname)
  assert sum(str(t.getIoType())=='INPUT' for t in net.getITerms())<=8
 (OUT/'diode-reconnection-audit.json').write_text(json.dumps(dict(moves=diode_moves,all_original_diodes_preserved=True,functional_equivalence_by_identity_buffer_collapse=True,antenna_protection_revalidation_required=True,accepted=False),indent=2)+'\n')
 odb.write_db(dd,str(OUT/'candidate-partially-routed.odb'))
 (OUT/'audit.json').write_text(json.dumps(dict(accepted=False,new_buffers=21,instances=len(new),all_original_geometry_preserved=True,original_functional_connections_recovered_after_identity_buffer_collapse=True,wrong_connection_control_rejected=True,power_geometry_ports_preserved=True,diode_connections_preserved=False,diode_connections_recovered_after_buffer_collapse=True,moved_diode_count=44,requires_routing_antenna_rc_and_all_corner_timing=True),indent=2)+'\n')
else:raise ValueError(mode)
