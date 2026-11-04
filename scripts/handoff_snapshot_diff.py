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
    Path(out).write_text(json.dumps(report,indent=1,sort_keys=True,default=str))
    print(json.dumps({k:{x:v[x] for x in v if x!='first'} for k,v in report.items()},sort_keys=True))
if __name__=='__main__':main(*sys.argv[1:])
