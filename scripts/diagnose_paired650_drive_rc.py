"""Exact failed native circuit topology and metal-only loading diagnosis."""
import os,json,subprocess,hashlib,zipfile,collections,pathlib
import numpy as np
from scipy.sparse import coo_matrix
from scipy.sparse.linalg import splu
import cdr_mos650_spice_syntax as parser
assert os.environ.get('GITHUB_ACTIONS')=='true'
P='repos/Melihakbulut221/nssoc/';out=pathlib.Path('out');out.mkdir();work=pathlib.Path('/mnt/paired650-wave-audit');work.mkdir(exist_ok=True)
def api(s):return json.loads(subprocess.check_output(['gh','api',P+s]))
r=api('actions/runs/43642783223');assert r['status']=='completed'and r['conclusion']=='failure'and r['head_sha']=='15a63339b7a18be32652b2d481c863bd8936c208'
a=api('actions/artifacts/14135837525');digest='fdee30ae9abd5a38d685b819d7cb3fc84840a3fab2cbef0f4aa8ded130997c0c';assert a['workflow_run']['id']==r['id']and a['workflow_run']['head_sha']==r['head_sha']and a['digest']=='sha256:'+digest and not a['expired']
p=work/'native.zip'
with p.open('xb')as f:subprocess.run(['gh','api',P+'actions/artifacts/14135837525/zip'],stdout=f,check=True)
with p.open('rb')as f:assert hashlib.file_digest(f,'sha256').hexdigest()==digest
z=zipfile.ZipFile(p)
def member(suffix,sha):
 names=[n for n in z.namelist()if n.endswith(suffix)];assert len(names)==1,names
 b=z.read(names[0]);assert hashlib.sha256(b).hexdigest()==sha
 return b
contract=json.loads(member('/composition-n1/contract.json','ef839c27e19bf819aa6894f2b99774b2202f6d7694c434f39a64ea9798cd8b86'))
model=member('/composition-n1/model.cir','dd2922e9bfecfbf085ff093099c43568c399df7e3c199063333aa7f7db1c4fbb').decode()
rows=parser.statements(model);start=[i for i,r in enumerate(rows)if r[:2]==['.subckt','nssoc_cdr650_gate_n1']];assert len(start)==1
body=rows[start[0]+1:];assert body[-1][:1]==['.ends'];body=body[:-1]
rs=[(r[1].lower(),r[2].lower(),float(parser.number(r[3])))for r in body if r[0].lower().startswith('r')]
cs=[(r[1].lower(),r[2].lower(),float(parser.number(r[3])))for r in body if r[0].lower().startswith('c')]
assert len(rs)==28634 and len(cs)==18488
adj=collections.defaultdict(list)
for u,v,value in rs:
 assert value>0;adj[u].append((v,value));adj[v].append((u,value))
