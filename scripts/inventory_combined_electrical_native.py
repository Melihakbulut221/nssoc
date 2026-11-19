import os,json,hashlib,re
from pathlib import Path
import odb
p=Path(os.environ['NSSOC_INVENTORY_ODB']);h=hashlib.sha256(p.read_bytes()).hexdigest();d=odb.dbDatabase.create();odb.read_db(d,str(p));b=d.getChip().getBlock();assert len(list(b.getInsts()))==106650
rows=json.loads(Path(os.environ['NSSOC_INVENTORY_VIOLATIONS']).read_text());nets={}
for row in rows:
 pin=row['pin']
 if '/'in pin:
  instance,terminal=pin.rsplit('/',1);i=b.findInst(instance);assert i,instance;t=i.findITerm(terminal);assert t,pin;n=t.getNet()
 else:
  t=b.findBTerm(pin);assert t,pin;n=t.getNet()
 assert n,pin
 nets.setdefault(n.getName(),dict(violations=[]))['violations'].append(row)
for name,entry in nets.items():
 n=b.findNet(name);terms=[]
 for t in n.getITerms():
  i=t.getInst();m=i.getMaster();terms.append(dict(instance=i.getName(),master=m.getName(),pin=t.getMTerm().getName(),direction=str(t.getIoType()),type=str(t.getSigType()),location=list(i.getLocation()),antenna=m.getName()=='sg13g2_diode'))
 drivers=[t for t in terms if t['direction']=='OUTPUT'];loads=[t for t in terms if t['direction']=='INPUT'];diodes=[t for t in loads if t['antenna']]
 entry.update(type=str(n.getSigType()),drivers=drivers,terms=terms,ports=[t.getName()for t in n.getBTerms()],input_loads=len(loads),antenna_loads=len(diodes),functional_input_loads=len(loads)-len(diodes))
 variants={}
 for driver in drivers:
  stem=re.sub(r'_\d+$','',driver['master'])
  for strength in [1,2,4,8,16]:
   master=d.findMaster(stem+'_'+str(strength))
   if master:variants[master.getName()]=dict(width=master.getWidth(),height=master.getHeight(),pins=[dict(name=t.getName(),direction=str(t.getIoType()),type=str(t.getSigType()))for t in master.getMTerms()])
 entry['available_master_variants']=variants
assert hashlib.sha256(p.read_bytes()).hexdigest()==h
Path(os.environ['NSSOC_INVENTORY_REPORT']).write_text(json.dumps(dict(source_odb_sha256=h,source_unchanged=True,instances=106650,violation_rows=len(rows),unique_nets=len(nets),nets=nets,accepted=False),indent=2)+'\n')
