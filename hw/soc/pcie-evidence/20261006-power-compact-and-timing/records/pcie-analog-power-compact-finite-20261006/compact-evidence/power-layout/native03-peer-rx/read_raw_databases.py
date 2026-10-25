# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Read saved KLayout comparison databases only; never extract/compare geometry."""
from pathlib import Path
import hashlib,json
import klayout.db as db
D=Path('/dev/shm/nssoc-div4-v7-power-v2-checks-02');B=Path(__file__).resolve().parent

def pin(p):
 with p.open('rb') as f:return dict(bytes=p.stat().st_size,sha256=hashlib.file_digest(f,'sha256').hexdigest())
rows=[]
for path in sorted(D.glob('*/result.lvsdb')):
 before=pin(path);saved=db.LayoutVsSchematic();saved.read(str(path));xref=saved.xref();assert xref is not None
 pairs=[]
 for p in xref.each_circuit_pair():
  a,z=p.first(),p.second();assert a is not None and z is not None
  assert list(a.each_subcircuit())==[] and list(z.each_subcircuit())==[]
  pairs.append(dict(layout=a.name,schematic=z.name,status=str(p.status()),layout_devices=sum(1 for _ in a.each_device()),schematic_devices=sum(1 for _ in z.each_device())))
 diagnostics=[dict(severity=str(x.severity),category=x.category_name,cell=x.cell_name,net=x.net_name,message=x.message) for x in saved.each_log_entry()]
 assert pin(path)==before;rows.append(dict(name=path.parent.name,input=dict(path=str(path),**before),pairs=pairs,extraction_diagnostics=diagnostics))
assert len(rows)==16
p=B/'raw-database-read.json';assert not p.exists();p.write_text(json.dumps(dict(status='READ_ONLY_SAVED_NATIVE_DATABASE_CENSUS',method=pin(Path(__file__)),databases=rows,geometry_extraction_or_comparison_executed=False),indent=2)+'\n')
print('READ_ONLY_SAVED_16_DATABASES_COMPLETE')
