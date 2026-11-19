"""Read-only native inventory of every remaining electrical violation pin."""
import os,json,hashlib
from pathlib import Path
import odb
p=Path(os.environ['NSSOC_INVENTORY_ODB']);h=hashlib.sha256(p.read_bytes()).hexdigest()
assert h=='12a48d839091ba5c4fea76a193fea75fcc5f2f38621b1df809cb3df5bd51e458'
d=odb.dbDatabase.create();odb.read_db(d,str(p));b=d.getChip().getBlock();assert len(list(b.getInsts()))==106693
pins=json.loads(Path(os.environ['NSSOC_INVENTORY_PINS']).read_text());assert pins
r=dict(source_odb_sha256=h,instances=106693,pins={},nets={},masters={})
def terminal(t):
    i=t.getInst()
    return dict(instance=i.getName(),master=i.getMaster().getName(),pin=t.getMTerm().getName(),direction=str(t.getIoType()),type=str(t.getSigType()),location=list(i.getLocation()),orient=str(i.getOrient()))
for name,evidence in sorted(pins.items()):
    inst,pin=name.rsplit('/',1);i=b.findInst(inst);assert i,name
    matches=[t for t in i.getITerms() if t.getMTerm().getName()==pin];assert len(matches)==1,name
    t=matches[0];n=t.getNet();assert n and str(t.getSigType())not in ['POWER','GROUND'],name
    r['pins'][name]=dict(net=n.getName(),terminal=terminal(t),violations=evidence)
    if n.getName() not in r['nets']:
        terms=[terminal(x) for x in n.getITerms()]
        r['nets'][n.getName()]=dict(signal_type=str(n.getSigType()),terminals=terms,drivers=[x for x in terms if x['direction']in ['OUTPUT','INOUT']],loads=[x for x in terms if x['direction']=='INPUT'],ports=[dict(name=x.getName(),direction=str(x.getIoType()))for x in n.getBTerms()])
names={'sg13g2_buf_'+str(s)for s in [1,2,4,8,16]}
for net in r['nets'].values():
    for t in net['drivers']:
        stem=t['master'].rsplit('_',1)[0];names.update(stem+'_'+str(s)for s in [1,2,4,8,16])
for name in sorted(names):
    m=d.findMaster(name)
    r['masters'][name]=None if m is None else dict(width=m.getWidth(),height=m.getHeight(),pins=[dict(name=t.getName(),direction=str(t.getIoType()),type=str(t.getSigType()))for t in m.getMTerms()])
assert set(r['pins'])==set(pins)
assert hashlib.sha256(p.read_bytes()).hexdigest()==h;r['source_unchanged']=True
Path(os.environ['NSSOC_INVENTORY_REPORT']).write_text(json.dumps(r,indent=2)+'\n')
