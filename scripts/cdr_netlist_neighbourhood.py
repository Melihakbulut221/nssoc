# SPDX-License-Identifier: Apache-2.0
"""Print the device neighbourhood of selected instances in an extracted SPICE deck.

Parasitic two-terminal resistors (R cards) are merged into their nets, so each
listed node is a wire net. For every seed instance this prints the instance card,
then every device card touching one of its nets, with net names normalised to
the merged root. Read-only; nothing is simulated.
"""
import collections,sys
from pathlib import Path
def load(path):
    lines=Path(path).read_text(errors='replace').split('\n');par={}
    def f(a):
        r=a
        while par.get(r,r)!=r:r=par[r]
        while par.get(a,a)!=r:par[a],a=r,par[a]
        return r
    for l in lines:
        p=l.split()
        if len(p)>=4 and p[0][0]in'Rr':
            try:float(p[3])
            except ValueError:continue
            a,b=f(p[1].lower()),f(p[2].lower())
            if a!=b:par[a]=b
    devs=[]
    for l in lines:
        p=l.split()
        if p and p[0][0]in'XxQq':
            toks=[t for t in p[1:]if '='not in t];devs.append((p[0],toks[-1],[f(n.lower())for n in toks[:-1]],l.strip()))
    return devs
def main(path,seeds,depth):
    devs=load(path);on=collections.defaultdict(list)
    for d in devs:
        for n in d[2]:on[n].append(d)
    byname={d[0].lower():d for d in devs}
    for s in seeds:
        d=byname.get(s.lower())
        if d is None:
            hits=[x for x in devs if x[0].lower().endswith(s.lower())];print('##',s,'not exact; suffix hits',[h[0]for h in hits][:8]);d=hits[0]if hits else None
        if d is None:continue
        print('##',d[3][:240]);print('   nets',d[2])
        frontier={n for n in d[2]};seen=set()
        for level in range(depth):
            nxt=set()
            for n in sorted(frontier):
                if n in seen or len(on[n])>60:print('   (skip net',n,len(on[n]),'devices)')if len(on[n])>60 else None;seen.add(n);continue
                seen.add(n);print('  net',n)
                for x in on[n]:
                    print('    ',x[0],x[1],[('*'+m if m==n else m)for m in x[2]],' '.join(t for t in x[3].split()if t.split('=')[0]in('w','l','nx','r','m')))
                    nxt.update(x[2])
            frontier=nxt-seen
if __name__=='__main__':main(sys.argv[1],sys.argv[3].split(','),int(sys.argv[2]))
