# SPDX-License-Identifier: Apache-2.0
"""Independent flat MOS/RC connectivity and collapsed pair-capacitance check.
No calibrated extraction, spatial C placement, body RC or Liberty approval.
"""
import collections,copy,hashlib,io,json,math,pathlib,re,zipfile
OUT=pathlib.Path('out');OUT.mkdir(exist_ok=True)
class Rejected(Exception):pass
def require(ok,message):
 if not ok:raise Rejected(message)
def scalar(s):
 m=re.fullmatch(r'([+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:e[+-]?\d+)?)(meg|[tgkmunpf]?)',s.lower())
 require(m is not None,'unsupported passive value')
 value=float(m[1])*{'':1,'t':1e12,'g':1e9,'meg':1e6,'k':1e3,'m':1e-3,'u':1e-6,'n':1e-9,'p':1e-12,'f':1e-15}[m[2]]
 require(math.isfinite(value) and value>0,'nonpositive/nonfinite passive')
 return value
def parse(text):
 lines=[]
 for raw in text.splitlines():
  s=raw.strip()
  if not s or s.startswith('*'):continue
  if s.startswith('+'):
   require(bool(lines),'orphan continuation');lines[-1]+=' '+s[1:]
  else:lines.append(s)
 result=dict(mos={},R={},C={},ports=[]);names=set();sub=0
 for line in lines:
  t=line.lower().split();kind=t[0][0]
  if t[0]=='.subckt':
   sub+=1;result['ports']=t[2:];continue
  if t[0] in ['.ends','.end']:continue
  require(kind in ['r','c','m','x'],'unsupported SPICE statement '+t[0])
  require(t[0] not in names,'duplicate instance');names.add(t[0])
  if kind in ['r','c']:
   require(len(t)==4,'unsupported passive card shape');result[kind.upper()][t[0]]=(t[1],t[2],scalar(t[3]));continue
  params={};pos=[]
  for v in t[1:]:
   if '=' in v:
    k,val=v.split('=',1);require(k not in params,'duplicate device parameter');params[k]=val
   else:pos.append(v)
  require(len(pos)==5,'unsupported non-four-terminal MOS instance')
  result['mos'][t[0]]={'nodes':pos[:4],'model':pos[4],'params':params}
 require(sub==1,'requires one flat subcircuit')
 require(len(set(result['ports']))==len(result['ports']),'duplicate ports')
 return result
def audit(cc,rc):
 require(not cc['R'],'CC reference has resistors')
 require(cc['ports']==rc['ports'],'port order differs')
 require(set(cc['mos'])==set(rc['mos']) and len(cc['mos'])==8,'eight MOS identities differ')
 parent={}
 def find(n):
  parent.setdefault(n,n)
  if parent[n]!=n:parent[n]=find(parent[n])
  return parent[n]
 def union(a,b):
  a,b=find(a),find(b)
  if a!=b:parent[b]=a
 for a,b,v in rc['R'].values():union(a,b)
 mapping={};inverse=collections.defaultdict(set)
 def bind(n,ref):
  root=find(n);require(root not in mapping or mapping[root]==ref,'resistor short between reference nets')
  mapping[root]=ref;inverse[ref].add(root)
 for p in cc['ports']:bind(p,p)
 for name,a in cc['mos'].items():
  b=rc['mos'][name];require(a['model']==b['model'] and a['params']==b['params'],'device model/geometry changed')
  for n,ref in zip(b['nodes'],a['nodes']):bind(n,ref)
 require(all(len(roots)==1 for roots in inverse.values()),'reference net split across resistance components')
 missing_roots={find(n) for a,b,v in rc['C'].values() for n in [a,b]}-set(mapping)
 require(not missing_roots,'capacitor endpoint without port/device anchor')
 require(all(find(a) in mapping for a,b,v in rc['R'].values()),'unanchored resistor network')
 def caps(rows,mapper):
  pairs=collections.defaultdict(float);self_c=0
  for a,b,v in rows.values():
   a,b=mapper(a),mapper(b)
   if a==b:self_c+=1;continue
   pairs[tuple(sorted([a,b]))]+=v
  return pairs,self_c
 ref,_=caps(cc['C'],lambda x:x);got,self_c=caps(rc['C'],lambda x:mapping[find(x)])
 missing=set(ref)-set(got);extra=set(got)-set(ref)
 changed=[k for k in set(ref)&set(got) if abs(ref[k]-got[k])>1e-23+1e-5*abs(ref[k])]
 result=dict(mos=8,rc_resistors=len(rc['R']),cc_capacitors=len(cc['C']),rc_capacitors=len(rc['C']),reference_pairs=len(ref),projected_pairs=len(got),missing_pairs=len(missing),extra_pairs=len(extra),changed_pairs=len(changed),reference_sum_f=sum(ref.values()),projected_sum_f=sum(got.values()),collapsed_intraconductor_capacitors=self_c,max_pair_difference_f=max([abs(ref.get(k,0)-got.get(k,0)) for k in set(ref)|set(got)],default=0))
 return result,not(missing or extra or changed)
