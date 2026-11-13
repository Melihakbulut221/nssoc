# SPDX-License-Identifier: Apache-2.0
import collections,copy,hashlib,io,json,pathlib,re,sys,zipfile
from audit_sram_flat_rc import parse,scalar,require
sys.path.insert(0,'hw/soc/flow')
from mos_graph_equivalence import prove_mos_graph
OUT=pathlib.Path('out');OUT.mkdir(exist_ok=True)
result=dict(status='UNPROVEN',full_macro_lvs=False,qualified_pex=False,manufacturing_approval=False)
def extract(path,sha,suffix,prefix=''):
 raw=pathlib.Path(path).read_bytes();require(hashlib.sha256(raw).hexdigest()==sha,'archive SHA mismatch')
 z=zipfile.ZipFile(io.BytesIO(raw));names=[n for n in z.namelist() if n.startswith(prefix) and n.endswith(suffix)]
 require(len(names)==1,'ambiguous native selection');return z.read(names[0])
def graph(m):
 require(not m['R'],'MOS projection has resistors');devices=[];nets=set(m['ports']);err=0
 for name,r in m['mos'].items():
  w,l=[scalar(r['params'][k])*1e6 for k in ['w','l']];rw,rl=round(w,12),round(l,12)
  err=max(err,abs(w-rw),abs(l-rl));require(err<1e-12 and rw>0 and rl>0,'dimension loss')
  devices.append(dict(name=name,model=r['model'],w=rw,l=rl,**dict(zip(['D','G','S','B'],r['nodes']))));nets.update(r['nodes'])
 require(len(devices)==8,'exactly eight MOS required')
 return dict(nets={n:n for n in nets},pins={p:p for p in m['ports']},devices=devices,maximum_float_normalization_um=err)
try:
 cc=extract('native.zip','35be261afbc97cb1b555e2678090caf4624424a47127aba3695e5411e8093b33','_k25d_pex_netlist.spice','CC/')
 ref=extract('reference.zip','124f6a92fa56346b1c471efb84750878180ef0c8056b2c940c5c6fce0e41e29b','reference.spice')
 require(hashlib.sha256(cc).hexdigest()=='cbc7dca6e387a67db742336a5f232184ea30e044c18c33c0c5fd77b516c0d57d','CC SHA mismatch')
 require(hashlib.sha256(ref).hexdigest()=='64d041383d0ebee7b54dab0bc10d651d31262a2a41ccd15a9c0727dac06e0dd9','reference SHA mismatch')
 matches=re.findall(r'^\s*\.subckt\s+DP8TCell\b.*?^\s*\.ends[^\n]*',ref.decode(),re.I|re.M|re.S);require(len(matches)==1,'leaf selection ambiguous')
 a,b=parse(matches[0]),parse(cc.decode())
 result.update(reference_spice_sha256=hashlib.sha256(ref).hexdigest(),extracted_netlist_sha256=hashlib.sha256(cc).hexdigest(),ports={'reference':a['ports'],'extracted':b['ports']},models={'reference':dict(collections.Counter(x['model'] for x in a['mos'].values())),'extracted':dict(collections.Counter(x['model'] for x in b['mos'].values()))},counts={'reference':len(a['mos']),'extracted':len(b['mos'])},scope='Independent schematic vs extracted MOS projection. Every named port, model, W/L, gate and bulk preserved. Only D/S interchange allowed. No aliases/body ties. RC accuracy and full macro excluded.')
 ga,gb=graph(a),graph(b);proof=prove_mos_graph(ga,gb);proof.pop('mapping')
 bad=copy.deepcopy(gb);bad['devices'][0]['w']*=2
 try:prove_mos_graph(ga,bad);raise AssertionError('wrong geometry accepted')
 except ValueError:pass
 result.update(status='PASS_SCOPED_INDEPENDENT_MOS_GRAPH',proof=proof,changed_geometry_rejected=True)
except Exception as e:result.update(status='FAIL_OR_INCONCLUSIVE_INDEPENDENT_MOS_GRAPH',error=type(e).__name__+': '+str(e))
(OUT/'result.json').write_text(json.dumps(result,indent=2));print(json.dumps(result));raise SystemExit(0 if result['status'].startswith('PASS_') else 1)
