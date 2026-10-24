from pathlib import Path
import json,sys
sys.path.insert(0,'scripts');import run_cloud_npu_write_trace as w
B=Path(__file__).resolve().parent/'evq37187157260';model=Path('/home/hasanmelih/.ciel/ciel/ihp-sg13g2/versions/c4b8b4e5e7a05f375cca3815d51b3a37721fbf5c/ihp-sg13g2/libs.ref/sg13g2_stdcell/verilog/sg13g2_stdcell.v')
lock=dict(schema=1,producer=w.q.PRODUCER,prior=w.PRIOR,bounds=dict(cells=w.MAX_CELLS,signals=w.MAX_SIGNALS,events=w.MAX_EVENTS),cycle_bound=3000000,window=[w.START,w.LAST],variants={})
for v in ('original','candidate'):
 b=w.derive_binding((B/'producer'/('synthesis-'+v)/'soc_top.netlist.v').read_text(),model.read_text(),v);lock['variants'][v]=dict(binding_sha256=w.digest(b),cells=len(b['cells']),signals=len(b['signals']),sequential_boundaries=len(b['sequential_boundary']));print(v,lock['variants'][v]);(B/(v+'-write-binding02.json')).write_text(json.dumps(b,indent=2)+'\n')
Path(w.LOCK).write_text(json.dumps(lock,indent=2)+'\n')
