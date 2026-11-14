# SPDX-License-Identifier: Apache-2.0
"""Cloud-only inspection of failed leaf open control; not an LVS acceptance."""
import pathlib,hashlib,zipfile,tarfile,io,json,re
import klayout.db as db
def field(o,n):
 v=getattr(o,n);return v() if callable(v) else v
b=pathlib.Path('native.zip').read_bytes();assert hashlib.sha256(b).hexdigest()=='10383d47cb01e321e8fd479f5aa46387fd42847266475a89270e0013a729cb35'
z=zipfile.ZipFile(io.BytesIO(b));names=[n for n in z.namelist() if n.endswith('.tgz')];assert len(names)==1
rows=[]
with tarfile.open(fileobj=io.BytesIO(z.read(names[0])),mode='r:gz') as t:
 for label in ['mapped-original','mapped-open']:
  prefix='native/control-'+label+'/'
  raw=t.extractfile(prefix+'lvs.lvsdb').read();pathlib.Path('leaf.lvsdb').write_bytes(raw)
  ref=t.extractfile(prefix+'reference.cdl').read().decode()
  ports=[line.split()[2:] for line in ref.splitlines() if line.lower().startswith('.subckt')]
  resistors=[line.split() for line in ref.splitlines() if re.search(r'(?i)\blvsres\b',line)]
  assert len(ports)==1 and len(resistors)==1
  resistor=resistors[0];nodes=resistor[1:3]
  usages={n:sum(n in line.split()[1:] for line in ref.splitlines() if line and not line.startswith(('.', '*'))) for n in nodes}
  lvs=db.LayoutVsSchematic();lvs.read('leaf.lvsdb');pairs=[]
  for pair in lvs.xref().each_circuit_pair():
   row={'status':str(pair.status())}
   for side,c in [('layout',pair.first()),('reference',pair.second())]:
    row[side]={'name':c.name,'pins':[{'id':field(p,'id'),'name':field(p,'name')} for p in c.each_pin()]}
   row['net_pairs']=[{'status':str(p.status()),'layout':field(p.first(),'name') if p.first() else None,'reference':field(p.second(),'name') if p.second() else None} for p in lvs.xref().each_net_pair(pair)]
   pairs.append(row)
  rows.append({'label':label,'database_sha256':hashlib.sha256(raw).hexdigest(),'reference_ports':ports[0],'resistor_terminal_nodes':nodes,'resistor_node_device_usage_counts':usages,'circuits':pairs})
r={'scope':'DIAGNOSTIC ONLY: why a port-disconnected negative control can retain an isomorphic device graph. No LVS criteria changed.','controls':rows,'production_accepted':False}
pathlib.Path('out').mkdir();pathlib.Path('out/open-control-pins.json').write_text(json.dumps(r,indent=2))
