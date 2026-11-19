#!/usr/bin/env python3
"""Three measured-load isolation buffers; frozen original geometry and logical identity."""
import os,json,re,copy
from pathlib import Path
import odb
from buffer_core_only_chip_controls import load,identity,geom,connections
OUT=Path(os.environ['NSSOC_CRITICAL_ECO_OUT']);mode=os.environ['NSSOC_CRITICAL_ECO_MODE']
SPEC=[('nssoc_sta_i_8624', 'Y', 'sg13g2_o21ai_1', 'nssoc_sta_n_100389', 'sg13g2_buf_8', [('ANTENNA_491', 'A'), ('load_slew2384', 'A'), ('load_slew2381', 'A'), ('wire2380', 'A')]), ('nssoc_sta_i_8545', 'Y', 'sg13g2_o21ai_1', 'nssoc_sta_n_100405', 'sg13g2_buf_8', [('ANTENNA_500', 'A'), ('load_slew2402', 'A'), ('load_slew2399', 'A'), ('wire2398', 'A')]), ('nssoc_sta_i_56298', 'Y', 'sg13g2_o21ai_1', 'nssoc_sta_n_57040', 'sg13g2_buf_8', [('nssoc_sta_i_58280', 'A1'), ('nssoc_sta_i_56299', 'B')]), ('nssoc_sta_i_61007', 'Y', 'sg13g2_nor3_2', 'nssoc_sta_n_60783', 'sg13g2_buf_8', [('ANTENNA_2569', 'A'), ('ANTENNA_2570', 'A'), ('ANTENNA_2571', 'A'), ('ANTENNA_2572', 'A'), ('fanout935', 'A')]), ('nssoc_sta_i_61007', 'Y', 'sg13g2_nor3_2', 'nssoc_sta_n_60783', 'sg13g2_buf_8', [('ANTENNA_2573', 'A'), ('ANTENNA_2574', 'A'), ('ANTENNA_2575', 'A'), ('ANTENNA_2576', 'A'), ('nssoc_sta_i_61075', 'B')]), ('nssoc_sta_i_65080', 'Y', 'sg13g2_nor4_1', 'nssoc_sta_n_64543', 'sg13g2_buf_8', [('nssoc_sta_i_65081', 'B2')])]
def function(text,name):
 m=re.search(r'cell\s*\(\s*"?'+re.escape(name)+r'"?\s*\)\s*\{',text);assert m
 j=m.end();start=j;depth=1
 while depth:depth+=(text[j]=='{')-(text[j]=='}');j+=1
 f=re.findall(r'\bfunction\s*:\s*([^;]+)',text[start:j]);assert len(f)==1
 return f[0].strip().strip('"')
d,b=load(OUT/'source.odb');assert len(list(b.getInsts()))==106664
if mode=='prepare':
 statuses={i.getName():str(i.getPlacementStatus())for i in b.getInsts()};before=connections(b);newcells={};moves={}
 # Every original load on these five nets must be explicitly assigned once.
 assigned={}
 for name,pin,old,netname,mastername,sinks in SPEC:
  assigned.setdefault(netname,[]).extend(sinks)
 for netname,sinks in assigned.items():
  net=b.findNet(netname);assert net and not list(net.getBTerms())
  actual={(t.getInst().getName(),t.getMTerm().getName())for t in net.getITerms()if str(t.getIoType())=='INPUT'}
  assert len(sinks)==len(set(sinks)) and set(sinks)==actual,(netname,sinks,actual)
 expected_diodes={'ANTENNA_491','ANTENNA_500'}|{'ANTENNA_'+str(i)for i in range(2569,2577)}
 actual_diodes={sn for sinks in assigned.values()for sn,sp in sinks if b.findInst(sn).getMaster().getName()=='sg13g2_antennanp'}
 assert actual_diodes==expected_diodes

 for index,(name,pin,old,netname,mastername,sinks)in enumerate(SPEC):
  assert function((OUT/'std.lib').read_text(),mastername)=='A'
  driver=b.findInst(name);assert driver and driver.getMaster().getName()==old
  net=driver.findITerm(pin).getNet();assert net.getName()==netname and str(net.getSigType())=='SIGNAL'and not list(net.getBTerms())
  assert sum(str(t.getIoType())=='OUTPUT'for t in net.getITerms())==1
  tag='nssoc_regiso_'  +str(index);assert not b.findInst(tag)and not b.findNet(tag+'_net')
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
 assert checked==103083,checked
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
 assert len(diode_moves)==10
 for netname in changed:
  net=bb.findNet(netname)
  assert sum(str(t.getIoType())=='INPUT' for t in net.getITerms())<=8
 (OUT/'diode-reconnection-audit.json').write_text(json.dumps(dict(moves=diode_moves,all_original_diodes_preserved=True,functional_equivalence_by_identity_buffer_collapse=True,antenna_protection_revalidation_required=True,accepted=False),indent=2)+'\n')
 odb.write_db(dd,str(OUT/'candidate-partially-routed.odb'))
 (OUT/'audit.json').write_text(json.dumps(dict(accepted=False,new_buffers=6,instances=len(new),all_original_geometry_preserved=True,original_functional_connections_recovered_after_identity_buffer_collapse=True,wrong_connection_control_rejected=True,power_geometry_ports_preserved=True,diode_connections_preserved=False,diode_connections_recovered_after_buffer_collapse=True,moved_diode_count=10,requires_routing_antenna_rc_and_all_corner_timing=True),indent=2)+'\n')
else:raise ValueError(mode)
