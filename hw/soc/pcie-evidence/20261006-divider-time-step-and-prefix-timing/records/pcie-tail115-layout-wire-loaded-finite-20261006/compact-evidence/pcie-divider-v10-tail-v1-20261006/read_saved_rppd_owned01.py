from pathlib import Path
import sys,json
R=Path.cwd();sys.path.insert(0,str(R/'hw/soc/flow'))
import check_pcie_clock_div4_v9_bias_v1 as c
B=Path(__file__).resolve().parent;O=B/'saved-rppd01';assert not O.exists();O.mkdir();c.SCRATCH_ROOTS=(O,)
r=c.execute([R/'hw/soc/tools/physical/librelane-3.0.5-x86_64.AppImage','python',B/'inspect_saved_rppd01.py'],O,'read')
(O/'result.json').write_text(json.dumps(r,indent=2)+'\n');print(r)
