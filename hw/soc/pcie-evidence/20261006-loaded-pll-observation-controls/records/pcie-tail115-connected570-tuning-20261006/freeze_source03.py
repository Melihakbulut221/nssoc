# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Bind the actual bounded native command control and the exact full34ns retry."""
from pathlib import Path
import ast,copy,difflib,hashlib,json,os,sys
B=Path(__file__).resolve().parent;C=B.parent/'pcie-tail115-connected570-save-batches-20261006';R=Path.cwd()
sys.path.insert(0,str(B));sys.path.insert(0,str(C))
import characterize_clamped570_02 as prior
import characterize_clamped570_03 as m
import save_batches03 as batch

def pin(p):
 p=Path(p)
 with p.open('rb')as f:return dict(bytes=p.stat().st_size,sha256=hashlib.file_digest(f,'sha256').hexdigest())
def verify_inventory(d):
 for p,v in d.items():assert pin(p)==v,p

def main():
 assert not(B/'source-freeze03.json').exists()and not m.NATIVE_ROOT.exists()
 assert sys.executable==str(R/'hw/soc/tools/cocotb-venv/bin/python')and os.sched_getaffinity(0)=={10}
 oldfreeze=B/'source-freeze02.json';old=json.loads(oldfreeze.read_text());verify_inventory(old['pins'])
 controlfreeze=C/'source-freeze01.json';cf=json.loads(controlfreeze.read_text());verify_inventory(cf['pins'])
 cp=C/'source-only-peer-root01.json';peer=json.loads(cp.read_text());assert peer['status']=='PASS_SOURCE_ONLY_570_BATCHED_SAVE_NATIVE_CONTROLS'and peer['freeze']==pin(controlfreeze)and peer['findings']==[]
 N=C/'native-control01';control=json.loads((N/'result.json').read_text());assert control['status']=='PASS_BOUNDED_NATIVE570_SAVE_BATCH_COMMAND_AND_OBSERVATION_CONTROLS'and control['cases']==8 and all(x['passed']for x in control['outcomes'])
 verify_inventory(control['inputs'])
 for p,v in control['outputs'].items():assert pin(N/p)==v,p
 owner=json.loads((N/'owner.json').read_text());assert len(owner['processes'])==1
 for p in owner['processes']:
  assert p['status']=='REAPED_NO_LIVE_MEMBERS'and p['returncode']==0 and p['members_at_leader_exit']==[]
  assert not Path('/proc',str(p['identity']['pid'])).exists()
 assert not Path('/proc/414085').exists()and not Path('/proc/414067').exists()
 oldbody=Path(prior.__file__).read_text();newbody=Path(m.__file__).read_text()
 restored=newbody.replace("NATIVE_ROOT=B/'native03'","NATIVE_ROOT=B/'native02'")
 importblock="SAVE_SOURCE=B.parent/'pcie-tail115-connected570-save-batches-20261006'\nsys.path.insert(0,str(SAVE_SOURCE))\nimport save_batches03 as batch\n"
 assert restored.count(importblock)==1;restored=restored.replace(importblock,'')
 fresh='        *batch.commands(n.vectors(rows, c["extra_vectors"])),';oldsave='        "save " + " ".join(n.vectors(rows, c["extra_vectors"])),'
 assert restored.count(fresh)==1;restored=restored.replace(fresh,oldsave);assert restored==oldbody
 def functions(s):return {n.name:ast.dump(n,include_attributes=False)for n in ast.parse(s).body if isinstance(n,(ast.FunctionDef,ast.ClassDef))}
 fa,fb=functions(oldbody),functions(newbody);assert fa.keys()==fb.keys();same=[k for k in fa if fa[k]==fb[k]];assert set(fa)-set(same)=={'deck'}
 recipes=[]
 for v in m.POINTS:
  c,rows,texts=m.config(v);oldc,oldrows,oldtexts=prior.config(v)
  normal=copy.deepcopy(c);normal['sources']=[p.replace('characterize_clamped570_03.py','characterize_clamped570_02.py')for p in normal['sources']]
  assert normal==oldc and rows==oldrows and texts==oldtexts
  expected=m.n.vectors(rows,c['extra_vectors']);lines=batch.commands(expected);deck=m.deck(c,rows,texts)
  assert deck==batch.replace_save(prior.deck(oldc,oldrows,oldtexts),expected)
  assert c['stop_s']==34e-9 and c['step_s']==3.125e-13 and c['window_s']==[4e-9,34e-9]
  assert len(rows)==570 and len(expected)==1133 and len(lines)==9
  path=B/f'recipe03-v{int(v*100):03d}.cir';assert not path.exists();path.write_text(deck)
  recipes.append(dict(vctrl=v,config=c,devices=rows,physical_texts=texts,deck=deck,observations=expected,save_commands=lines))
 (B/'recipes03.json').write_text(json.dumps(recipes,indent=2)+'\n')
 bridge=dict(status='EXACT_COMPLETE_DRIVER02_TO03_BATCHING_AND_NAMESPACE_ONLY',parent=pin(Path(prior.__file__)),output=pin(Path(m.__file__)),before=oldbody,after=newbody,full_diff=''.join(difflib.unified_diff(oldbody.splitlines(True),newbody.splitlines(True))),unchanged_functions=same,changed_functions=['deck'],control_reuse='All41 actual prior safety/storage/lifecycle controls remain original evidence. Every tested function/class AST is unchanged; only deck save emission and module namespace/import differ. Eight additional actual bounded native/observation controls bind new helper. No prior control or failed02 native rerun.',native_control=pin(N/'result.json'))
 (B/'batch-source-supplement03.json').write_text(json.dumps(bridge,indent=2)+'\n')
 resource=json.loads((B/'resource-contract02.json').read_text());resource['native_root']=str(m.NATIVE_ROOT)
 (B/'resource-contract03.json').write_text(json.dumps(resource,indent=2)+'\n')
 paths=set(map(Path,old['pins']))|set(map(Path,cf['pins']))
 paths.update([oldfreeze,controlfreeze,cp,B/'source-only-peer-root02.json',B/'resource-peer-pll02.json',B/'native02-failure-diagnosis01.json',C/'control-contract01.json'])
 paths.update(p for p in N.rglob('*')if p.is_file())
 paths.add(B.parent/'pcie-570-batch-native-control01.log')
 sources=['prepare_retry03.py','driver_custom03.py','capture_custom03.py','prepare_driver03.py','characterize_clamped570_03.py','launch_three03.py','freeze_source03.py']
 outputs=['retry-source-bridge03.json','driver-source-bridge03.json','batch-source-supplement03.json','recipes03.json','resource-contract03.json',*[f'recipe03-v{int(v*100):03d}.cir'for v in m.POINTS]]
 paths.update(B/p for p in sources+outputs)
 record=dict(status='FROZEN_CLAMPED570_THREE_POINT_DIAGNOSTICS_PENDING_SOURCE_PEER',pins={str(p.absolute()):pin(p)for p in sorted(paths)},products={name:pin(B/name)for name in sources},parent_freeze=pin(oldfreeze),parent_source_peer=pin(B/'source-only-peer-root02.json'),full_driver_bridge=pin(B/'driver-source-bridge03.json'),exact_complete_parent_inverse=pin(B/'batch-source-supplement03.json'),recipe_pin=pin(B/'recipes03.json'),resource_contract=pin(B/'resource-contract03.json'),runtime=old['runtime'],actual_controls=old['actual_controls'],inherited_actual_cases=41,new_actual_cases=8,total_reused_and_new_actual_cases=49,new_control=dict(path=str(N/'result.json'),pin=pin(N/'result.json'),source_freeze=pin(controlfreeze),source_peer=pin(cp)),source570_freeze=old['source570_freeze'],source570_peer=old['source570_peer'],parent455_freeze=old['parent455_freeze'],predeclared=old['predeclared'],scope='Fresh native03 only after independent source peer. Full34ns/.3125ps/window4–34ns and all570 safety/original13+4 predicates unchanged. Only save command arity split into9commands, exact1133-vector union/order retained and actual bounded2ps control passed. Source02/failed02/full65596-byte failed prefix preserved. Three clamped points are not570 convergence, pump reachability, tuning range/polarity, closed-loop acquisition or fullPHY acceptance.')
 (B/'source-freeze03.json').write_text(json.dumps(record,indent=2)+'\n');print(json.dumps(dict(freeze=pin(B/'source-freeze03.json'),pins=len(paths),driver=pin(Path(m.__file__)),unchanged_functions=same,new_native_control=pin(N/'result.json'))))
if __name__=='__main__':main()
