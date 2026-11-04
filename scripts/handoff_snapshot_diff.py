# SPDX-License-Identifier: Apache-2.0
"""Section-by-section difference of handoff before/restored snapshots; derived only."""
import json,sys
from pathlib import Path
def find(root,name):
    hits=[p for p in Path(root).rglob(name)];assert len(hits)==1,(name,hits);return hits[0]
def diff(a,b,path='',out=None,limit=40):
    out=[]if out is None else out
    if len(out)>=limit:return out
    if isinstance(a,dict)and isinstance(b,dict):
        for k in sorted(set(a)|set(b)):
            if k not in a or k not in b:out.append(dict(path=path+'/'+k,before=k in a,after=k in b))
            elif a[k]!=b[k]:diff(a[k],b[k],path+'/'+k,out,limit)
            if len(out)>=limit:break
    elif a!=b:out.append(dict(path=path,before=a,after=b))
    return out
def main(root,out):
    before=json.loads(find(root,'handoff-before.json').read_bytes())
    after=json.loads(find(root,'handoff-restored-observed.json').read_bytes())
    baseline=json.loads(find(root,'handoff-baseline.json').read_bytes())
    report={}
    for key in sorted(set(before)|set(after)):
        if key=='nets':continue
        a,b=before.get(key),after.get(key)
        report[key]=dict(equal=a==b,equal_to_baseline=b==baseline.get(key),first=diff(a,b) if a!=b else [])
        if isinstance(a,dict)and isinstance(b,dict)and a!=b:
            report[key]['changed_keys']=sum(1 for k in set(a)|set(b) if a.get(k)!=b.get(k))
            report[key]['baseline_vs_before_changed_keys']=sum(1 for k in set(a)|set(baseline.get(key,{})) if a.get(k)!=baseline.get(key,{}).get(k))
    import collections
    kinds=collections.Counter();examples={}
    for name,b in baseline['nets'].items():
        x=before['nets'][name];y=after['nets'][name]
        key=('after_eq_base' if y['encoded']==b['encoded'] else 'after_ne_base',
             'before_eq_base' if x['encoded']==b['encoded'] else 'before_ne_base',
             'wire_changed' if x['wire']!=y['wire'] else 'wire_same',
             'id_same' if x['identity']==y['identity'] else 'id_changed')
        kinds[key]+=1
        if key[0]=='after_ne_base' and len(examples.setdefault(key,[]))<12:
            examples[key].append(dict(name=name,baseline=b['encoded'],before=x['encoded'],after=y['encoded'],
                wires=[b['wire'],x['wire'],y['wire']]))
    report['nets']=dict(census={'|'.join(k):v for k,v in kinds.items()},examples={'|'.join(k):v for k,v in examples.items()})
    Path(out).write_text(json.dumps(report,indent=1,sort_keys=True,default=str))
    print(json.dumps(report['nets']['census'],sort_keys=True))
    print(json.dumps({k:{x:v[x] for x in v if x!='first'} for k,v in report.items()},sort_keys=True))
if __name__=='__main__':main(*sys.argv[1:])
