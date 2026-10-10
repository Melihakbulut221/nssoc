from pathlib import Path
import sys,json,hashlib
R=Path.cwd();sys.path.insert(0,str(R/'hw/soc/flow'))
import audit_pcie_clock_div4_v9_bias_v1 as a
P=Path('/dev/shm/nssoc-div4-v8-cap-v1-layout-01');g=P/'nssoc_clock_div4_v8_cap_v1_layout.gds';r=P/'result.json'
assert a.pin(g)['sha256']==a.BASE_GDS_SHA and a.pin(r)['sha256']==a.BASE_RESULT_SHA
metadata=json.loads(r.read_text());layout,instances=a.parent.top_instances(g,a.OLD_TOP)
selected,vias=a.primitive_matches(instances,metadata['instances'],metadata['origin_translation_um'],layout.dbu)
tp=Path('/home/hasanmelih/.ciel/ciel/ihp-sg13g2/versions/c4b8b4e5e7a05f375cca3815d51b3a37721fbf5c/ihp-sg13g2/libs.tech/klayout/python/sg13g2_pycell_lib/sg13g2_tech.json');tech=json.loads(tp.read_text())['techParams']
result={}
for name in sorted(a.PULLDOWNS):
 actual=selected[name]['geometry'];expect=a.rppd_template(1,7,tech,layout.dbu)
 row={str(k):dict(actual=actual.get(k,a.pya.Region()).to_s(),expected=expect.get(k,a.pya.Region()).to_s(),difference=(actual.get(k,a.pya.Region())^expect.get(k,a.pya.Region())).to_s())for k in sorted(set(actual)|set(expect))};result[name]=row
 print(name,json.dumps(row),flush=True)
 assert a.geometry_key(actual)==a.geometry_key(expect)
 assert a.geometry_key(actual)!=a.geometry_key(a.rppd_template(1,8,tech,layout.dbu))
print(json.dumps(dict(status='PASS_SAVED_NATIVE_L7_RPPD_EXACT_INDEPENDENT_RECTANGLES',inputs={str(p):a.pin(p) for p in [g,r,tp,Path(a.__file__),Path(__file__)]},dbu=layout.dbu,geometry=result,scope='Saved original GDS only; no new PCell generation/DRC/LVS or claim of V9 native geometry.')))
