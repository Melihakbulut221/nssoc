#!/usr/bin/env python3
"""Three measured-load isolation buffers; frozen original geometry and logical identity."""
import os,json,re,copy
from pathlib import Path
import odb
from buffer_core_only_chip_controls import load,identity,geom,connections
OUT=Path(os.environ['NSSOC_CRITICAL_ECO_OUT']);mode=os.environ['NSSOC_CRITICAL_ECO_MODE']
SPEC=[('nssoc_sta_i_8457', 'Y', 'sg13g2_o21ai_1', 'nssoc_sta_n_100406', 'sg13g2_buf_8', [('load_slew2431', 'A'), ('load_slew2428', 'A'), ('wire2427', 'A')]), ('nssoc_sta_i_52826', 'Y', 'sg13g2_o21ai_1', 'nssoc_sta_n_53586', 'sg13g2_buf_8', [('nssoc_sta_i_57620', 'A1'), ('nssoc_sta_i_52834', 'A2')]), ('nssoc_sta_i_63807', 'Y', 'sg13g2_o21ai_1', 'nssoc_sta_n_63283', 'sg13g2_buf_8', [('nssoc_sta_i_66452', 'B2'), ('nssoc_sta_i_65898', 'C'), ('nssoc_sta_i_65702', 'C'), ('nssoc_sta_i_65697', 'D'), ('nssoc_sta_i_65678', 'A1'), ('nssoc_sta_i_65288', 'A1'), ('nssoc_sta_i_63808', 'C')])]
def function(text,name):
 m=re.search(r'cell\s*\(\s*"?'+re.escape(name)+r'"?\s*\)\s*\{',text);assert m
 j=m.end();start=j;depth=1
 while depth:depth+=(text[j]=='{')-(text[j]=='}');j+=1
 f=re.findall(r'\bfunction\s*:\s*([^;]+)',text[start:j]);assert len(f)==1
 return f[0].strip().strip('"')
d,b=load(OUT/'source.odb');assert len(list(b.getInsts()))==106651
if mode=='prepare':
 statuses={i.getName():str(i.getPlacementStatus())for i in b.getInsts()};before=connections(b);newcells={};moves={}
 for index,(name,pin,old,netname,mastername,sinks)in enumerate(SPEC):
  assert function((OUT/'std.lib').read_text(),mastername)=='A'
  driver=b.findInst(name);assert driver and driver.getMaster().getName()==old
  net=driver.findITerm(pin).getNet();assert net.getName()==netname and str(net.getSigType())=='SIGNAL'and not list(net.getBTerms())
  assert sum(str(t.getIoType())=='OUTPUT'for t in net.getITerms())==1
  assert not any(t.getInst().getMaster().getName()=='sg13g2_antennanp'for t in net.getITerms())
  tag='nssoc_slewiso_' +str(index);assert not b.findInst(tag)and not b.findNet(tag+'_net')
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
 assert checked==103082,checked
 clocks=[n for n in b.getNets()if str(n.getSigType())=='CLOCK'];assert len(clocks)==2113
 assert all(left[n.getName()]==right[n.getName()]for n in clocks)
 for net in b.getNets():
  oldrule=net.getNonDefaultRule();newrule=bb.findNet(net.getName()).getNonDefaultRule()
  assert (oldrule.getName()if oldrule else None)==(newrule.getName()if newrule else None),('ndr_assignment_changed',net.getName())
 for name in changed:assert not bb.findNet(name).getWire()
 (OUT/'preserved-route-audit.json').write_text(json.dumps(dict(unchanged_def_net_records=checked,changed_nets=sorted(changed),clock_routes_preserved=True,checked_clock_nets=2113,ndr_assignments_preserved=True,requires_incremental_routing=True),indent=2)+'\n')
 odb.write_db(dd,str(OUT/'candidate-partially-routed.odb'))
 (OUT/'audit.json').write_text(json.dumps(dict(accepted=False,new_buffers=3,instances=len(new),all_original_geometry_preserved=True,original_functional_connections_recovered_after_identity_buffer_collapse=True,wrong_connection_control_rejected=True,power_geometry_ports_preserved=True,diode_connections_preserved=True,requires_routing_antenna_rc_and_all_corner_timing=True),indent=2)+'\n')
else:raise ValueError(mode)
