from pathlib import Path
import sys,json,hashlib
R=Path.cwd();B=Path(__file__).resolve().parent
sys.path.insert(0,str(R/'hw/soc/flow'))
import check_pcie_clock_div4_v7_v2 as checked
assert checked.digest(checked.__file__)=='24c89628c6d61226344214e077b5fa535c5570e4a7853fbd109e8cb1b1fcd163'
checked.SCRATCH_ROOTS=(B,)
app=R/'hw/soc/tools/physical/librelane-3.0.5-x86_64.AppImage';assert checked.digest(app)==checked.APP_SHA
r=checked.execute([app,'python',B/'read_raw_databases.py'],B,'saved-database-reader');assert r['returncode']==0
(B/'reader-execution.json').write_text(json.dumps(r,indent=2)+'\n');print(r)
