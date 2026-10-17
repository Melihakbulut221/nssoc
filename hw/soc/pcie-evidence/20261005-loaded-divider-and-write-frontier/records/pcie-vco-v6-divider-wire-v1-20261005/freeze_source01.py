# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
import ast,hashlib,json,sys
from pathlib import Path
R=Path.cwd();B=Path(__file__).resolve().parent
sys.path.insert(0,str(R/'scripts'))
import characterize_pcie_vco_v6_divider_wire_v1 as m
pin=lambda p:{'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
products=[R/'scripts/build_pcie_clock_div4_v7_hybrid_v1.py',R/'scripts/characterize_pcie_vco_v6_divider_wire_v1.py',m.CHAIN,R/'sw/tests/test_pcie_vco_v6_divider_wire_v1.py',*[p for p in m.DIVIDER.rglob('*') if p.is_file()]]
paths=set(products)
for module in list(sys.modules.values()):
    raw=getattr(module,'__file__',None)
    if raw and Path(raw).is_relative_to(R/'scripts') and raw.endswith('.py'):paths.add(Path(raw))
for bias,fault in [(.6,''),(.85,''),(.6,'disconnect_divider_clock'),(.6,'wrong_feedback_modulus')]:
    c,rows,texts=m.config(bias,fault)
    paths.update(Path(p) for p in c['sources'])
    assert len(rows)==455
    (B/('recipe-'+str(bias)+'-'+(fault or 'nominal')+'.json')).write_text(json.dumps({'config':c,'devices':rows,'vector_count':len(m.n.vectors(rows,c['extra_vectors'])),'included_texts':{name:{'bytes':len(text.encode()),'sha256':hashlib.sha256(text.encode()).hexdigest()} for name,text in texts.items()}} ,indent=2)+'\n')
paths.update(m.n.MODELS.glob('*.lib'));paths.update(m.n.OSDI);paths.add(m.n.NG)
paths.update(p for p in B.rglob('*') if p.is_file() and p.name not in ('source-freeze.json',) and p.suffix not in ('.pyc',) and '__pycache__' not in p.parts)
paths.update(m.core.HYBRID/x for x in m.core.PINS)
record={'status':'FROZEN_SOURCE_ONLY_455_DEVICE_ACTUAL_VCO_DIVIDER_WIRE_MODEL','new_sources':{str(p.relative_to(R)):pin(p) for p in products},'pins':{str(p.resolve()):pin(p) for p in sorted(paths)},'controls':{'passed':25,'failed_attempt01_retained':2,'final_log':pin(B/'source-controls02.log')},'predeclared':{'vctrl':.6,'stop_s':34e-9,'step_s':5e-12,'window_s':[4e-9,34e-9],'intrinsics':455,'HBT':64,'finite_contacts':31,'vectors':956,'wire_R':1201,'wire_C':1383,'CPU':10,'AS':2*1024**3,'own_limit':80*1024**2,'floor':512*1024**2,'elapsed_watchdog':None},'source_peer_required_before_native':True,'qualified_PEX':False}
(B/'source-freeze.json').write_text(json.dumps(record,indent=2)+'\n');print(len(paths),'inputs',len(products),'new sources',pin(B/'source-freeze.json'))