def main():
 raw=pathlib.Path('native.zip').read_bytes();require(hashlib.sha256(raw).hexdigest()=='35be261afbc97cb1b555e2678090caf4624424a47127aba3695e5411e8093b33','artifact hash mismatch')
 z=zipfile.ZipFile(io.BytesIO(raw));models={};sha={}
 for mode,expected in [('CC','cbc7dca6e387a67db742336a5f232184ea30e044c18c33c0c5fd77b516c0d57d'),('RC','77b35e72ed46865efaaf440cecfad07c78e4468fc1dad193cc94f19651c94dde')]:
  matches=[n for n in z.namelist() if n.startswith(mode+'/') and n.endswith('_k25d_pex_netlist.spice')];require(len(matches)==1,'netlist selection ambiguous')
  b=z.read(matches[0]);sha[mode]=hashlib.sha256(b).hexdigest();require(sha[mode]==expected,'netlist hash mismatch');models[mode]=parse(b.decode())
 cc,rc=models['CC'],models['RC'];result,passed=audit(cc,rc)
 controls={}
 # Remove the largest capacitor: a physical coupling loss must be rejected.
 key=max(rc['C'],key=lambda k:rc['C'][k][2]);bad=copy.deepcopy(rc);del bad['C'][key]
 try:_,accepted=audit(cc,bad)
 except Rejected:accepted=False
 controls['removed_capacitor']={'instance':key,'rejected':not accepted}
 # Seek a bridge resistance whose removal disconnects a real terminal/port net.
 for key in rc['R']:
  bad=copy.deepcopy(rc);del bad['R'][key]
  try:audit(cc,bad)
  except Rejected as e:
   if 'split' in str(e):controls['disconnected_resistor']={'instance':key,'rejected':True,'reason':str(e)};break
 controls.setdefault('disconnected_resistor',{'rejected':False,'reason':'no terminal-disconnecting bridge found'})
 bad=copy.deepcopy(rc);first=next(iter(bad['mos']));bad['mos'][first]['model']='deliberately_wrong_model'
 try:audit(cc,bad);rejected=False
 except Rejected:rejected=True
 controls['changed_mos_model']={'rejected':rejected}
 result.update(status='PASS_SCOPED_COLLAPSED_RC_CHECKS' if passed and all(x['rejected'] for x in controls.values()) else 'FAIL_SCOPED_RC_CHECKS',source_artifact=14067369661,netlist_sha256=sha,controls=controls,qualified_pex=False,manufacturing_approval=False,scope='Eight-device leaf only; same-engine CC versus resistor-collapsed RC with exact MOS identities/parameters and terminal anchors. No independent schematic LVS, spatial C proof, calibrated physical model, full well/body RC or full-macro qualification.')
 (OUT/'result.json').write_text(json.dumps(result,indent=2));print(json.dumps(result));return result['status'].startswith('PASS_')
try:ok=main()
except Exception as e:
 (OUT/'result.json').write_text(json.dumps(dict(status='ERROR',error=type(e).__name__+': '+str(e),qualified_pex=False,manufacturing_approval=False),indent=2));raise
raise SystemExit(0 if ok else 1)