records=contract['devices'];assert len(records)==650
nets=['aqp','aqn','bqp','bqn','cqp','cqn','dqp','dqn','adp','adn','cdp','cdn','s0p','s0n','s1p','s1n']
nets += [prefix+'_n_'+suffix for prefix in ['x','y']for suffix in ['40','51','62','42','46']]
result={'source_run':r['id'],'source_head':r['head_sha'],'native_artifact':a['id'],'native_archive_sha256':digest,'model_sha256':'dd2922e9bfecfbf085ff093099c43568c399df7e3c199063333aa7f7db1c4fbb','contract_sha256':'ef839c27e19bf819aa6894f2b99774b2202f6d7694c434f39a64ea9798cd8b86','accepted':False,'scope':'Actual source identity, component topology, metal resistor effective R and metal external-coupling first moment with all other conductors clamped. Excludes intrinsic device/MIM loading and finite driver resistance. Not qualified PEX, bandwidth, a new transient, or changed acceptance.','nets':{}}
for net in nets:
 devices=[d for d in records if net in d['logical_terminals'].values()]
 drivers=[d for d in devices if d['model']=='npn13g2'and d['logical_terminals']['C']==net and d['logical_terminals']['B']!=net[:-1]+('n'if net.endswith('p')else'p')]
 reference_terminal='C';reference_role='unique_data_driver_collector'
 if net.startswith(('x_n_','y_n_')):
  reference_role='canonical_shared_net_reference_not_unique_driver'
  drivers=[q for q in devices if q['model']=='npn13g2'and q['logical_terminals']['C']==net]
  if not drivers:
   reference_terminal='E';drivers=[q for q in devices if q['model']=='npn13g2'and q['logical_terminals']['E']==net]
  assert drivers
  drivers=[min(drivers,key=lambda q:q['native_id'])]
 assert len(drivers)==1,(net,len(drivers))
 driver=drivers[0]['instances'][0]['nodes'][0 if reference_terminal=='C'else 2].lower();assert driver in adj
 seen={driver};queue=[driver]
 while queue:
  u=queue.pop()
  for v,value in adj[u]:
   if v not in seen:seen.add(v);queue.append(v)
 nodes=sorted(seen-{driver});index={n:i for i,n in enumerate(nodes)};n=len(nodes);rr=[];cc=[];vv=[];cvec=np.zeros(n);external_c=0.;internal_c=0.
 for u,v,value in rs:
  if u not in seen:continue
  assert v in seen;g=1/value
  for node in [u,v]:
   if node!=driver:rr.append(index[node]);cc.append(index[node]);vv.append(g)
  if u!=driver and v!=driver:
   rr.extend([index[u],index[v]]);cc.extend([index[v],index[u]]);vv.extend([-g,-g])
 for u,v,value in cs:
  inside=(u in seen)+(v in seen)
  if inside==2:internal_c+=value
  elif inside==1:
   external_c+=value;node=u if u in seen else v
   if node!=driver:cvec[index[node]]+=value
 matrix=coo_matrix((vv,(rr,cc)),shape=(n,n)).tocsc();lu=splu(matrix);moments=lu.solve(cvec);assert np.isfinite(moments).all()and moments.min()>-1e-18
 terms=[];touch=[]
 for d in devices:
  inst=d['instances'];touch.append({k:d[k]for k in ['native_id','model','logical_terminals','native_parameters','original_source','instances']})
  # compact model order for non-MOS is available in their node order; bind
  # selected HBT terminals directly (C B E substrate) without guessing.
  if d['model']=='npn13g2':
   for t,pos in [('C',0),('B',1),('E',2)]:
    if d['logical_terminals'][t]!=net:continue
    node=inst[0]['nodes'][pos].lower();assert node in seen,(net,d['native_id'],t,node)
    if node==driver:resistance=moment=0.
    else:
     drive=np.zeros(n);drive[index[node]]=1;solved=lu.solve(drive);assert np.linalg.norm(matrix@solved-drive,np.inf)<1e-6
     resistance=float(solved[index[node]]);moment=float(moments[index[node]])
    terms.append({'native_id':d['native_id'],'terminal':t,'node':node,'effective_metal_resistance_from_driver_ohm':resistance,'metal_external_clamped_first_moment_s':moment})
 result['nets'][net]={'reference_role':reference_role,'reference_terminal':reference_terminal,'driver_native_id':drivers[0]['native_id'],'driver_node':driver,'metal_nodes':len(seen),'external_metal_c_f':external_c,'internal_metal_c_f':internal_c,'maximum_metal_external_clamped_first_moment_s':float(moments.max()),'hbt_terminal_connections':terms,'physical_devices_on_logical_net':touch}
result['scope'] += ' Shared comparator nets use an explicitly labeled canonical terminal reference, not a unique driver. Effective R and clamped-metal first moments do not include nonlinear loading or imply full settling/signoff.'
assert len(result['nets'])==26
(out/'drive-rc.json').write_text(json.dumps(result,indent=2))
