# SPDX-License-Identifier: Apache-2.0
"""Census of restored versus relinked netlist topology of one handoff run; derived only."""
import collections,json,sys
from pathlib import Path
def find(root,name):
    hits=list(Path(root).rglob(name));assert len(hits)==1,(name,hits);return hits[0]
def main(root,out):
    a=json.loads(find(root,'handoff-topology-before.json').read_bytes())
    b=json.loads(find(root,'handoff-topology-after.json').read_bytes())
    r=dict(top=[a['top'],b['top']],instances=[len(a['instances']),len(b['instances'])],ports=[len(a['ports']),len(b['ports'])],nets=[len(a['nets']),len(b['nets'])])
    ia,ib=a['instances'],b['instances']
    missing=sorted(set(ia)-set(ib));extra=sorted(set(ib)-set(ia))
    r['missing_after']=dict(count=len(missing),by_master=collections.Counter(ia[n]['master']for n in missing).most_common(30),examples=missing[:10])
    r['extra_after']=dict(count=len(extra),examples=extra[:10],by_master=collections.Counter(ib[n]['master']for n in extra).most_common(10))
    master=collections.Counter();pins=collections.Counter();ex=collections.defaultdict(list)
    for n in set(ia)&set(ib):
        x,y=ia[n],ib[n]
        if x['master']!=y['master']:master[(x['master'],y['master'])]+=1;continue
        for p in set(x['pins'])|set(y['pins']):
            if x['pins'].get(p,'<absent>')!=y['pins'].get(p,'<absent>'):
                key=(x['master'],p,'absent_after' if p not in y['pins'] else 'absent_before' if p not in x['pins'] else 'net_differs')
                pins[key]+=1
                if len(ex[key])<3:ex[key].append([n,x['pins'].get(p),y['pins'].get(p)])
    r['master_changes']=[[list(k),v]for k,v in master.most_common(20)]
    r['pin_differences']=[[list(k),v,ex[k]]for k,v in pins.most_common(40)]
    pa,pb=a['ports'],b['ports']
    r['port_differences']=[[k,pa.get(k),pb.get(k)]for k in sorted(set(pa)|set(pb))if pa.get(k)!=pb.get(k)][:20]
    Path(out).write_text(json.dumps(r,indent=1,sort_keys=True))
    print(json.dumps({k:r[k] for k in ('instances','ports','nets')},sort_keys=True))
if __name__=='__main__':main(*sys.argv[1:])
