#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Read failed native GDS/LEF and prove exact database-unit agreement."""
import json,re,sys,pya
from pathlib import Path
from decimal import Decimal
p=Path(sys.argv[1]);name='nssoc_cdr_pd500_active_input_v57'
L=pya.Layout();L.read(str(p/'layout'/(name+'.gds')));T=L.cell(name)
text=(p/'layout'/(name+'.lef')).read_text();size=re.findall(r'SIZE ([\d.]+) BY ([\d.]+) ;',text)
assert len(size)==1
native=[T.dbbox().width(),T.dbbox().height()];printed=list(map(float,size[0]))
grid=[Decimal(x)/Decimal(str(L.dbu))for x in size[0]]
assert all(v==v.to_integral_value()for v in grid)
assert list(map(int,grid))==[T.bbox().width(),T.bbox().height()]
assert printed!=native
d=dict(status='PASS_EXACT_INTEGER_GRID_EQUALITY_WITH_BINARY_FLOAT_COUNTEREXAMPLE',native_double=native,printed_double=printed,native_integer=[T.bbox().width(),T.bbox().height()],lef_exact_grid=[str(v)for v in grid],dbu=L.dbu,tolerance=0,geometry_changed=False)
(p/'readback.json').write_text(json.dumps(d,indent=2))
