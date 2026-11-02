#!/usr/bin/env python3
"""Compare all eight actual extracted access networks; no physical acceptance."""
import hashlib,json,math,os,subprocess,tarfile,shlex
from pathlib import Path
from collections import Counter,defaultdict
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'clock-access-resistance'
REPO='Melihakbulut221/nssoc'
def need(ok,msg):
    if not ok:raise ValueError(msg)
def pin(b):return dict(bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def api(path):return json.loads(subprocess.check_output(['gh','api','repos/'+REPO+'/'+path],timeout=180))
def save(name,value): (OUT/name).write_text(json.dumps(value,sort_keys=True,indent=2,allow_nan=False)+'\n')

def number(token):
    import re
    from decimal import Decimal
    m=re.fullmatch(r"([-+]?\d+(?:\.\d*)?(?:[eE][-+]?\d+)?)([numkpf]?)",token.lower())
    need(m is not None,"finite supported resistance token")
    v=Decimal(m[1])*{"":Decimal(1),"n":Decimal("1e-9"),"u":Decimal("1e-6"),"m":Decimal("1e-3"),"k":Decimal("1e3"),"p":Decimal("1e-12"),"f":Decimal("1e-15")}[m[2]]
    need(v.is_finite()and v>0,"positive physical resistance")
    return v
def solve(edges,source,sink):
    import numpy as np
    from scipy.sparse import coo_matrix
    from scipy.sparse.linalg import spsolve
    adjacency={}
    for name,a,b,r in edges:
        need(a!=b and math.isfinite(r)and r>0,"valid resistor")
        adjacency.setdefault(a,set()).add(b);adjacency.setdefault(b,set()).add(a)
    need(source!=sink and source in adjacency and sink in adjacency,"distinct original ports")
    seen={source};todo=[source]
    while todo:
        for n in adjacency[todo.pop()]:
            if n not in seen:seen.add(n);todo.append(n)
    need(sink in seen,"same connected native resistor component")
    selected=[e for e in edges if e[1]in seen]
    names=sorted(seen-{sink});idx={n:i for i,n in enumerate(names)}
    rr=[];cc=[];vv=[]
    for _,a,b,r in selected:
        for n,other in ((a,b),(b,a)):
            if n==sink:continue
            rr.append(idx[n]);cc.append(idx[n]);vv.append(1/r)
            if other!=sink:rr.append(idx[n]);cc.append(idx[other]);vv.append(-1/r)
    matrix=coo_matrix((vv,(rr,cc)),shape=(len(names),len(names))).tocsc()
    rhs=np.zeros(len(names));rhs[idx[source]]=1
    volt=spsolve(matrix,rhs)
    need(np.isfinite(volt).all(),"finite connected solve")
    residual=float(np.max(np.abs(matrix@volt-rhs)))
    need(residual<1e-8,"unit injection KCL")
    potentials={n:float(volt[i])for n,i in idx.items()};potentials[sink]=0.
    ranked=[]
    for name,a,b,r in selected:
        current=(potentials[a]-potentials[b])/r
        ranked.append(dict(element=name,a=a,b=b,resistance_ohm=r,unit_current_a=current,power_at_1a_w=current*current*r))
    resistance=potentials[source];energy=sum(e["power_at_1a_w"]for e in ranked)
    need(resistance>0 and math.isclose(resistance,energy,rel_tol=1e-8,abs_tol=1e-9),"positive effective resistance equals full network power")
    for e in ranked:e["fraction_of_effective_resistance"]=e["power_at_1a_w"]/resistance
    return dict(source=source,sink=sink,effective_resistance_ohm=resistance,kcl_max_residual_a=residual,
                nodes=len(seen),edges=len(selected),all_edges=sorted(ranked,key=lambda x:-x["power_at_1a_w"]))
def controls():
    a=solve([("r1","a","b",2.),("r2","b","c",3.),("r3","a","c",5.)],"a","c")
    need(math.isclose(a["effective_resistance_ohm"],2.5),"parallel-series analytic control")
    reverse=solve([("r1","a","b",2.),("r2","b","c",3.),("r3","a","c",5.)],"c","a")
    need(math.isclose(a["effective_resistance_ohm"],reverse["effective_resistance_ohm"]),"reciprocity")
    rejected=[]
    for label,edges,s,t in [
      ("disconnected",[("r","a","b",1.),("q","c","d",2.)],"a","c"),
      ("negative",[("r","a","b",-1.)],"a","b"),
      ("nan",[("r","a","b",float("nan"))],"a","b"),
      ("same_port",[("r","a","b",1.)],"a","a")]:
        try:solve(edges,s,t)
        except ValueError:rejected.append(label)
        else:raise ValueError("missed resistance refusal")
    return dict(analytic_resistance_ohm=2.5,reciprocity=True,rejected=rejected,physical_acceptance=False)

def main():
    need(os.environ.get('GITHUB_ACTIONS')=='true'and os.environ.get('RUNNER_ENVIRONMENT')=='github-hosted','hosted only')
    need(os.environ['GITHUB_REPOSITORY']==REPO and os.environ['GITHUB_REF']=='refs/heads/codex/cdr-clock-metal-resistance','exact source branch')
    need(os.environ['GITHUB_EVENT_NAME']=='workflow_dispatch'and os.environ['GITHUB_RUN_ATTEMPT']=='1','first explicit dispatch')
    need(os.environ['APPROVED_SOURCE']==os.environ['GITHUB_SHA'],'approved source')
    need(subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()==os.environ['GITHUB_SHA'],'exact checkout')
    m=json.loads((ROOT/'scripts/cdr-clock-access-resistance-pins.json').read_bytes())
    for name,want in m['files'].items():need(pin((ROOT/name).read_bytes())==want,'pinned source '+name)
    OUT.mkdir()
    save('controls.json',controls())
    basis=json.loads((ROOT/'scripts/cdr-clock-access-resistance-basis.json').read_bytes())
    p=basis['producer'];run=api('actions/runs/'+str(p['run']));rel=api('releases/'+str(p['release']))
    need(run['head_sha']==p['source']and run['conclusion']=='success'and run['run_attempt']==1,'actual successful fresh RC')
    need(rel['target_commitish']==p['source']and rel['tag_name']==p['tag']and api('git/ref/tags/'+p['tag'])['object']['sha']==p['source'],'RC source release')
    live={v['name']:v for v in rel['assets']}
    need(set(live)==set(p['assets']),'complete asset set')
    paths={}
    for name,want in p['assets'].items():
        a=live[name];need(a['id']==want['id']and a['size']==want['bytes']and a['digest']=='sha256:'+want['sha256'],'asset identity')
        target=OUT/name
        with target.open('wb')as stream:subprocess.run(['gh','api','repos/'+REPO+'/releases/assets/'+str(a['id']),'-H','Accept: application/octet-stream'],stdout=stream,check=True,timeout=300)
        need(pin(target.read_bytes())=={k:want[k]for k in ('bytes','sha256')},'download digest');paths[name]=target
    index=json.loads(paths['complete-output-index.json'].read_bytes())
    need(index['files']==p['complete_members']and index['context']==dict(source=p['source'],run=p['run'],attempt=1),'full native index')
    selected={'mim/precise/wire/rc03/wires.spice','mim/precise/wire/rc03/pump_wires.ext','mim/precise/wire/rc03/pump_wires.res.ext','mim/precise/wire/anchors08.json','mim/composition/composition.json','fresh-rc-qualification.json'}
    content={};seen=set()
    with tarfile.open(paths['native-fresh-rc.tar.gz'],'r:gz')as tar:
        for item in tar:
            need(item.isfile(),'only indexed files')
            prefix=p['archive_root']+'/'
            need(item.name.startswith(prefix),'actual archive root')
            name=item.name[len(prefix):]
            need(name in index['files']and name not in seen,'unique indexed member');seen.add(name)
            h=hashlib.sha256();size=0;parts=[]
            stream=tar.extractfile(item)
            while True:
                chunk=stream.read(1024*1024)
                if not chunk:break
                size+=len(chunk);h.update(chunk)
                if name in selected:parts.append(chunk)
            need(dict(bytes=size,sha256=h.hexdigest())==index['files'][name],'every native member digest')
            if name in selected:content[name]=b''.join(parts)
    need(seen==set(index['files'])and set(content)==selected,'complete archive authentication')
    q=json.loads(content['fresh-rc-qualification.json']);need(q==basis['qualification'],'actual qualification')
    parse=lambda name:[shlex.split(line,comments=False)for line in content[name].decode().splitlines()if line.strip()and not line.lstrip().startswith('*')]
    exported=[r for r in parse('mim/precise/wire/rc03/wires.spice')if r[0].lower().startswith('r')]
    distributed=parse('mim/precise/wire/rc03/pump_wires.res.ext')
    key=lambda a,b,r:(tuple(sorted((a.lower(),b.lower()))),number(r))
    need(len(exported)==q['counts']['R']==26344 and all(len(r)==4 for r in exported),'all26344 actual resistors')
    need(Counter(key(*r[1:4])for r in exported)==Counter(key(*r[1:4])for r in distributed if r[0]=='resist'),'native/exported complete R agreement')
    edges=[(r[0].lower(),r[1].lower(),r[2].lower(),float(number(r[3])))for r in exported]
    need(len({e[0]for e in edges})==len(edges),'unique R elements')
    points=defaultdict(list)
    for r in distributed:
        if r[0]=='rnode':
            need(len(r)==7,'original rnode record')
            points[r[1].lower()].append(dict(point_dbu=[int(r[4])*5,int(r[5])*5],raw=r))
    anchors={a['label']:a for a in json.loads(content['mim/precise/wire/anchors08.json'])['anchors']}
    ports={r[1]:r for r in parse('mim/precise/wire/rc03/pump_wires.ext')if r[0]=='port'}
    need(len(anchors)==978 and set(ports)==set(anchors),'all actual978 anchors')
    for name,r in ports.items():need(r[3:5]==r[5:7]and all(abs(int(v)*5-x)<=2 for v,x in zip(r[3:5],anchors[name]['point_dbu'])),'native anchor coordinates')
    comp=json.loads(content['mim/composition/composition.json'])
    baseline=json.loads((ROOT/'docs/evidence/clock-access-original-eight-resistances.json').read_bytes())
    queries=[];comparisons=[]
    for upper,clock in [(u,c)for us,cs in [((54,56),(61,62)),((106,108),(115,116))]for u in us for c in cs]:
        labels=['T'+str(upper).zfill(3)+'_E','T'+str(clock).zfill(3)+'_C']
        for did,term,label in [(upper,'E',labels[0]),(clock,'C',labels[1])]:
            a=anchors[label];record=next(t for d in comp['device_records']if d['native_id']==did for t in d['terminals']if t['terminal']==term)
            need(record['anchor']==label and record['native_cluster']==a['native_cluster']and record['native_net']==a['detail']['native_net'],'actual composition/native anchor binding')
        need(anchors[labels[0]]['wire_component']==anchors[labels[1]]['wire_component'],'same native path')
        result=solve(edges,*[s.lower()for s in labels])
        for edge in result['all_edges']:edge['native_coordinates']={k:points[edge[k]]for k in ('a','b')}
        queries.append(result)
        previous=[r for r in baseline['queries']if r['source']==result['source']and r['sink']==result['sink']]
        need(len(previous)==1,'exact prior source/sink query')
        old=previous[0]['effective_resistance_ohm'];new=result['effective_resistance_ohm']
        comparisons.append(dict(source=result['source'],sink=result['sink'],old_ohm=old,new_ohm=new,delta_ohm=new-old,reduction_percent=(old-new)/old*100))
    save('result.json',dict(status='MEASURED_ALL_EIGHT_NEW_VS_OLD_NATIVE_RC_PATHS',source=os.environ['GITHUB_SHA'],run=int(os.environ['GITHUB_RUN_ID']),fresh_rc_run=p['run'],all_members_authenticated=len(seen),counts=q['counts'],comparisons=comparisons,queries=queries,electrical_accepted=False,full_phy_accepted=False,physical650_accepted=False))
    save('inputs.json',dict(run=run,release=rel,index_pin=pin(paths['complete-output-index.json'].read_bytes()),selected={name:index['files'][name]for name in selected}))
    paths['native-fresh-rc.tar.gz'].unlink()
    print(json.dumps(comparisons,indent=2))
if __name__=='__main__':main()
