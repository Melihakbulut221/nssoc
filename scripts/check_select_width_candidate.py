import sys,json
from pathlib import Path
sys.path.insert(0,str(Path.cwd()/'hw/soc/flow'))
import check_pcie_cdr_feedforward_v1 as check
layout=Path('hw/soc/out/select-width-rwidth2')
r=json.loads((layout/'result.json').read_text())
assert r['candidate_resistor_width']=='2u' and r['kind']=='select'
assert len(r['core_devices'])==6 and r['substrate_contacts']==6
res=[d for d in r['core_devices'] if d['model']=='rppd']
assert len(res)==4 and all(d['params']['w']=='2u' for d in res)
check.TOP='nssoc_cdr_select_feedforward_layout_v1_rwidth2_candidate'
check.EXPECTED_DEVICES=12
check.KIND='select'
check.run(layout,Path('hw/soc/out/select-width2-native-checks'),Path('hw/soc/tools/physical/librelane-3.0.5-x86_64.AppImage'))
