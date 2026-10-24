# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Separately version geometry readers for the completed standalone divider."""
from pathlib import Path
import difflib
import hashlib
import json

B = Path(__file__).resolve().parent
OLD = B.parent / 'pcie-vco-v6-local-v1-wire-20261005'
OLDG = '/dev/shm/nssoc-vco-v4-mim-v6-local-v1-layout-01'
NEWG = '/dev/shm/nssoc-div4-v7-layout-01'
OLDW = '/dev/shm/nssoc-vco-v4-mim-v6-local-v1-wire-geometry-01'
NEWW = '/dev/shm/nssoc-div4-v7-wire-geometry-01'
OLDC = '/dev/shm/nssoc-vco-v4-mim-v6-local-v1-final-check-01'
NEWC = '/dev/shm/nssoc-div4-v7-checks-02'
bridges = []


def pin(path):
    with Path(path).open('rb') as stream:
        return dict(bytes=Path(path).stat().st_size, sha256=hashlib.file_digest(stream, 'sha256').hexdigest())


def replace(text, old, new):
    assert text.count(old) == 1, repr(old)
    return text.replace(old, new)


def common(text):
    return text.replace(OLDG, NEWG).replace(OLDW, NEWW).replace(OLDC, NEWC).replace('nssoc_clock_vco_hbt_v6_local_v1_layout.gds', 'nssoc_clock_div4_v7_layout.gds')


def save(name, text):
    before = (OLD / name).read_text()
    after = B / name
    assert not after.exists()
    after.write_text(text)
    a, z = before.splitlines(True), text.splitlines(True)
    ops = [dict(tag=tag, before=''.join(a[i:j]), after=''.join(z[k:l]))
           for tag, i, j, k, l in difflib.SequenceMatcher(None, a, z, autojunk=False).get_opcodes()]
    assert ''.join(x['before'] for x in ops) == before
    assert ''.join(x['after'] for x in ops) == text
    bridges.append(dict(before=dict(path=str(OLD / name), **pin(OLD / name)),
                        after=dict(path=str(after), **pin(after)), opcodes=ops))


text = common((OLD / 'probe_native_cells.py').read_text())
text = replace(text, "print('COUNT',len(rows),Counter(r['cell'].split('$')[0] for r in rows))",
               "assert len(rows)==91\nassert Counter(r['cell'].split('$')[0] for r in rows)==dict(npn13G2=34,rppd=33,cmim=6,ptap1=18)\nprint('COUNT',len(rows),Counter(r['cell'].split('$')[0] for r in rows))")
save('probe_native_cells.py', text)

text = common((OLD / 'probe_device_locations.py').read_text())
text = replace(text, "models=dict(npn13G2='npn13G2',rppd='rppd',rsil='rsil',pmosHV='sg13_hv_pmos',cmim='cap_cmim',ptap1='ptap1',ntap1='ntap1',diodevdd_2kv='diodevdd_2kv',diodevss_2kv='diodevss_2kv')", "models=dict(npn13G2='npn13G2',rppd='rppd',cmim='cap_cmim',ptap1='ptap1')")
text = replace(text, 'assert len(leaves)==62', 'assert len(leaves)==len(source)==91')
text = replace(text, 'body={("npn13G2","S"),("sg13_hv_pmos","B"),("rppd","rppd_sub"),("ptap1","WELL"),("ntap1","WELL")}', 'body={("npn13G2","S"),("rppd","rppd_sub"),("ptap1","WELL")}')
text = text.replace('len(used)==len(leaves)==62', 'len(used)==len(leaves)==91').replace('ALL_62_NATIVE', 'ALL_91_NATIVE')
text = replace(text, 'for d in c.each_device():', "assert Counter(d.device_class().name for d in c.each_device())==dict(npn13G2=34,rppd=33,cap_cmim=6,ptap1=18)\nfor d in c.each_device():")
save('probe_device_locations.py', text)

text = common((OLD / 'probe_wire_components.py').read_text())
text = text.replace('assert c.pin_count()==6', 'assert c.pin_count()==7')
text = replace(text, 'assert classes==dict(npn13G2=30,ptap1=12,ntap1=1,rppd=9,cap_cmim=6,sg13_hv_pmos=4),classes', 'assert classes==dict(npn13G2=34,ptap1=18,rppd=33,cap_cmim=6),classes')
text = replace(text, 'r=pya.Region(top.begin_shapes_rec(g.layer(layer,0))).merged();assert not r.is_empty();regions[layer]=r', 'r=pya.Region(top.begin_shapes_rec(g.layer(layer,0))).merged();regions[layer]=r')
text = replace(text, 'layers[layer]=dict(area_dbu2=r.area()', 'layers[layer]=dict(explicitly_empty=r.is_empty(),area_dbu2=r.area()')
text = replace(text, 'for metal in METALS:\n r=regions[metal];a=r.area();box=r.bbox();candidates=[]', '# Empty layers remain explicitly inventoried; no nonempty polygon is omitted.\nACTIVE_METALS=[m for m in METALS if not regions[m].is_empty()]\nassert ACTIVE_METALS==[8,10,30,50,67,126]\nassert regions[134].is_empty() and regions[133].is_empty()\nfor metal in ACTIVE_METALS:\n r=regions[metal];a=r.area();box=r.bbox();candidates=[]')
text = replace(text, "for layer,r in regions.items():e.register(r,'gds_'+str(layer));e.connect(r)\nfor a,v,b in zip(METALS,VIAS,METALS[1:]):e.connect(regions[a],regions[v]);e.connect(regions[v],regions[b])", "for layer,r in regions.items():\n if not r.is_empty():e.register(r,'gds_'+str(layer));e.connect(r)\nfor a,v,b in zip(METALS,VIAS,METALS[1:]):\n if not regions[v].is_empty():\n  assert not regions[a].is_empty() and not regions[b].is_empty()\n  e.connect(regions[a],regions[v]);e.connect(regions[v],regions[b])")
text = text.replace('for m in METALS}', 'for m in ACTIVE_METALS}').replace('for m in METALS)', 'for m in ACTIVE_METALS)')
text = replace(text, "wire.write(str(OUT/'wires.gds'));e.write(str(OUT/'wires.l2n'))", "assert len(rows)==37 and len(coverage)==38\nwire.write(str(OUT/'wires.gds'));e.write(str(OUT/'wires.l2n'))")
save('probe_wire_components.py', text)

