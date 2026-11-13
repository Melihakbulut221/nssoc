# SPDX-License-Identifier: Apache-2.0
"""Independent full SRAM reference inventory; not layout LVS or RC approval."""
import collections, hashlib, io, json, pathlib, sys, zipfile
sys.path.insert(0, 'hw/soc/flow')
from mos_graph_equivalence import load_mos_netlist
out=pathlib.Path('out');out.mkdir(exist_ok=True)
r={'full_macro_lvs':False,'qualified_pex':False,'manufacturing_approval':False}
try:
 raw=pathlib.Path('reference.zip').read_bytes()
 assert hashlib.sha256(raw).hexdigest()=='124f6a92fa56346b1c471efb84750878180ef0c8056b2c940c5c6fce0e41e29b','archive SHA mismatch'
 z=zipfile.ZipFile(io.BytesIO(raw));names=[n for n in z.namelist() if n.endswith('reference.spice')]
 assert len(names)==1,'ambiguous reference'
 native=z.read(names[0]);digest=hashlib.sha256(native).hexdigest()
 assert digest=='64d041383d0ebee7b54dab0bc10d651d31262a2a41ccd15a9c0727dac06e0dd9','reference SHA mismatch'
 path=pathlib.Path('reference.spice');path.write_bytes(native)
 import klayout.db as db
 n=db.Netlist();n.read(str(path),db.NetlistSpiceReader())
 tops=list(n.each_top_circuit())
 assert len(tops)==1 and tops[0].name.lower()=='dp8tsramdp256x16','wrong or ambiguous top'
 g=load_mos_netlist(path)
 models=collections.Counter(d['model'] for d in g['devices'])
 bulks=collections.Counter(g['pins'].get(d['B'],'INTERNAL') for d in g['devices'])
 dims=collections.Counter((d['model'],d['w'],d['l']) for d in g['devices'])
 assert g['devices'] and len(g['devices'])==sum(models.values()),'empty/inconsistent inventory'
 r.update(status='INDEPENDENT_REFERENCE_INVENTORIED',reference_spice_sha256=digest,top=tops[0].name,mos_count=len(g['devices']),net_count=len(g['nets']),port_names=sorted(g['pins'].values()),models=dict(models),bulk_port_counts=dict(bulks),dimensions=[{'model':m,'w_um':w,'l_um':l,'count':c} for (m,w,l),c in sorted(dims.items())],maximum_float_normalization_um=g['maximum_float_normalization_um'],scope='Hash-locked independent schematic flattened by KLayout 0.30.13. All devices must be MOS4 with positive W/L. No extracted layout is compared, no body aliases are introduced, and no process or full-chip approval is implied.')
except Exception as e:r.update(status='ERROR',error=type(e).__name__+': '+str(e))
(out/'reference-macro-inventory.json').write_text(json.dumps(r,indent=2));print(json.dumps(r));raise SystemExit(0 if r['status']=='INDEPENDENT_REFERENCE_INVENTORIED' else 1)
