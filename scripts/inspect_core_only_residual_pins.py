#!/usr/bin/env python3
"""Read-only transformed terminal geometry for measured electrical residuals."""
import os,json,hashlib
from pathlib import Path
import odb
source=Path(os.environ['NSSOC_INVENTORY_ODB']);out=Path(os.environ['NSSOC_INVENTORY_OUT'])
before=hashlib.sha256(source.read_bytes()).hexdigest();d=odb.dbDatabase.create();odb.read_db(d,str(source));b=d.getChip().getBlock();u=b.getDbUnitsPerMicron()
assert len(list(b.getInsts()))==105245

def rect(r):return [r.xMin()/u,r.yMin()/u,r.xMax()/u,r.yMax()/u]
def terminal(t):
 i=t.getInst();r=t.getBBox();assert r.xMax()>r.xMin() and r.yMax()>r.yMin()
 return dict(instance=i.getName(),pin=t.getMTerm().getName(),master=i.getMaster().getName(),master_type=str(i.getMaster().getType()),io_type=str(t.getIoType()),signal_type=str(t.getSigType()),orientation=str(i.getOrient()),instance_bbox_um=rect(i.getBBox()),pin_bbox_um=rect(r))
targets=['nssoc_sta_i_8470/Y','nssoc_sta_i_10894/X','nssoc_sta_i_78691/Q','u_ram.g_ram_2048x64_ecc.u_b1/A_DOUT[0]'];records=[]
for target in targets:
 name,pin=target.rsplit('/',1);i=b.findInst(name);assert i;t=i.findITerm(pin);assert t and str(t.getIoType())=='OUTPUT';net=t.getNet();assert net
 drivers=[terminal(x)for x in net.getITerms()if str(x.getIoType())=='OUTPUT'];assert len(drivers)==1
 sinks=[terminal(x)for x in net.getITerms()if str(x.getIoType())!='OUTPUT'];assert all(x['io_type']=='INPUT'for x in sinks)
 records.append(dict(driver=terminal(t),net=net.getName(),net_type=str(net.getSigType()),sinks=sinks,bterms=[x.getName()for x in net.getBTerms()]))
iso=b.findInst('nssoc_residualbuf_2_0');assert iso
extra={pin:terminal(iso.findITerm(pin))for pin in ['A','X']}
assert hashlib.sha256(source.read_bytes()).hexdigest()==before
(out/'pin-inventory.json').write_text(json.dumps(dict(source_odb_sha256=before,instances=105245,targets=records,sram_isolation_buffer=extra,read_only=True),indent=2)+'\n')
