"""Passive extracted-wire sensitivity; never a transient or PHY acceptance test."""
import math,re,warnings
from collections import defaultdict,deque
import numpy as np
from scipy.sparse import coo_matrix
from scipy.sparse.linalg import spsolve,MatrixRankWarning

def need(value,message):
    if not value:raise ValueError(message)

def number(text):
    m=re.fullmatch(r"([+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?)([A-Za-z]*)",text)
    need(m is not None,"unsupported numeric token")
    scale={"":1.,"t":1e12,"g":1e9,"meg":1e6,"k":1e3,"m":1e-3,"u":1e-6,"n":1e-9,"p":1e-12,"f":1e-15}
    suffix=m[2].lower();need(suffix in scale,"unknown numeric suffix")
    value=float(m[1])*scale[suffix];need(math.isfinite(value),"nonfinite value")
    return value

def parse_model(text,contract):
    rows=[line.split() for line in text.splitlines() if line.strip() and not line.lstrip().startswith("*")]
    need(len(rows)>2 and rows[0][0].lower()==".subckt"and rows[-1][0].lower()==".ends","one explicit subcircuit")
    need(rows[0][1].lower()==rows[-1][1].lower()and len(rows[-1])==2,"matching subcircuit terminator")
    need([x.lower()for x in rows[0][2:]]==[x.lower()for x in contract["interface"]],"exact native port order")
    devices={x["instance"].lower():x for x in contract["device_records"]}
    counts={"devices":0,"R":0,"C":0};seen=set();edges=[]
    for row in rows[1:-1]:
        name=row[0].lower();need(name not in seen,"duplicate element");seen.add(name)
        if name[0] in "rc":
            need(len(row)==4 and row[1].lower()!=row[2].lower(),"explicit distinct R/C nodes")
            value=number(row[3]);kind=name[0].upper();counts[kind]+=1
            need(value>0 if kind=="R"else value>=0,"invalid passive value")
            if kind=="R":edges.append((name,row[1].lower(),row[2].lower(),value))
        else:
            need(name in devices,"unrecognized active element or directive")
            d=devices[name];nodes=[t["node"].lower()for t in d["terminals"]];i=1+len(nodes)
            need(row[1:i]==nodes or [x.lower()for x in row[1:i]]==nodes,"exact device terminal order")
            need(row[i].lower()==d["model"].lower(),"exact native model")
            params={}
            for token in row[i+1:]:
                need(token.count("=")==1,"explicit device parameter")
                k,v=token.split("=");k=k.lower();need(k not in params,"duplicate device parameter");params[k]=v
            expected={k.lower():v for k,v in d["parameters"].items()}
            need(params==expected,"unchanged device parameters")
            counts["devices"]+=1
    need(counts==contract["counts"]and counts["devices"]==len(devices),"complete measured model census")
    return edges,counts

def solve(edges,source,sink):
    need(source!=sink,"distinct terminal pair")
    adjacency=defaultdict(list);names=set()
    for name,a,b,r in edges:
        need(name not in names and a!=b and math.isfinite(r)and r>0,"unique finite positive resistor")
        names.add(name);adjacency[a].append(b);adjacency[b].append(a)
    need(source in adjacency and sink in adjacency,"terminals in resistor graph")
    reached={source};queue=deque([source])
    while queue:
        for n in adjacency[queue.popleft()]:
            if n not in reached:reached.add(n);queue.append(n)
    need(sink in reached,"same passive connected component")
    component=[e for e in edges if e[1]in reached];nodes=sorted(reached-{sink});index={n:i for i,n in enumerate(nodes)}
    rr=[];cc=[];vv=[]
    for _,a,b,r in component:
        g=1./r
        for p,q in ((a,b),(b,a)):
            if p==sink:continue
            rr.append(index[p]);cc.append(index[p]);vv.append(g)
            if q!=sink:rr.append(index[p]);cc.append(index[q]);vv.append(-g)
    matrix=coo_matrix((vv,(rr,cc)),shape=(len(nodes),len(nodes))).tocsc()
    rhs=np.zeros(len(nodes));rhs[index[source]]=1.
    with warnings.catch_warnings():
        warnings.simplefilter("error",MatrixRankWarning)
        voltage=spsolve(matrix,rhs,permc_spec="COLAMD",use_umfpack=False)
    need(np.all(np.isfinite(voltage)),"finite sparse solution")
    observed={n:float(voltage[i])for n,i in index.items()};observed[sink]=0.
    residual=matrix@voltage-rhs;maximum=float(np.max(np.abs(residual)))
    need(maximum<=1e-7,"unit-current KCL residual")
    resistance=observed[source];need(resistance>0,"positive effective resistance")
    contributions=[];balance=defaultdict(float);power=0.
    for name,a,b,r in component:
        dv=observed[a]-observed[b];current=dv/r;loss=current*current*r;power+=loss
        balance[a]+=current;balance[b]-=current
        contributions.append(dict(element=name,a=a,b=b,resistance_ohm=r,unit_current_a=current,unit_power_w=loss,normalized_power=loss/resistance,sensitivity_ohm_per_ohm=current*current))
    need(abs(balance[source]-1.)<=1e-7 and abs(balance[sink]+1.)<=1e-7,"two terminal current balance")
    need(abs(power-resistance)<=max(1e-9,1e-7*resistance),"full network energy equals effective resistance")
    need(min(observed.values())>=-1e-7*resistance and max(observed.values())<=resistance*(1.+1e-7),"passive maximum principle")
    contributions.sort(key=lambda v:(-v["unit_power_w"],v["element"]))
    return dict(effective_resistance_ohm=resistance,component_nodes=len(reached),component_resistors=len(component),
        current_injection_a=1.,source=source,sink=sink,maximum_kcl_residual_a=maximum,
        energy_sum_w=power,source_current_a=balance[source],sink_current_a=balance[sink],
        full_unit_current_voltages_v=observed,full_edge_contributions=contributions,
        interpretation="Passive same-net unit-current resistance and sensitivity only; other terminals floating, capacitances excluded. Not actual operating currents or transient/signoff evidence.")
