"""Native metal boundary-C and open-circuit DC resistance diagnostics only."""
import json,hashlib,subprocess,zipfile,tarfile,math,os
from pathlib import Path
from collections import Counter,defaultdict
from decimal import Decimal
import numpy as np
from scipy.sparse import coo_matrix
from scipy.sparse.linalg import splu
import cdr_mos650_spice_syntax as parser
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'wire-load-compare';OUT.mkdir();NATIVE=OUT/'native';NATIVE.mkdir();DERIVED=OUT/'derived';DERIVED.mkdir()
P='repos/Melihakbulut221/nssoc/'
def sha(p):
 with Path(p).open('rb')as f:return hashlib.file_digest(f,'sha256').hexdigest()
def api(s):return json.loads(subprocess.check_output(['gh','api',P+s],timeout=60))
def archive(aid,digest,run,head,name):
 r=api('actions/runs/'+str(run));assert r['status']=='completed'and r['conclusion']=='success'and r['head_sha']==head
 m=api('actions/artifacts/'+str(aid));assert m['workflow_run']['id']==run and m['workflow_run']['head_sha']==head and m['digest']=='sha256:'+digest and not m['expired']
 path=NATIVE/name
 with path.open('xb')as f:subprocess.run(['gh','api',P+'actions/artifacts/'+str(aid)+'/zip'],stdout=f,check=True)
 assert sha(path)==digest;return zipfile.ZipFile(path)