text = common((OLD / 'probe_terminal_anchors.py').read_text())
text = replace(text, "body={('npn13G2','S'),('sg13_hv_pmos','B'),('rsil','rsil_sub'),('rppd','rppd_sub'),('ptap1','WELL'),('ntap1','WELL')}", "body={('npn13G2','S'),('rppd','rppd_sub'),('ptap1','WELL')}")
start = text.index("  elif cls.name=='sg13_hv_pmos' and td.name=='G':")
end = text.index('  else:candidates=pinboxes', start)
text = text[:start] + text[end:]
text = text.replace("('npn13G2','cmim','pmosHV','rsil','rppd','ptap1','ntap1')", "('npn13G2','cmim','rppd','ptap1')")
text = text.replace('native_device_count=62,native_terminal_count=201', 'native_device_count=91,native_terminal_count=283').replace("result['declared_terminal_count']==201", "result['declared_terminal_count']==283")
text = replace(text, "assert result['declared_terminal_count']==283", "assert result['declared_terminal_count']==283\nassert not unresolved\nassert result['dispositions']==dict(ACTUAL_METAL_POINT_REFERENCE=198,UNCHANGED_INTRINSIC_BODY_TERMINAL_NO_ADDED_SUBSTRATE_R=85)")
save('probe_terminal_anchors.py', text)

text = common((OLD / 'prepare_anchors.py').read_text())
text = text.replace('219a6006e89266f05430a469d3a90279b1f287e2a57125d1a6642173dfc21f84', '8484a6f3db8e91923ec6e5d2184bf6ba80570b2c894b5e4f563b637e0165ee3f')
text = text.replace('len(components)==20', 'len(components)==37').replace('len(anchors)==151 and len(body)==56', 'len(anchors)==205 and len(body)==85')
text = text.replace('source_native_device_count=62,source_public_ports=6,source_wire_components=20', 'source_native_device_count=91,source_public_ports=7,source_wire_components=37').replace('actual_metal_terminals=145,body_well_terminals=56', 'actual_metal_terminals=198,body_well_terminals=85')
save('prepare_anchors.py', text)

text = common((OLD / 'bind_source_ids.py').read_text())
text = replace(text, 'from collections import defaultdict', 'from collections import defaultdict\nimport math')
text = replace(text, "kind={'npn13G2':'hbt','rppd':'resistor','sg13_hv_pmos':'pmos','cap_cmim':'capacitor','ptap1':'substrate_tap','ntap1':'well_tap'}", "kind={'npn13G2':'hbt','rppd':'resistor','cap_cmim':'capacitor','ptap1':'substrate_tap'}")
text = replace(text, "order={'npn13G2':['C','B','E','S'],'rppd':['rppd_1','rppd_2','rppd_sub'],'sg13_hv_pmos':['D','G','S','B'],'cap_cmim':['mim_top','mim_btm'],'ptap1':['TIE','WELL'],'ntap1':['TIE','WELL']}[d['model']]", "order={'npn13G2':['C','B','E','S'],'rppd':['rppd_1','rppd_2','rppd_sub'],'cap_cmim':['mim_top','mim_btm'],'ptap1':['TIE','WELL']}[d['model']]")
text = replace(text, " if d['model']=='sg13_hv_pmos':nets[-1]='NWELL'\n", '')
text = replace(text, ' assert len(nets)==len(order)', " assert len(nets)==len(order)\n assert set(actual)==set(order)\n if d['model']=='npn13G2':expected=dict(we=.07,le=.9,Nx=source['nx'],m=1)\n elif d['model']=='rppd':expected=dict(w=source['width_um'],l=source['length_um'],ps=0,b=0,m=1)\n elif d['model']=='cap_cmim':\n  w,h=source['width_um'],source['length_um'];expected=dict(w=w,l=h,A=w*h,P=2*(w+h),m=1)\n else:expected=dict(A=source['area_um2'],P=source['perimeter_um'])\n assert set(d['parameters'])==set(expected)\n assert all(math.isclose(d['parameters'][k],v,rel_tol=1e-12,abs_tol=1e-12) for k,v in expected.items()),(d['native_id'],d['parameters'],expected)")
text = text.replace('len(rows)==len(used)==62', 'len(rows)==len(used)==len(g[\'instances\'])==91').replace('len(net_map)==len(reverse)==22', 'len(net_map)==len(reverse)==38').replace('PASS_FULL62_DEVICE', 'PASS_FULL91_DEVICE')
text = replace(text, " source_body_and_well_distinct=net_map['BULK']!=net_map['NWELL'],inputs=", " source_body_distinct_from_contact=net_map['BULK']!=net_map['SUB'],all18_finite_substrate_contacts_retained=True,no_well_devices_in_source=True,inputs=")
save('bind_source_ids.py', text)

out = B / 'geometry-source-bridge.json'
assert not out.exists()
out.write_text(json.dumps(bridges, indent=2) + '\n')
print(json.dumps(dict(sources=[x['after'] for x in bridges], bridge=pin(out)), indent=2))
