# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
from pathlib import Path
import ast,difflib,hashlib,json
R=Path.cwd();B=Path(__file__).resolve().parent
P=R/'hw/soc/out/pcie-vco-v6-divider-tail115-v1-sixteenthstep-20261006/characterize_sixteenthstep01.py'
BASE=P.read_text();TREE=ast.parse(BASE)
def section(name):
 n=next(x for x in TREE.body if isinstance(x,(ast.FunctionDef,ast.ClassDef))and x.name==name)
 return ast.get_source_segment(BASE,n)+'\n'
def pin(p):return dict(bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest())
text=(B/'driver_custom03.py').read_text();bridges=[]
meter=section('Meter');new=meter.replace('Frozen424 device screens','Frozen539 non-contact device screens').replace('== 455','== 570')
old='        super().push(block)';assert new.count(old)==1
new=new.replace(old,'        require(self.count + len(block) <= MAX_ROWS, "Bounded120000 native rows including adaptive extras")\n'+old)
text+='\n\n'+new;bridges.append(dict(name='Meter',before=meter,after=new))
for name in ['deck','run_native','run']:
 before=section(name);after=before
 if name=='deck':after=after.replace('Actual455-device VCOv6 and divider wire RC loaded /80 prototype','Clamped570 full-device PFD-idle tuning diagnostic; not a connected-loop run')
 if name=='deck':
  old_save='        "save " + " ".join(n.vectors(rows, c["extra_vectors"])), '
  old_save=old_save.rstrip()
  assert after.count(old_save)==1
  after=after.replace(old_save,'        *batch.commands(n.vectors(rows, c["extra_vectors"])),')
 if name=='run':
  after=after.replace('not out.exists() and out.resolve().is_relative_to("/dev/shm")','not out.exists() and out.parent == NATIVE_ROOT and not out.is_symlink()').replace('"Fresh RAM output"','"Fresh SSD point output"')
  after=after.replace('    out.mkdir()','    NATIVE_ROOT.mkdir(exist_ok=True)\n    out.mkdir()')
  after=after.replace('"Finite27C loaded /80 with actual VCO and divider metal RC; explicit ideal body boundaries, no substrate spreading, device-wire coupling, RF/PVT, PLL lock, BER or foundry qualification."','"Finite27C clamped570/PFD-idle tuning only;1133 saved vectors,120000-row hard bound, SSD1280MiB perpoint/4GiB aggregate with failures retained; no polarity, pump reachability, lock, PVT or fullPHY qualification."')
  after=after.replace('PASS_NATIVE_LOADED_FEEDBACK_SCREEN','PASS_NATIVE_CLAMPED570_TUNING_POINT').replace('FAIL_NATIVE_LOADED_FEEDBACK_SCREEN','FAIL_NATIVE_CLAMPED570_TUNING_POINT')
 text+='\n\n'+after;bridges.append(dict(name=name,before=before,after=after))
text+='\n\n'+(B/'capture_custom03.py').read_text()
text+='\n\nOWN_LIMIT=AGGREGATE_LIMIT\nnative_limit=previous.native_limit\n'
# Full inherited native owner function has no body delta; supporting globals
# are explicit in this new module, rather than mutated in the frozen parent.
text+='''
if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('--vctrl',type=float,choices=POINTS,required=True);a=ap.parse_args()
 out=NATIVE_ROOT/f'v{int(round(a.vctrl*100)):03d}-01'
 result=run(out,a.vctrl)
 print(result['status'])
 raise SystemExit(0 if result['status']=='PASS_NATIVE_CLAMPED570_TUNING_POINT'else 1)
'''
ast.parse(text)
out=B/'characterize_clamped570_03.py';assert not out.exists();out.write_text(text)
r=dict(parent=str(P),parent_pin=pin(P),custom_sources={str(B/n):pin(B/n)for n in ['driver_custom03.py','capture_custom03.py']},output=pin(out),functions=[dict(x,full_diff=''.join(difflib.unified_diff(x['before'].splitlines(True),x['after'].splitlines(True))))for x in bridges],scope='Complete copied N16 Meter/deck/run_native/run bodies and explicit new configuration/storage/measurement/capture. No native executed. All570 predicates pending actual controls and independent review.')
(B/'driver-source-bridge03.json').write_text(json.dumps(r,indent=2)+'\n');print(pin(out))
