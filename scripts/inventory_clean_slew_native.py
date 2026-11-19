import os,json,hashlib
from pathlib import Path
import odb
p=Path(os.environ['NSSOC_INVENTORY_ODB']);h=hashlib.sha256(p.read_bytes()).hexdigest();d=odb.dbDatabase.create();odb.read_db(d,str(p));b=d.getChip().getBlock();assert len(list(b.getInsts()))==106650
r=dict(source_odb_sha256=h,instances=106650,targets={},masters={})
for name in ['nssoc_sta_i_55577','nssoc_sta_i_54413','nssoc_sta_i_57921']:
 i=b.findInst(name);assert i
 terminals=[]
 for t in i.getITerms():
  n=t.getNet();assert n
  terminals.append(dict(pin=t.getMTerm().getName(),direction=str(t.getIoType()),type=str(t.getSigType()),net=n.getName(),connections=[dict(instance=x.getInst().getName(),master=x.getInst().getMaster().getName(),pin=x.getMTerm().getName(),direction=str(x.getIoType()),location=list(x.getInst().getLocation()))for x in n.getITerms()]if str(t.getSigType())not in ['POWER','GROUND']else []))
 r['targets'][name]=dict(master=i.getMaster().getName(),location=list(i.getLocation()),orient=str(i.getOrient()),terminals=terminals)
for name in ['sg13g2_nor4_1','sg13g2_nor4_2','sg13g2_nor3_1','sg13g2_nor3_2','sg13g2_buf_1','sg13g2_buf_2','sg13g2_buf_4','sg13g2_buf_8','sg13g2_buf_16']:
 m=d.findMaster(name)
 r['masters'][name]=None if m is None else dict(width=m.getWidth(),height=m.getHeight(),pins=[dict(name=t.getName(),direction=str(t.getIoType()),type=str(t.getSigType()))for t in m.getMTerms()])
assert hashlib.sha256(p.read_bytes()).hexdigest()==h;r['source_unchanged']=True
Path(os.environ['NSSOC_INVENTORY_REPORT']).write_text(json.dumps(r,indent=2)+'\n')