def old_source(spec,selection):
 r=api('actions/runs/'+str(spec['run']));assert r['status']=='completed'and r['conclusion']=='success'and r['head_sha']==spec['source']
 rec=spec['assets'][spec['archive']];m=api('releases/assets/'+str(rec['id']));assert m['size']==rec['bytes']and m['digest']=='sha256:'+rec['sha256']
 path=NATIVE/(str(spec['run'])+'.tgz')
 with path.open('xb')as f:subprocess.run(['gh','api',P+'releases/assets/'+str(rec['id']),'-H','Accept: application/octet-stream'],stdout=f,check=True)
 assert sha(path)==rec['sha256'];rows={}
 with tarfile.open(path)as tar:
  for name in selection:
   raw=tar.extractfile(spec['archive_root']+'/'+name).read();assert {'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}==spec['selected'][name];rows[name]=raw
 return rows

def effective(edges,source,sink):
 if source==sink:return 0.0
 nodes=sorted({n for a,b,v in edges for n in (a,b)}-{sink});index={n:i for i,n in enumerate(nodes)};rr=[];cc=[];vv=[]
 for a,b,v in edges:
  g=1/float(v);i=index.get(a);j=index.get(b)
  for k in (i,j):
   if k is not None:rr.append(k);cc.append(k);vv.append(g)
  if i is not None and j is not None:rr.extend([i,j]);cc.extend([j,i]);vv.extend([-g,-g])
 L=coo_matrix((vv,(rr,cc)),shape=(len(nodes),len(nodes))).tocsc();L.sum_duplicates();inj=np.zeros(len(nodes));inj[index[source]]=1;u=splu(L).solve(inj)
 assert np.max(np.abs(L@u-inj))<1e-8,'DC nodal residual'
 value=float(u[index[source]]);assert math.isfinite(value)and value>0;return value
assert math.isclose(effective([('a','b',10),('b','c',20)],'a','c'),30,rel_tol=1e-12)
assert math.isclose(effective([('a','b',10),('a','b',20)],'a','b'),20/3,rel_tol=1e-12)
assert math.isclose(effective([('a','b',10),('b','c',20),('b','d',500)],'a','c'),30,rel_tol=1e-12)

def measure(identity,anchors,text,expected_C):
 pairs={p['layout']['id']:p for p in identity['pairs']};rows={(r['device'],r['terminal'].upper()):r for r in anchors['rows']};assert len(pairs)==650 and len(rows)==2046
 cards=parser.statements(text);assert cards[0][:2]==['.subckt','pump_wires']and cards[-1][0]=='.ends'
 counts=Counter(r[0][0]for r in cards[1:-1]);assert counts=={'R':28634,'C':expected_C,'X':7}
 graph=parser.Union();resistors=[];caps=[]
 for r in cards[1:-1]:
  if r[0][0] not in 'RC':continue
  assert len(r)==4 and r[1]!=r[2];v=parser.number(r[3]);assert v>=0
  if r[0][0]=='R':assert v>0;graph.join(r[1],r[2]);resistors.append((r[1],r[2],v))
  else:caps.append((r[1],r[2],v))
 groups=defaultdict(list)
 for e in resistors:groups[graph.find(e[0])].append(e)
 physical={a['label']:a for a in anchors['anchors']};assert len(physical)==1428
 owner={}
 for label,p in physical.items():
  assert label in graph.parent
  root=graph.find(label);assert owner.setdefault(root,p['wire_component'])==p['wire_component']
 assert len(owner)==len(set(owner.values()))==len(groups)==113
 targets=['adp','adn','cdp','cdn','s0p','s0n','s1p','s1n','aqp','aqn','cqp','cqn'];out={}
 for net in targets:
  selected=[]
  for i,pair in pairs.items():
   if pair['layout']['model']!='npn13g2':continue
   for reference,term in pair['reference_to_layout_terminal'].items():
    if pair['original_source']['terminals'][reference].lower()!=net or term not in ('B','C'):continue
    row=rows[i,term];assert row['disposition']=='ACTUAL_TERMINAL_METAL_POINT_REFERENCE';label=row['wire_anchor'];assert label in physical
    selected.append({'native_id':i,'origin_native_id':pair['original_source']['origin_native_id'],'terminal':term,'anchor':label})
  assert selected;roots={graph.find(x['anchor'])for x in selected};assert len(roots)==1
  root=next(iter(roots));nodes={n for e in groups[root]for n in e[:2]};ground=Decimal(0);coupled=Decimal(0);internal=Decimal(0);records=0
  for aa,bb,v in caps:
   left=aa in nodes;right=bb in nodes
   if left and right:internal+=v
   elif left or right:
    records+=1;other=bb if left else aa
    if other=='sub':ground+=v
    else:coupled+=v
  drivers=[x for x in selected if x['terminal']=='C'];sinks=[x for x in selected if x['terminal']=='B'];assert drivers and sinks
  dc=[]
  for d in drivers:
   for s in sinks:
    value=effective(groups[root],d['anchor'],s['anchor']);reverse=effective(groups[root],s['anchor'],d['anchor']);assert math.isclose(value,reverse,rel_tol=1e-8,abs_tol=1e-10)
    dc.append({'driver_origin':d['origin_native_id'],'sink_origin':s['origin_native_id'],'driver_native':d['native_id'],'sink_native':s['native_id'],'resistance_ohm':value})
  out[net]={'wire_component':owner[root],'native_nodes':len(nodes),'native_R_branches':len(groups[root]),'ground_C_fF':float(ground*Decimal(10)**15),'boundary_coupling_C_fF':float(coupled*Decimal(10)**15),'internal_C_fF':float(internal*Decimal(10)**15),'boundary_C_records':records,'semantic_HBT_terminals':selected,'open_circuit_DC_resistance':dc}
 return out

result={'accepted':False,'full_phy_accepted':False,'timing_accepted':False,'scope':'Native wire-only diagnostics: coupling is not grounded effective load. DC resistance excludes intrinsic devices. Not RF PEX, delay or loaded electrical acceptance.','context':{'run':os.environ['GITHUB_RUN_ID'],'source':os.environ['GITHUB_SHA']}}
try:
 assert os.environ['GITHUB_ACTIONS']=='true'
 cfg=json.loads((ROOT/'scripts/cdr-mos650-gate-ac-inputs.json').read_text())
 oldmetal=old_source(cfg['mim'],['native/mim-precise/wire/anchors08.json','native/mim-precise/wire/rc03/wires.spice']);oldid=old_source(cfg['current_wire'],['derived/lvs_flat-identity.json'])
 newmetal=archive(14125201998,'1443428cee3752ae7c9b14aa65d01e614520ca5547e79abf8e406ff3c56617fb',43623877135,'ca7922a41bb122ec714a23cd2ca5b7ea63d197ba','new-metal.zip')
 newid=archive(14125295448,'d8376d4009da54acbe52569fd119add9f07f4f13d8120ebc65bd5fa193c899ac',43622884786,'e0a87989915cb7d65a20176de33649859f013393','new-identity.zip')
 old=measure(json.loads(oldid['derived/lvs_flat-identity.json']),json.loads(oldmetal['native/mim-precise/wire/anchors08.json']),oldmetal['native/mim-precise/wire/rc03/wires.spice'].decode(),18476)
 new=measure(json.loads(newid.read('lvs_flat-identity.json')),json.loads(newmetal.read('mos650-metal-rc/native/mim-precise/wire/anchors08.json')),newmetal.read('mos650-metal-rc/native/mim-precise/wire/rc03/wires.spice').decode(),18488)
 result.update(old=old,new=new,status='COMPLETE_NATIVE_WIRE_DIAGNOSTIC_NOT_ELECTRICAL_ACCEPTANCE',analytic_controls=3)
except BaseException as e:
 result.update(status='FAIL_OR_ERROR',error=repr(e));raise
finally:
 (DERIVED/'result.json').write_text(json.dumps(result,indent=2)+'\n')
